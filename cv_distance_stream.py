#coding=utf8
#
#用摄像头检测小球到摄像头的距离，根据距离控制LED灯的闪烁
#距离越小闪烁越快,直至长亮
#Use camera to detect the distance from the target to control the flash of LED light
# the closer target is , the more frequently the LED flashes

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

stream = None
bytes = ''
Running = False 

#暂停信号的回调
def Stop(signum, frame):
    global Running

    print("Stop: CV_distance detection")
    if Running is True:
        Running = False

#继续信号的回调
def Continue(signum, frame):
    global stream
    global Running

    print("Continue: CV_distance detection", signum)
    if Running is False:
        #开关一下连接
        if stream:
            stream.close()
        stream = urllib.urlopen("http://127.0.0.1:8080/?action=stream?dummy=param.mjpg")
        bytes = ''
        Running = True

#注册信号回调
signal.signal(signal.SIGTSTP, Stop)
signal.signal(signal.SIGCONT, Continue)

LED2 = 23  #LED对应的IO口
pi = pigpio.pi()
pi.set_mode(LED2, pigpio.OUTPUT) #将IO口设为输出
pi.write(LED2, 1) #将LED灯熄灭
led_time = 0

Dist = 0.0
rads = [0,0,0,0,0,0,0,0,0,0]
lastR = 0
count = 0

#数值映射
def leMap(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

#闪烁LED灯
def ledFlash():
    global LED2
    global pi
    global led_time
    global quit
    while True:
      if Running:
        if Dist  >= 10 and Dist < 30: #距离在10～30之间
            led_time = leMap(float(Dist), 10.0,20.0, 0.01,0.3)
            pi.write(LED2, 1)
            time.sleep(led_time)
            pi.write(LED2, 0)
            time.sleep(led_time)
        elif Dist >= 30: #距离超过30
            pi.write(LED2, 1)
            time.sleep(0.1)
        else :  #距离小于10
            pi.write(LED2, 0)
            time.sleep(0.1)
      else:
          time.sleep(0.05)

#获取面积最大的轮廓
def getAreaMaxContour(contours) :
        contour_area_temp = 0
        contour_area_max = 0
        area_max_contour = None;

        for c in contours :
            contour_area_temp = math.fabs(cv2.contourArea(c))
            if contour_area_temp > contour_area_max :
                contour_area_max = contour_area_temp
                if contour_area_temp > 300:
                    area_max_contour = c

        return area_max_contour

#启动控制LED闪烁的线程
th1 = threading.Thread(target=ledFlash)
th1.setDaemon(True)
th1.start()

while True:
  if Running:
    orgFrame = None
    try:
        bytes += stream.read(4096) #获取数据
        a = bytes.find('\xff\xd8') #查找帧头
        b = bytes.find('\xff\xd9') #查找帧尾
        if a != -1 and b != -1:
            jpg = bytes[a:b+2]  #取出数据
            bytes = bytes[b+2:] #去除已取出的数据
            orgFrame = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8), cv2.CV_LOAD_IMAGE_COLOR) #解码图片
            #将图片缩放到320*480，以减少CPU 占用
            orgFrame = cv2.resize(orgFrame, (320,240), interpolation = cv2.INTER_CUBIC)
    except Exception as e:
        print(e)
        continue

    if orgFrame is not None:
        height,width = orgFrame.shape[:2]
        frame = orgFrame
        frame = cv2.GaussianBlur(frame, (3,3), 0); #高斯模糊
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV); #将图片转换到HSV空间

        #分离出各个HSV通道
        h, s, v = cv2.split(frame)
        v = cv2.equalizeHist(v)
        frame = cv2.merge((h,s,v))

        frame = cv2.inRange(frame, (68,70,120), (82, 255, 255)) #green ball  #二值化
        #frame = cv2.inRange(frame, (0,70,130), (5, 255, 255))  #red ball
        #frame = cv2.inRange(frame, (115,70,120), (120, 255, 255)) #red ball
        frame = cv2.morphologyEx(frame, cv2.MORPH_CLOSE, (4,4))
        (contours, hierarchy) = cv2.findContours(frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE,(0,0)) #找出所有轮廓
        areaMaxContour = getAreaMaxContour(contours) #找出最大轮廓

        centerX = 0
        centerY = 0 

        if areaMaxContour is not None:
            (cen, rad) = cv2.minEnclosingCircle(areaMaxContour) #获取最小外接圆
            #cv2.circle(orgFrame, (int(cen[0]),int(cen[1])), int(rad), (255,0,0), 1)
            rads.append(rad)  #将新半径追加到历史数据中
        else:
            rads.append(0)  #没找到目标的话就追加半径为0
        rads = rads[1:]  #去掉最旧的一个半径

        alr = 0
        for r in rads:
            alr = alr + r
        alr = alr / 10 #计算最近十次的半径

        lastR = lastR * 0.7 + alr * 0.3 #简单地滤波
        count += 1
        if count >= 5:   #每五次更新一次距离
            if lastR >= 2 :
                Dist = 40 * 47 /(lastR*2)  #40是小球的直径， 47是摄像头焦距， 
                Dist = Dist if Dist < 100 else 0 #限制范围
            else:
                Dist = 0
       #    print(Dist)
            count = 0

       # frame = cv2.bitwise_and(orgFrame, orgFrame, mask= frame)
       # cv2.imshow('f', frame)
       #  cv2.circle(orgFrame, (centerX, centerY), 2, (255,99,0), -1)
       # cv2.imshow('frame', orgFrame)
       # if cv2.waitKey(1) & 0xFF == ord('q'):
       #     break
  else:
      bytes = ''
      time.sleep(0.05)
#cv2.destroyAllWindows()


