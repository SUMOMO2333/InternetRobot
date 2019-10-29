#coding=utf8
#
# 实现功能: 通过摄像头颜色识别捕捉小球控制舵机转动使摄像头始终跟随小球运动
#Use the camera to recognize the color to move the motor towards follwing the movement of target

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

lsc = LSC_Client.LSC_Client()

#暂停信号的回调
def Stop(signum, frame):
    global Running

    print("Stop: CV_camera_tracking")
    if Running is True:
        Running = False

#继续信号的回调
def Continue(signum, frame):
    global stream
    global Running

    print("Continue: CVcamera_tracking")
    if Running is False:
        #关闭链接然后重新打开
        if stream:
            stream.close()
        stream = urllib.urlopen("http://127.0.0.1:8080/?action=stream?dummy=param.mjpg")
        bytes = ''
        Running = True

#注册信号回调
signal.signal(signal.SIGTSTP, Stop)
signal.signal(signal.SIGCONT, Continue)

#数值范围映射
def leMap(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

#获取面积最大的轮廓
def getAreaMaxContour(contours) :
        contour_area_temp = 0
        contour_area_max = 0
        area_max_contour = None;

        for c in contours :
            contour_area_temp = math.fabs(cv2.contourArea(c)) #计算面积
            if contour_area_temp > contour_area_max : #新面积大于历史最大面积就将新面积设为历史最大面积
                contour_area_max = contour_area_temp
                if contour_area_temp > 30: #只有新的历史最大面积大于30,才是有效的最大面积
                                           #就是剔除过小的轮廓
                    area_max_contour = c

        return area_max_contour #返回得到的最大面积，如果没有就是 None

pitch = 1500  #初始位置为中间位置
yaw = 1500
lsc.MoveServo(19, 1500,1000)  #让摄像头云台的两个舵机都转动到中间位置
lsc.MoveServo(20, 1500,1000)

while True:
  if Running is True:
    orgFrame = None
    try:
        bytes += stream.read(4096)  #从流中获取数据，数据都是来自与Mjpg-streamer
        a = bytes.find('\xff\xd8') #查找帧头
        b = bytes.find('\xff\xd9') #查找帧尾
        if a != -1 and b != -1:
            jpg = bytes[a:b+2]  #提取数据
            bytes = bytes[b+2:] #取出被取走的数据
            #对接收到的数据进行解码
            orgFrame = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8), cv2.CV_LOAD_IMAGE_COLOR)
            #对图片进行缩放，缩放到320×240, 以降低后续处理的CPU占用
            orgFrame = cv2.resize(orgFrame, (320,240), interpolation = cv2.INTER_CUBIC)
    except Exception as e:
        print(e)
        continue

    if orgFrame is not None:  
        height,width = orgFrame.shape[:2]
        frame = orgFrame
        frame = cv2.GaussianBlur(frame, (5,5), 0); #将
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV); #将图像转换到HSV空间

        #分离出各个HSV通道
        h, s, v = cv2.split(frame)
        v = cv2.equalizeHist(v)
        frame = cv2.merge((h,s,v))

        frame = cv2.inRange(frame, (70,100,75), (85, 255, 255)) #根据hsv值对图片进行二值化 
        frame = cv2.morphologyEx(frame, cv2.MORPH_CLOSE, (3,3))
        (contours, hierarchy) = cv2.findContours(frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE,(0,0)) #找出所有外轮廓
        areaMaxContour = getAreaMaxContour(contours) #找到最大的轮廓
        centerX = 0
        centerY = 0 
        if areaMaxContour is not None:  #有找到最大面积
            ((centerX, centerY), rad) = cv2.minEnclosingCircle(areaMaxContour) #获得最大轮廓的最小外接圆
           # cv2.circle(orgFrame, (int(centerX), int(centerY)), 4, (0,0,255), -1)     
           # cv2.circle(orgFrame, (int(centerX), int(centerY)), int(rad), (255,0,0), 2)

        #frame = cv2.bitwise_and(orgFrame, orgFrame, mask= frame)

        centerX = leMap(centerX, 0.0, 320.0, 0.0, 640.0)  #将0～320映射到0-640, 在没对图片进行缩放时可以不做映射
                                                          #下面的代码都是按0-640写的， 所以要做此操作
        centerY = leMap(centerY, 0.0, 240.0, 0.0, 480.0)

        xc = True
        yc = True

        #范围为0-640
        if centerX > 620:
            pitch = pitch - 50  #根据中心位置确定要调整的舵机角度,距离中心越大调整幅度就越大
        elif centerX > 540:
            pitch = pitch -  30
        elif centerX > 380:
            pitch = pitch - 15
        elif centerX > 325:
            pitch = pitch - 2
        elif centerX > 315:
            xc = False  #在中心范围内，不用调整舵机
        elif centerX > 260:
            pitch = pitch + 2
        elif centerX > 100:
            pitch = pitch + 15
        elif centerX > 20:
            pitch = pitch + 30
        elif centerX > 0:
            pitch = pitch + 50
        else:
            xc = False  #屏幕中没有球， 不调整舵机

        #范围为0-480
        if centerY > 450:
            yaw = yaw + 40  #根据中心位置确定要调整的舵机角度,距离中心越大调整幅度就越大
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

        if xc is True:  #舵机角度被改变
            pitch = pitch if pitch <= 2500 else 2500  #限制舵机角度的最大最小值
            pitch = pitch if pitch >= 500 else 500
            lsc.MoveServo(19, pitch, 50)  #让舵机转到新的角度去

        if yc is True:
            yaw = yaw if yaw <= 2500 else 2500
            yaw = yaw if yaw >= 500 else 500
            lsc.MoveServo(20, yaw, 50)

        #if cv2.waitKey(1) & 0xFF == ord('q'):
        #    break
  else:
      bytes = ''
      time.sleep(0.1)
      
#cv2.destroyAllWindows()


