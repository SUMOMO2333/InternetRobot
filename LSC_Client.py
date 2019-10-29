#coding:utf-8
#achieve a client which connnects to the server(lsc.py)
#this client can send server commands ,such as run action group.

import socket
import threading
import time

class LSC_Client(object):

    ip_port = ('127.0.0.1', 9029)
    sock = None
    th1 = None
    Stop = False

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(self.ip_port)
        self.th1 = threading.Thread(target=LSC_Client.Heartbeat, args=(self,))
        self.th1.setDaemon(True)
        self.th1.start()

    def __del__(self):
        self.Stop = True
        self.th1.join()
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

    def MoveServo(self, servoId, pos, time):
        buf = bytearray(b'\x55\x55\x08\x03\x01')   #action command 3, motor number =1
        buf.extend([(0xff & time), (0xff & (time >> 8))])  #rotation time
        buf.append((0xff & servoId)) #choose the motor that you want to control
        buf.extend([(0xff & pos), (0xff & (pos >> 8))]) # target location
        self.sock.sendall(buf) #send the data stored in buffer

    def RunActionGroup(self,actNum, num):
        buf = bytearray(b'\x55\x55\x05\x06') # header, length, command # 6
        buf.append(0xff & actNum)  #append the action number
        buf.extend([(0xff & num), (0xff & (num >> 8))]) 
        self.sock.sendall(buf) #send the data in buffer

    def StopActionGroup(self):
        self.sock.sendall(b'\x55\x55\x02\x07')  # send stop command


    def Heartbeat(self):
        count = 0
        while True:
            if self.Stop is True:
                break
            time.sleep(0.1)
            count += 1
            if count >= 30: #3 sec once
                count = 0
                try:
                    self.sock.sendall('3') #send char "3"
                except:
                    continue

    #读出接收到的所有数据,以清除缓存 
    def flush(self):
        self.sock.settimeout(0.0000001) #
        while True:
            try:
                self.sock.recv(8192)
            except:
                break

    ##等待动作组被执行完或是被停止, timeout 为超时时间
    def WaitForFinish(self, timeout): 
        self.flush()

        buf = bytearray()
        timeout = time.time() + (float(timeout) / 1000) #计算超时时间到达后的系统时间
        self.sock.settimeout(0.005)
        while True:   
            if time.time() > timeout:  #如果系统时间达到就返回False,即动作组没在指定时间内停止
                return False
            try:
                rcv  = self.sock.recv(128)  #接收数据
                if rcv is not None:
                    buf += rcv
                    while True:
                        try:
                            index = buf.index(b'\x55\x55')  #find fram header
                            if len(buf) >= index + 3:
                                buf = buf[index:]  #将帧头前面不符合的部分剔除
                                if (buf[2] + 2) <= len(buf): #缓存中的数据数据是否完整
                                    cmd = buf[0: (buf[2]+2)] #将命令取出 print("OK")
                                    buf = buf[buf[2]+2:]
                                    if cmd[3] == 0x08 or cmd[3] == 0x07:  #接受到的数据的命令号为8或7就是动作已停止
                                        return True
                        except:
                            break
            except socket.timeout:
                continue
            except:
                return False


