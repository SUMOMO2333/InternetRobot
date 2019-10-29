#coding=utf8
#
# 
#Use camera to dectect the color of target and perform designed action.
import cv2
import numpy as np
import pickle
import matplotlib.pyplot as plt
import time
import math
import urllib
import socket
import pigpio
import threading
import signal
import LSC_Client

color = 0
rR = 0
rG = 0
rB = 0

stream = None
bytes = ''
Running = False

lsc = LSC_Client.LSC_Client()

#adjust stop signal
def Stop(signum, frame):
    global Running

    print("Stop: CV_color_detection")
    if Running is True:
        Running = False

#adjust Continue singlal
def Continue(signum, frame):
    global stream
    global Running

    print("Continue: CV_color_detection")
    if Running is False:
        #open connection 
        if stream:
            stream.close()
        stream = urllib.urlopen("http://127.0.0.1:8080/?action=stream?dummy=param.mjpg")
        bytes = ''
        Running = True


signal.signal(signal.SIGTSTP, Stop)
signal.signal(signal.SIGCONT, Continue)


#normolization.
def leMap(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


#find the largest area 
#the input varieble is the area which is gonna be compared
def getAreaMaxContour(contours) :
        contour_area_temp = 0
        contour_area_max = 0
        area_max_contour = None;

        for c in contours : #traversal all
            contour_area_temp = math.fabs(cv2.contourArea(c)) #calculate the area
            if contour_area_temp > contour_area_max :
                contour_area_max = contour_area_temp
                if contour_area_temp > 300:  
                	#Only when the area is larger than 300, the area is considered as value, this is a filter
                    area_max_contour = c

        return area_max_contour #return the largest frame area

action = 9999
actionTime = 0

def runAction():
    global action
    global actionTime

    while True:
        if action != 9999:
            lsc.RunActionGroup(action,actionTime) #send action command
            lsc.WaitForFinish(20000) #wait for action to be done
            action = 9999
        else:
            time.sleep(0.01)

#Start the action in running threading
th2 = threading.Thread(target=runAction)
th2.setDaemon(True)
th2.start()


#设置要运行的动作组
#num为要运行的动作组， num1为要运行的次数
def setAction(num,num1 = 1):
    global action
    global actionTime

    if action == 9999:  #if action number is 9999, that means the robot is not running any action right now.
        action = num   #action number
        actionTime = num1
        return action #sent back the action number
    else:
        return None  #faile


while True:
    if Running:
      orgFrame = None
      try:
          bytes += stream.read(4096) #read in the data
          a = bytes.find('\xff\xd8') #find frame head
          b = bytes.find('\xff\xd9') #find rame end 
          if a != -1 and b != -1:
              jpg = bytes[a:b+2]  #get the picture
              bytes = bytes[b+2:] #delete the pic
              orgFrame = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8), cv2.CV_LOAD_IMAGE_COLOR) #decode the picture
              orgFrame = cv2.resize(orgFrame, (320,240), interpolation = cv2.INTER_CUBIC) #normalize the picture to 320*240
    
      except Exception as e:
          print(e)
          continue
      if orgFrame is not None:
        height,width = orgFrame.shape[:2]
        frame = orgFrame
        frame = cv2.GaussianBlur(frame, (3,3), 0);
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV);  #change to HSV domain

        #split the HSV channel
        h, s, v = cv2.split(frame)
        v = cv2.equalizeHist(v)
        frame = cv2.merge((h,s,v))

        #each 3 frame can be use to detect one color
        # Split to 3 frame can reduece the CPU usage
        if color == 0:
            #frame = cv2.inRange(frame, (0,70,120), (5, 255, 255))
            frame = cv2.inRange(frame, (10,80,120), (19, 255, 255))
        elif color == 1:
            #frame = cv2.inRange(frame, (72,70,120), (77, 255, 255))
            frame = cv2.inRange(frame, (38,80,120), (48, 255, 255))
        else:
            #frame = cv2.inRange(frame, (115,70,120), (120, 255,255))
            frame = cv2.inRange(frame, (25,40,180), (33, 255,255))

        frame = cv2.morphologyEx(frame, cv2.MORPH_CLOSE, (4,4)) 
        (contours, hierarchy) = cv2.findContours(frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE,(0,0)) #find all contours
        areaMaxContour = getAreaMaxContour(contours) 
        centerX = 0
        centerY = 0 
        rad = 0
        if areaMaxContour is not None:
            print(centerX, centerY)
            (cen, rad) = cv2.minEnclosingCircle(areaMaxContour) #find min circle

        #store the detected color based on the target color
        if color == 0:
            rR = rad
            color = 1
        elif color == 1:
            rG = rad
            color = 2
        else:
            rB = rad
            color = 0

        #set action based on color.
        if rR > rG and rR > rB and rR >= 0: #red is largeest
            setAction(51,1)
        elif rG > rR and rG > rB and rG >= 0: #green is largetest
            setAction(50,1)
        elif rB > rR and rB > rG and rB >= 0:  #blue is largest
            setAction(50,1)
        else:
            pass
    else:
        bytes = ''
        time.sleep(0.1)

#cv2.destroyAllWindows()


