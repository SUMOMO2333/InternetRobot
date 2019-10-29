#!/usr/bin/python2
#coding=utf8
#
#实现功能: 获取超声波数据，根据距离的远近控制LED闪烁频率，
#距离越近频率越高直至长亮起
#
import pickle
import time
import urllib
import socket
import threading
import pigpio
import signal

Running = False

LED2 = 23    #LED的IO口
pi = pigpio.pi()
pi.set_mode(LED2, pigpio.OUTPUT)  #将IO口设置为输出
pi.write(LED2, 1)   #向IO口写入1,
led_time = 0

ip_port_sonar = ('127.0.0.1', 9030)
sock_sonar = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock_sonar.connect(ip_port_sonar)   #连接到超声波距离服务器以获取超声波测量到的距离

distance = 0.0  #距离

def leMap(x, in_min, in_max, out_min, out_max):  #数值映射
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


#从服务器获取数据更新距离
def updateDistance():
    global sock_sonar
    global distance
    global getDist

    while True:
        rcv = sock_sonar.recv(1024) #接收数据
        if rcv == b'':
            distance = 0.0
            break;
        else:
          if Running is True: 
            st =  rcv.strip()#去除空格   #有时候会粘包，影响不大不做处理
            try:
                distance = float(st)  #将字符串转换为浮点数
            except Exception as e: #粘包的话就不能正确转换数据，会抛异常
                print(e)
                distance = 0.0

#心跳，每隔3秒跳一次
def Heartbeat():
    while True:
        time.sleep(3)
        try:
            sock_sonar.sendall("3") #向服务器发字符"3"
        except:
            continue


##启动更新距离的子线程
th1 = threading.Thread(target=updateDistance)
th1.setDaemon(True)
th1.start()

##启动心跳子线程
th2 = threading.Thread(target=Heartbeat)
th2.setDaemon(True)
th2.start()

##暂停信号的回调
def Stop(signum, frame):  
    global Running
    print("Stop: 超声波LED")
    if Running is True:
        Running = False

##继续信号的回调
def Continue(signum, frame):
    global Running
    print("Continue: 超声波LED")
    if Running is False:
        Running = True

##注册回调
signal.signal(signal.SIGTSTP, Stop)
signal.signal(signal.SIGCONT, Continue)


while True:
  if Running is True:
    if distance >= 10 and distance < 30:
        led_time = leMap(float(distance), 10.0, 30.0, 0.01, 0.4)   #将距离数据映射到0.01~0.4 之间， 该值是LED的闪烁时间的变化范围
        pi.write(LED2, 1)
        time.sleep(led_time)
        pi.write(LED2, 0)
        time.sleep(led_time)
    elif distance >= 30:  #大于30cm就直接灭掉
        pi.write(LED2, 1)
        time.sleep(0.05)
    else :
        pi.write(LED2, 0) #小于10就长亮
        time.sleep(0.05)
  else:  #Running 为 False时就是被暂停，什么都不干
      time.sleep(0.1)


