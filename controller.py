#!/usr/bin/python3
#coding:utf8

# This is an server to switch different functions.
import subprocess
import time
import threading
import socketserver
import re
import signal

lastMode = 0

ChildSonarLed = subprocess.Popen(["python2", "/home/pi/spider/sonar_led.py"])  #LED control based on distance
ChildSonar = subprocess.Popen(["python2", "/home/pi/spider/spider_bz.py"])    #obstacle detection
ChildCvColor = subprocess.Popen(["python2", "/home/pi/spider/cv_color_stream.py"]) #color recognization
ChildCvTrack = subprocess.Popen(["python2", "/home/pi/spider/cv_track_stream.py"]) #camera track
ChildCvDistance = subprocess.Popen(["python2", "/home/pi/spider/cv_distance_stream.py"]) #distance detection
ChildCvFind = subprocess.Popen(["python2", "/home/pi/spider/cv_find_stream.py"])  #spider following target


#
#
def modeReset():  
    if lastMode != 1:
        ChildSonarLed.send_signal(signal.SIGTSTP)  #send LED sensor stop signal
    if lastMode != 2:
        ChildSonar.send_signal(signal.SIGTSTP)  #send sona stop signal
    if lastMode != 3:
        ChildCvColor.send_signal(signal.SIGTSTP)
    if lastMode != 4:
        ChildCvTrack.send_signal(signal.SIGTSTP) 
    if lastMode != 5:
        ChildCvDistance.send_signal(signal.SIGTSTP) 
    if lastMode != 6:
        ChildCvFind.send_signal(signal.SIGTSTP) 

class RobotServer(socketserver.TCPServer):
    allow_reuse_address = True  

class RobotServerHandler(socketserver.BaseRequestHandler):
    ip = ""
    port = None
    buf = ""

    def setup(self):
        self.ip = self.client_address[0].strip()  # get the ip of client
        self.port = self.client_address[1] # get the port number of client
        print("connected\tIP:" + self.ip + "\tPort:" + str(self.port))
        self.request.settimeout(20)  #set time out as 20 seconds

    def handle(self):
        global lastMode
        Flag = True
        while Flag:
            try:
                recv = self.request.recv(128)  #receive data
                if recv == b'':
                    Flag = False  
                else:
                    self.buf += recv.decode()  #decoding the received data
                    #print(self.buf)
                    self.buf = re.sub(r'333333','',self.buf, 10)  #assume clinet will send "3" to represent a heartbeat,delete "3" from string/
                    s = re.search(r'mode=\d{1,2}', self.buf, re.I) #find the "mode = digit" from string
                    if s:
                        self.buf=""   #if found, then clear the buffer
                        Mode = int(s.group()[5:])  #get mode value from the string
                        print(Mode)


                        #send child process signal to continue based on different mode value
                        
                        if Mode == 0:
                            if lastMode != Mode: #only when the last time mode is different with current mode
                                lastMode = Mode   
                                modeReset()
                            self.request.sendall("OK".encode())   #send "OK" to clients
                        elif Mode == 1:
                            if lastMode != Mode:
                                lastMode = Mode
                                modeReset()
                                ChildSonarLed.send_signal(signal.SIGCONT)
                            self.request.sendall("OK".encode())
                        elif Mode == 2:
                            if lastMode != Mode:
                                lastMode = Mode
                                modeReset()
                                ChildSonar.send_signal(signal.SIGCONT)
                            self.request.sendall("OK".encode())
                        elif Mode == 3:
                            if lastMode != Mode:
                                lastMode = Mode
                                modeReset()
                                ChildCvColor.send_signal(signal.SIGCONT)
                            self.request.sendall("OK".encode())
                        elif Mode == 4:
                            if lastMode != Mode:
                                lastMode = Mode
                                modeReset()
                                ChildCvTrack.send_signal(signal.SIGCONT)
                            self.request.sendall("OK".encode())
                        elif Mode == 5:
                            if lastMode != Mode:
                                lastMode = Mode
                                modeReset()
                                ChildCvDistance.send_signal(signal.SIGCONT)
                            self.request.sendall("OK".encode())
                        elif Mode == 6:
                            if lastMode != Mode:
                                lastMode = Mode
                                modeReset()
                                ChildCvFind.send_signal(signal.SIGCONT)
                            self.request.sendall("OK".encode())
                        else:
                            lastMode = 0
                            modeReset()
                            self.request.sendall("Failed".encode())
                            pass
            except Exception as e:
                print(e)
                Flag = False

    def finish(self):
        lastMode = 0
        modeReset()
        print("disconnected\tIP:" + self.ip + "\tPort:" + str(self.port))


server = RobotServer(("",9040), RobotServerHandler)  
server.serve_forever()#start server

