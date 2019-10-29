#!/usr/bin/python2
#coding=utf8
import pickle
import time
import urllib
import socket
import threading
import signal
from LSC_Client import LSC_Client

ip_port_sonar = ('127.0.0.1', 9030)
sock_sonar = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
sock_sonar.connect(ip_port_sonar)  #连接到超声波距离服务器以获取距离

distance = 0.0
step = 0
Running = False

lsc = LSC_Client()

##从服务器接收超声波距离的数据
def updateDistance():
    global sock_sonar
    global distance

    while True:
        rcv = sock_sonar.recv(1024)
        if rcv == b'':
            distance = 0.0
            break;
        else:
            if Running is True:
                st =  rcv.strip() #去除空格
                try:
                    distance = float(st)  #将字符串转为浮点数
                except Exception as e:
                    print(e)
                    distance = 0.0

#启动距离更新线程
th1 = threading.Thread(target=updateDistance)
th1.setDaemon(True)
th1.start()


#暂停信号的回调
def Stop(signum, frame):
    global Running
    global step

    print("Stop: 超声波避障")
    if Running is True:
        Running = False
        lsc.StopActionGroup()  #暂停时要将正在运行的动作组停下来
        step = 0

#继续信号的回调
def Continue(signum, frame):
    global Running
    global step

    print("Continue: 超声波避障")
    if Running is False:
        step = 0
        Running = True

#注册信号回调
signal.signal(signal.SIGTSTP, Stop)
signal.signal(signal.SIGCONT, Continue)


#心跳，
def Heartbeat():
    while True:
        time.sleep(3)
        try:
            sock_sonar.sendall("3")
        except:
            continue

#启动心跳线程
th2 = threading.Thread(target=Heartbeat)
th2.setDaemon(True)
th2.start()


lsc.RunActionGroup(0,1)

while True:
  if Running is True:
    try:
        if step == 0:
            lsc.RunActionGroup(1,0)  #动作组1, 低姿态前进
            step = 1 #转到步骤1
        elif step == 1:
            if distance > 0 and distance <= 30:  # 超声波距离小于30CM
                lsc.StopActionGroup() #停止正在执行的动作组
                step = 2 #转到步骤2
        elif step == 2:
            lsc.RunActionGroup(4,11)  #运行4号动作在，低姿态右转动作执行16次
            lsc.WaitForFinish(20000)  #等待执行完毕
            step = 3 #转到步骤3
        elif step == 3: 
            step = 0 #回到步骤0
        else:
            pass
        time.sleep(0.1)
    except Exception as e:
        print(e)
        break
  else: #Running 是False, 程序被暂停，什么都不做
      time.sleep(0.1)


