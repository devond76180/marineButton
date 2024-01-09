import sys
import threading
import time
import traceback
from PyQt5.QtCore import *
from PyQt5.QtWidgets import * 
from PyQt5.QtGui import * 
from typing import NamedTuple
from evdev import ecodes, list_devices, AbsInfo, InputDevice
from Xlib import display
import board
import busio
from digitalio import Direction
from adafruit_mcp230xx.mcp23017 import MCP23017

NAME_NAV = "nav"
NAME_ANC = "anc"
NAME_ANCHOR_UP = "anchorup"
NAME_ANCHOR_DOWN = "anchordown"
NAME_HORN = "horn"
NAME_FRESH_WATER = "freshwater"
NAME_MACERATOR = "macerator"
NAME_RAW_WATER = "rawwater"
NAME_LIVE_WELL = "livewell"
NAME_LIVE_WELL_FILL = "livewellfill"
NAME_BILGE_STARBOARD = "bilgestarboard"
NAME_BILGE_PORT = "bilgeport"

TOP_LABEL_ROW = 0
TOP_BUTTON_ROW = 1
BOTTOM_LABEL_ROW = 6
BOTTOM_BUTTON_ROW = 7

touchDevice = None
stopThreads = False
i2c = None
mcp1 = None
mcp2 = None
relayArray = []
class ButtonStruct(NamedTuple):
    state : int
    cycleState : int
    cycleTimer : int
    cycleSpinner : None
    buttonTimer : None
    button : None
    cycleTime : int
    momentary : int
    isOff : int
    relay : int
    
class EventThread(QThread):
    any_signal = pyqtSignal(int,int)
    
    def __init__(self, parent=None):
        super(EventThread, self).__init__(parent)

        # helper function to execute the threads
    
    def run(self):

        prevTime = 0
        global stopThreads
        while True :
            for event in touchDevice.read_loop() :
                #if event.type == evdev.ecodes.EV_KEY:
                if prevTime == 0:
                    prevTime = time.perf_counter()
                    #print(event)
                    data = display.Display().screen().root.query_pointer()._data
                    #print(display.Display().screen().root.query_pointer()._data)
                    #self.callback(data["root_x"],data["root_y"])
                    self.any_signal.emit(data["root_x"],data["root_y"])
                elif time.perf_counter() - prevTime > 0.1:
                    prevTime = time.perf_counter()
                    #print(prevTime," ",time.perf_counter()," ",event)
                    data = display.Display().screen().root.query_pointer()._data
                    #print(display.Display().screen().root.query_pointer()._data)
                    #self.callback(data["root_x"],data["root_y"])
                    self.any_signal.emit(data["root_x"],data["root_y"])
                else :
                    prevTime = time.perf_counter()
            if stopThreads :
                break

