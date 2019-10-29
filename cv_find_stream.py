#coding=utf8
#
# #实现功能:通过摄像头检测特定颜色的物体，使六足机器人跟随物体运动
# Object: detect the color to cperform the specific action 
import cv2
import numpy as np
import pickle
import matplotlib.pyplot as plt
import time
import math
import urllib
import socket
import signal
import threading
import LSC_Client

stream = None
bytes = ''
Running = False

step = 0
Dist = 0.0
rads = [0,0,0,0,0,0,0,0,0]
lastR = 0
count = 0
centerX = 0
centerY = 0 
xc = False

lsc = LSC_Client.LSC_Client()


#暂停信号的回调
def Stop(signum, frame):
    global Running

    print("Stop: CV_camera_tracking")
    if Running is True:
        Running = False
        centerX = 0
        count = 0
        rads = [0,0,0,0,0,0,0,0,0,0]
        lastR = 0
        xc = False

#继续信号的回调
def Continue(signum, frame):
    global stream
    global Running 
    print("Continue:_camera_tracking")
    if Running is False:
        #开关一下连接
        if stream:
            stream.close()
        stream = urllib.urlopen("http://127.0.0.1:8080/?action=stream?dummy=param.mjpg")
        bytes = ''
        Running = True

#注册信号和回调
signal.signal(signal.SIGTSTP, Stop)
signal.signal(signal.SIGCONT, Continue)

#数值映射
def leMap(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

#找出最大的轮廓
def getAreaMaxContour(contours) :
        contour_area_temp = 0
        contour_area_max = 0
        area_max_contour = None;

        for c in contours : #历便所有轮廓
            contour_area_temp = math.fabs(cv2.contourArea(c)) #计算面积
            if contour_area_temp > contour_area_max :
                contour_area_max = contour_area_temp
                if contour_area_temp > 100:  #限制最小面积
                    area_max_contour = c

        return area_max_contour  #返回最大面积


def logic():
    global step
    global Dist
    global lsc
    global xc
    global centerX
    global centerY
    
    while True:
        if Running is True:
            if xc is True:
                if step == 0:
                    if centerX > 440:  #不在中心，根据方向让机器人转向一步
                        print("l")
                        lsc.RunActionGroup(38,1)
                        lsc.WaitForFinish(3000)
                    elif centerX < 200:
                        print("r")
                        lsc.RunActionGroup(37,1)
                        lsc.WaitForFinish(3000)
                    else:
                        step = 1 #转到步骤1
                        pass
                elif step == 1:
                    if Dist > 30:  #检查距离是不是在 30 到 20之间，根据情况做对应操作
                        lsc.RunActionGroup(35,1)  #大于30 就前进，去靠近目标
                        lsc.WaitForFinish(3000) #等待动作执行完
                    elif Dist < 20 and Dist > 0:  
                        lsc.RunActionGroup(36,1)#小于20就后退，去远离目标
                        lsc.WaitForFinish(3000) #等待动作执行完毕
                    else:
                        pass
                    step = 0 #回到步骤0

            xc = False
        time.sleep(0.01)

#启动跟随控制六足动作的线程
th1 = threading.Thread(target=logic)
th1.setDaemon(True)
th1.start()

pitch = 1500
yaw = 1500
lsc.MoveServo(19, 1500,1000)  #先让摄像头云台舵机转到对于中间位置
lsc.MoveServo(20, 1500,1000)

while True:
  if Running is True:
    orgFrame = None
    try:
        bytes += stream.read(4096)  #接收数据v
        a = bytes.find('\xff\xd8')  #找到帧头
        b = bytes.find('\xff\xd9')  #找到帧尾
        if a != -1 and b != -1:
            jpg = bytes[a:b+2]  #取出数据
            bytes = bytes[b+2:]

            #解码图片
            orgFrame = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8), cv2.CV_LOAD_IMAGE_COLOR)
            #将图片缩放到320*240
            orgFrame = cv2.resize(orgFrame, (320,240), interpolation = cv2.INTER_CUBIC)
    except Exception as e:
        print(e)
        continue

    if orgFrame is not None:
        height,width = orgFrame.shape[:2]
        frame = orgFrame
        frame = cv2.GaussianBlur(frame, (5,5), 0); #高斯模糊
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV); #将图片转换到HSV空间

        #分离出各个HSV通道
        h, s, v = cv2.split(frame)
        v = cv2.equalizeHist(v)
        frame = cv2.merge((h,s,v))

        frame = cv2.inRange(frame, (68,70,120), (82, 255, 255))  #根据目标的颜色对图片进行二值化
        frame = cv2.morphologyEx(frame, cv2.MORPH_CLOSE, (4,4)) #闭操作
        (contours, hierarchy) = cv2.findContours(frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE,(0,0)) #找到所有的轮廓
        areaMaxContour = getAreaMaxContour(contours)  #找到其中最大的轮廓
        centerX = 0
        centerY = 0 

        if areaMaxContour is not None:
            ((centerX, centerY), rad) = cv2.minEnclosingCircle(areaMaxContour) #获得最小外接圆
            #cv2.circle(orgFrame,(int(centerX), int(centerY)), int(rad), (255,0,0), 1)
            centerX = leMap(centerX, 0.0, 320.0, 0.0, 640.0)  #将数据从0-320 映射到 0-640
            centerY = leMap(centerY, 0.0, 240.0, 0.0, 480.0)
            rads.append(rad) #追加新的最小外接圆半径
        else:
            rads.append(0)  #没找到球就追加0
        rads = rads[1:]  #将最久的一个数据去掉


    ######根据图像计算距离##########
        alr = 0
        for r in rads:
            alr = alr + r
        alr = alr / 10  #计算最近的10次的最小外接圆直径
        lastR = lastR * 0.7 + alr * 0.3  #简单滤波
        count += 1
        if count >= 5:  #每5次更新一次距离
            if lastR >= 2:  #半径太小就直接让就距离为0, 0就是没有目标
                Dist = 40 * 47.0 / (lastR * 2) # 40 是我们的目标小球的，47.0是我们我们的摄像头焦距 
                Dist = Dist if Dist < 100 else 0 #限制量程
            else:
                Dist = 0
            count = 0
    ####################################


        if areaMaxContour is not None:
            yc = True
            if centerX > 0:
                xc = True
            else:
                xc = False

            if centerY > 450:
                yaw = yaw + 40
            elif centerY > 380:
                yaw = yaw + 25
            elif centerY > 310:
                yaw = yaw + 15
            elif centerY > 245:
                yaw = yaw + 2
            elif centerY > 235:
                yc = False
            elif centerY > 170:
                yaw = yaw - 2
            elif centerY > 100:
                yaw = yaw - 15
            elif centerY > 30:
                yaw = yaw - 25
            elif centerY > 0:
                yaw = yaw - 40
            else:
                yc = False


#            if yc is True:
#                yaw = yaw if yaw <= 2500 else 2500
#                yaw = yaw if yaw >= 500 else 500
#                lsc.MoveServo(20, yaw, 50)
        else:
            pass

#        if cv2.waitKey(1) & 0xFF == ord('q'):
#            break
  else:
      bytes = ''
      time.sleep(0.1)
      
#cv2.destroyAllWindows()


