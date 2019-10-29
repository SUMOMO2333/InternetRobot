#!/usr/bin/python3


#
#实现的功能: 程序通过超声波传感器测量距离.
#            实现一个socket服务器， 所有连接到这个服务器的客户端都会定时接收到该距离
#
import RPi.GPIO as GPIO
import time
import threading
import socketserver
import hcsr04

client_socket = []  #客户端列表

GPIO_TRIG = 3 #超声波trig引脚对应的IO号
GPIO_ECHO = 2 #超声波echo引脚对应的IO号

sonar = hcsr04.Measurement(GPIO_TRIG, GPIO_ECHO) #超声波类
distance = 0.0  #距离

class LobotServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

class LobotServerHandler(socketserver.BaseRequestHandler):
    global clietn_socket
    ip = ""
    port = None

    def setup(self):
        self.ip = self.client_address[0].strip()
        self.port = self.client_address[1]
        print("connected\tIP:"+self.ip+"\tPort:"+str(self.port))
        client_socket.append(self.request)
        self.request.settimeout(10)

    def handle(self):
        Flag = True
        while Flag:
            try:
                buf = self.request.recv(1024)
                if buf == b'':
                    Flag = False
                else:
                    pass #不管收到什么都不作处理
            except Exception as e:
                print(e)
                Flag = False
                break
    def finish(self):
        client_socket.remove(self.request)
        print("disconnected\tIP:"+self.ip+"\tPort:"+str(self.port))

def printDistance():
    global distance
    while True:
        string = "{:.2f}    ".format(distance)  #组织要发送的包含距离的字符串
        #print(string)
        for client in client_socket:  # 历便所有客户端发送数据
            try:
                client.sendall(string.encode()) 
            except Exception as e:
                print(e)
                continue
        time.sleep(0.2)

def updateDistance():
    global distance
    global odist
    while True:
        try:
            temp = sonar.distance_metric(sonar.raw_distance(2, 0.08))  #超声波测量距离 
            distance = temp if temp <= 450.0 else 0.0  #限幅， 超过450 的就等于0, 0代表就距离超出量程
        except Exception as e:
            print(e)

server = LobotServer(("", 9030), LobotServerHandler)

th1 = threading.Thread(target=updateDistance, daemon=True)  #测量距离的线程
th2 = threading.Thread(target=printDistance, daemon=True)   #向各个客户端发送距离的线程
th1.start()
th2.start()

while True:
    try:
        server.serve_forever()  #启动服务器的循环
    except Exception as e:
        print(e)
        server.shutdown()
        server.server_close()
        break