class Window(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        global mcp1
        global mcp2
        
        layout = QGridLayout()
        self.findTouchScreen()
        #print("")
        #print(touchDevice.name)
        self.eventThread = EventThread()
        self.eventThread.any_signal.connect(self.touchPressed)
        self.eventThread.start()
        self.buttonDict = {}
        self.labelDict = {}
        self.windowPos = None
        self.filler = QLabel("",self)
        self.filler.setFixedSize(100,100)
        self.filler2 = QLabel("",self)
        self.filler2.setFixedSize(100,30)
        global relayArray
        for i in range(16) :
            pin = mcp1.get_pin(i)
            pin.direction = Direction.OUTPUT
            pin.value = False
            relayArray.append(pin)
        
        
        self.livewellTimer = None

        self.labelNav = None
        pixmap = QPixmap("marine push button 4 off clean.png")
        self.pixmapOff = pixmap.scaled(120,120,Qt.KeepAspectRatio)
        pixmap = QPixmap("marine push button 4 on blue clean.png")
        self.pixmapBlue = pixmap.scaled(120,120,Qt.KeepAspectRatio)
        pixmap = QPixmap("marine push button 4 on red clean.png")
        self.pixmapRed = pixmap.scaled(120,120,Qt.KeepAspectRatio)
        pixmap = QPixmap("marine push button 4 on green clean.png")
        self.pixmapGreen = pixmap.scaled(120,120,Qt.KeepAspectRatio)

        self.createButtonOnOff(layout,NAME_NAV,0,TOP_BUTTON_ROW,False,0)
        self.createLabel("NAV",layout,NAME_NAV,0,TOP_LABEL_ROW)

        self.createButtonOnOff(layout,NAME_ANC,1,TOP_BUTTON_ROW,False,1)
        self.createLabel("AT ANCHOR",layout,NAME_ANC,1,TOP_LABEL_ROW)

        self.createButtonMomentary(layout,NAME_ANCHOR_UP,2,TOP_BUTTON_ROW,0)
        self.createLabel("ANCHOR UP",layout,NAME_ANCHOR_UP,2,TOP_LABEL_ROW)

        self.createButtonMomentary(layout,NAME_ANCHOR_DOWN,3,TOP_BUTTON_ROW,2)
        self.createLabel("ANCHOR DOWN",layout,NAME_ANCHOR_DOWN,3,TOP_LABEL_ROW)

        self.createButtonMomentary(layout,NAME_HORN,4,TOP_BUTTON_ROW,4)
        self.createLabel("HORN",layout,NAME_HORN,4,TOP_LABEL_ROW)

        self.createButtonOnOff(layout,NAME_LIVE_WELL,5,TOP_BUTTON_ROW,True,5)
        self.createLabel("LIVE WELL\n CYCLE",layout,NAME_LIVE_WELL,5,TOP_LABEL_ROW)

        self.createButtonOnOff(layout,NAME_FRESH_WATER,0,BOTTOM_BUTTON_ROW,False,6)
        self.createLabel("FRESH \n WATER",layout,NAME_FRESH_WATER,0,BOTTOM_LABEL_ROW)

        self.createButtonOnOff(layout,NAME_MACERATOR,1,BOTTOM_BUTTON_ROW,False,7)
        self.createLabel("MACERATOR",layout,NAME_MACERATOR,1,BOTTOM_LABEL_ROW)

        self.createButtonOnOff(layout,NAME_BILGE_STARBOARD,2,BOTTOM_BUTTON_ROW,False,8)
        self.createLabel("BILGE \n STARBOARD",layout,NAME_BILGE_STARBOARD,2,BOTTOM_LABEL_ROW)

        self.createButtonOnOff(layout,NAME_BILGE_PORT,3,BOTTOM_BUTTON_ROW,False,9)
        self.createLabel("BILGE \n PORT",layout,NAME_BILGE_PORT,3,BOTTOM_LABEL_ROW)

        self.createButtonOnOff(layout,NAME_RAW_WATER,4,BOTTOM_BUTTON_ROW,False,10)
        self.createLabel("RAW WATER",layout,NAME_RAW_WATER,4,BOTTOM_LABEL_ROW)

        self.createButtonOnOff(layout,NAME_LIVE_WELL_FILL,5,BOTTOM_BUTTON_ROW,False,5)
        self.createLabel("LIVE WELL\n FILL",layout,NAME_LIVE_WELL_FILL,5,BOTTOM_LABEL_ROW)


        layout.addWidget(self.filler2,2,0,1,1)
        layout.addWidget(self.filler,5,0,1,1)
        layout.addWidget(self.filler,8,0,1,1)
        self.setLayout(layout)
        self.setFixedSize(1000,600);
        self.setStyleSheet("background-color: rgb(250,250,255);border: 0px solid black;")

        self.navLink = [NAME_ANC]
        self.ancLink = [NAME_NAV]
        self.hornLink = None
        self.anchorupLink = None
        self.anchordownLink = None
        self.freshwaterLink = None
        self.maceratorLink = None
        self.bilgestarboardLink = None
        self.bilgeportLink = None
        self.rawwaterLink = None
        self.livewellLink = [NAME_LIVE_WELL_FILL]
        self.livewellfillLink = [NAME_LIVE_WELL]

        self.buttonLinks={NAME_NAV:self.navLink,NAME_ANC:self.ancLink,NAME_HORN:self.hornLink,
            NAME_ANCHOR_UP:self.anchorupLink,NAME_ANCHOR_DOWN:self.anchordownLink,
            NAME_MACERATOR:self.maceratorLink,NAME_FRESH_WATER:self.freshwaterLink,
            NAME_BILGE_STARBOARD:self.bilgestarboardLink,NAME_BILGE_PORT:self.bilgeportLink,
            NAME_RAW_WATER:self.rawwaterLink,NAME_LIVE_WELL:self.livewellLink,NAME_LIVE_WELL_FILL:self.livewellfillLink}
    
    def touchPressed(self,x,y) :
        keys = list(self.buttonDict)
        adjx = x - self.windowPos.x() 
        adjy = y - self.windowPos.y()
        #print("touch pressed ",adjx," ",adjy)
        for key in keys :
            button = self.buttonDict[key].button
            if adjx >= button.pos().x():
                if adjx <= button.pos().x()+button.width():
                    if adjy >= button.pos().y():
                         if adjy <= button.pos().y()+button.height():
                            self.onoff(button,key) 
        

    def mouseReleaseEvent(self,QMouseEvent):
        keys = list(self.buttonDict)
        x = QMouseEvent.pos().x();
        y = QMouseEvent.pos().y();
        
        for key in keys :
            button = self.buttonDict[key].button
            if x >= button.pos().x():
                if x <= button.pos().x()+button.width():
                    if y >= button.pos().y():
                        if y <= button.pos().y()+button.height():
                            self.off(button,key) 

    def createButtonMomentary(parent,layout,linkName,x,y,relay):
        button = QLabel(parent)
        button.setPixmap(parent.pixmapOff)
        button.setFixedSize(parent.pixmapOff.width(),parent.pixmapOff.height())
        layout.addWidget(button,y,x,1,1)      
        parent.buttonDict[linkName] = ButtonStruct(True,True,0,None,None,button,0,True,False,relay)

    def createButtonCycled(parent,layout,linkName,x,y,relay):
        button = QPushButton(
            icon=QIcon("marine push button 4 off clean.png"),
            text=""
        )
        button.setFixedSize(120,120)
        button.setIconSize(QSize(120, 120))
        button.setCheckable(True)
        button.clicked.connect(lambda: parent.onoff(button,linkName))
        layout.addWidget(button,y,x,1,1)
        parent.buttonDict[linkName] = ButtonStruct(True,True,0,None,None,button,0,False,False,relay)

    def createButtonOnOff(parent,layout,linkName,x,y,cycled,relay):
        button = QLabel(parent)
        button.setPixmap(parent.pixmapOff)
        button.setFixedSize(parent.pixmapOff.width(),parent.pixmapOff.height())
        layout.addWidget(button,y,x,1,1)

        if cycled :
            cycleTimeSpinner = QSpinBox()
            cycleTimeSpinner.setMinimum(0)
            cycleTimeSpinner.setMaximum(5)
            cycleTimeSpinner.setFont(QFont('Times', 20)) 
            cycleTimeSpinner.setFixedSize(120,80)
            #cycleTimeSpinner.setStyleSheet("background-color: rgb(199,217,252);border: 0px solid black;QSpinBox::up-button{width:60px;}QSpinBox::down-button{width:60px;}")
            cycleTimeSpinner.setStyleSheet("QSpinBox::up-button{width:60px;}QSpinBox::down-button{width:60px;}QSpinBox::")
            cycleTimeSpinner.setAlignment(Qt.AlignCenter)
            cycleTimeLabel = QLabel("CYCLE TIME\nMINUTES",parent)
            cycleTimeLabel.setFont(QFont('Times', 10)) 
            cycleTimeLabel.setFixedSize(120,40)
            cycleTimeLabel.setStyleSheet("background-color: rgb(199,217,252);border: 0px solid black;")
            cycleTimeLabel.setAlignment(Qt.AlignCenter)
            layout.addWidget(cycleTimeLabel,y+2,x,1,1)
            layout.addWidget(cycleTimeSpinner,y+3,x,1,1)
            timer = QTimer()
            timer.timeout.connect(lambda: parent.buttonTimer(button,linkName))
            parent.buttonDict[linkName] = ButtonStruct(True,True,0,cycleTimeSpinner,
                timer,button,0,False,True,relay)
        else :
            parent.buttonDict[linkName] = ButtonStruct(True,True,0,None,None,button,0,False,True,relay)

    def createLabel(parent,name,layout,linkName,x,y):
        label = QLabel(name,parent)
        label.setFont(QFont('Times', 10)) 
        label.setFixedSize(120,40)
        label.setStyleSheet("background-color: rgb(199,217,252);border: 0px solid black;")
        label.setAlignment(Qt.AlignCenter)

        layout.addWidget(label,y,x,1,1,Qt.AlignCenter)
        parent.labelDict[linkName] = label

    def onoff(self,button,linkName):
        print(linkName)
        global relayArray
        buttonDef = self.buttonDict[linkName]
        print(buttonDef)
        if buttonDef.momentary :
            buttonDef.button.setPixmap(self.pixmapBlue)             
            relayArray[buttonDef.relay].value = True
        elif buttonDef.isOff :
            print("turn on")
            buttonDef.button.setPixmap(self.pixmapBlue)
            relayArray[buttonDef.relay].value = True
            list = self.buttonLinks[linkName]
            if list != None:
                for x in list:
                    linkButtonDef = self.buttonDict[x]
                    linkButtonDef.button.setPixmap(self.pixmapOff)
                    relayArray[linkButtonDef.relay].value = True
                    if linkButtonDef.buttonTimer != None :
                        linkButtonDef.buttonTimer.stop()   
                    self.buttonDict[x] = ButtonStruct(True,True,0,linkButtonDef.cycleSpinner,
                        linkButtonDef.buttonTimer,linkButtonDef.button,0,linkButtonDef.momentary,True,
                        linkButtonDef.relay)
            if buttonDef.buttonTimer!= None:
                buttonDef.buttonTimer.start(1000)
                self.buttonDict[linkName] = ButtonStruct(True,True,0,buttonDef.cycleSpinner,
                    buttonDef.buttonTimer,buttonDef.button,buttonDef.cycleSpinner.value(),
                    buttonDef.momentary,False,buttonDef.relay)
            else :              
                buttonDef = self.buttonDict[linkName]
                self.buttonDict[linkName] = ButtonStruct(True,True,0,buttonDef.cycleSpinner,
                    buttonDef.buttonTimer,buttonDef.button,0,
                    buttonDef.momentary,False,buttonDef.relay)
        else :
            print("turn off")
            buttonDef.button.setPixmap(self.pixmapOff)
            relayArray[buttonDef.relay].value = False
            if buttonDef.buttonTimer!= None:
                 self.buttonDict[linkName].buttonTimer.stop()
                 buttonDef = self.buttonDict[linkName]
                 self.buttonDict[linkName] = ButtonStruct(True,True,0,buttonDef.cycleSpinner,
                     buttonDef.buttonTimer,buttonDef.button,0,buttonDef.momentary,True,
                     buttonDef.relay)
            else :
                self.buttonDict[linkName] = ButtonStruct(True,True,0,buttonDef.cycleSpinner,
                     buttonDef.buttonTimer,buttonDef.button,0,buttonDef.momentary,True,
                     buttonDef.relay)
    
    
    def off(self,button,linkName):
        buttonDef = self.buttonDict[linkName]
        if buttonDef.momentary :
            button.setPixmap(self.pixmapOff)             
            relayArray[buttonDef.relay].value = False
             
    def pressed(self,button):
            button.setIcon(QIcon("marine push button 4 on blue clean.png"))

    def released(self,button):
            button.setIcon(QIcon("marine push button 4 off clean.png"))

    def buttonTimer(self,button,linkName):
        #print("button timer ",linkName)
        buttonDef = self.buttonDict[linkName];
        if buttonDef.state :
            button.setPixmap(self.pixmapBlue)
            self.buttonDict[linkName] = ButtonStruct(False,buttonDef.cycleState,buttonDef.cycleTimer+1,
                buttonDef.cycleSpinner,buttonDef.buttonTimer,buttonDef.button,buttonDef.cycleTime,
                buttonDef.momentary,buttonDef.isOff,buttonDef.relay)
        else :
            if self.buttonDict[linkName].cycleState:
                button.setPixmap(self.pixmapGreen)
                self.buttonDict[linkName] = ButtonStruct(True,buttonDef.cycleState,buttonDef.cycleTimer+1,
                    buttonDef.cycleSpinner,buttonDef.buttonTimer,buttonDef.button,buttonDef.cycleTime,
                    buttonDef.momentary,buttonDef.isOff,buttonDef.relay)
            else :
                button.setPixmap(self.pixmapRed)
                self.buttonDict[linkName] = ButtonStruct(True,buttonDef.cycleState,buttonDef.cycleTimer+1,
                    buttonDef.cycleSpinner,buttonDef.buttonTimer,buttonDef.button,buttonDef.cycleTime,
                    buttonDef.momentary,buttonDef.isOff,buttonDef.relay)
        #print(buttonDef.cycleTimer)  
        if buttonDef.cycleTime > 0 :
            if buttonDef.cycleTimer > buttonDef.cycleTime*60:
                self.buttonDict[linkName] = ButtonStruct(buttonDef.state,not buttonDef.cycleState,0,buttonDef.cycleSpinner,
                buttonDef.buttonTimer,buttonDef.button,buttonDef.cycleTime,
                buttonDef.momentary,buttonDef.isOff,buttonDef.relay)

    def findTouchScreen(self):
        device_dir='/dev/input'
        devices = list_devices(device_dir)
        devices = [InputDevice(path) for path in devices]
        if not devices:
            msg = 'error: no input devices found (do you have rw permission on %s/*?)'
            #print(msg % device_dir, file=sys.stderr)
            sys.exit(1)
        for num, dev in enumerate(devices):
            #print(dev.name)
            if dev.name == "ADS7846 Touchscreen" :
                 global touchDevice
                 touchDevice  = dev
    def moveEvent(self,e):
        print(self.pos())
        self.windowPos = self.pos()


    def onQApplicationStarted(self) :
        self.windowPos = self.pos()
        keys = list(self.buttonDict)
        for key in keys :
            button = self.buttonDict[key].button
    
    def closeEvent(self,event) :
        global stopThreads
        stopThreads = True
        
if __name__ == "__main__":
    #global i2c
    i2c = busio.I2C(board.SCL, board.SDA)
    #global mcp1
    mcp1 = MCP23017(i2c)
    #mcp2 = MCP23017(i2c, address=0x24)    
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    t = QTimer()
    t.singleShot(0,window.onQApplicationStarted)
    sys.exit(app.exec())
    stopThreads = True
