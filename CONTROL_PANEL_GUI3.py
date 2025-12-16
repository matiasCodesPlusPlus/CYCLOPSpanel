"""MAIN file for control panel:
    created for GSFC - 665 CYCLOPS cryostat by Matias Calderon
    
    DO immediately
    --------------
    TODO: heater controls (TEST READY)
    TODO: file convention for camera images, preferably based on camera location along stage 
    
    NOT immediately
    --------------
    TODO: reconnection to peripherals if connection lost
    TODO: C++ level connectflags for MICROXCAM
    TODO: Cryostat Warm up command set (using heaters) 

"""
#general imports
import sys
# sys.path.append("C:\\CYCLOPSpanel\\include")

import csv
import pyvisa as pv
from datetime import datetime as dt
import sys
import serial
import serial.tools.list_ports
import os
from random import randint
import numpy as np
import threading

from packages.pressure_sensor import pressureSensor as PS
from collections import deque
#instrumentation imports
try:
    from packages import MICROXCAM_gsfchirmes as MX
except FileNotFoundError:
    print("use gsfc fresco for real testing")
from packages import LAKESHORE340 as LS340
from packages import NRT100 as NRT100
from packages import K2220G as K2220G
from packages import KS33600A
#GUI Package imports
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QStatusBar
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QRadioButton
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QLCDNumber
from PyQt5.QtWidgets import QFrame
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QTabBar
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QColor
from PyQt5 import QtCore
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import time
from packages.MoutInterpolator import create_manual_output_interpolator

class _FILEsystemPopUp(QDialog):

    def __init__(self, parent = None):
        super().__init__(parent)
        self.setWindowTitle(" CYCLOPS FILE SYSTEM")
        layout = QVBoxLayout()
        self.label = QLabel("CHOOSE COOLDOWN FILE OR CREATE NEW\n============================================", self)
        self.activeCooldownLabel = QLabel(f"THE ACTIVE COOLDOWN FILE IS FROM: \n {self._FILEmanager("load")}")
        self.useActiveButton = QPushButton("USE ACTIVE")
        self.newButton = QPushButton("NEW COOLDOWN")
        
        
        self.useActiveButton.setFont(QFont("Arial",10))
        self.useActiveButton.setFixedSize(250,50)
        self.useActiveButton.clicked.connect(self._load_and_close)

        self.newButton.setFont(QFont("Arial",10))
        self.newButton.setFixedSize(250,50)
        self.newButton.clicked.connect(self._create_and_close)
        #self.periph_connect_button.setStyleSheet("background-color: red")
       

        hButtonLay = QHBoxLayout()
        hButtonLay.addWidget(self.useActiveButton)
        hButtonLay.addWidget(self.newButton)
        

        layout.addWidget(self.label)
        layout.addWidget(self.activeCooldownLabel)
        layout.addLayout(hButtonLay)
        #layout.addWidget(self.label2)
        
        self.setLayout(layout)
        # Optional: set a specific size
        self.resize(500, 180)

    def _create_and_close(self):
        self._FILEmanager("create")
        self.close()
    def _load_and_close(self):
        self._FILEmanager("load")
        self.close()

    def checkFolder(self):
        return self.testID
    
    def _FILEmanager(self, action):
        self.USER = os.environ.get("USERNAME")
        """Use this function for any of the file handeling for this software, all actions can go thru this"""
        self.DATA_PIPE = f"C:\\Users\\{self.USER}\\Desktop\\CYCLOPS_DATA\\COOLDOWNS"

        if action == "create":
            """create a cooldown file - TODO: map this to correct buttons"""
            self.testID = f"{self.DATA_PIPE}\\CYCLOPS_RUN_{dt.now().strftime("%Y_%m_%d")}"
            with open(".\\localMEM\\local_cooldown.txt", "w") as cooldownFile:
                cooldownFile.writelines(self.testID)
        elif action == "load":
            """loads cooldown file from memory, this will be stored in //.localMEM"""
            if os.environ.get("USERNAME") == "gsfchirmes":
                with open(".\\localMEM\\local_cooldown.txt", "r") as cooldownFile:
                    self.testID = cooldownFile.readline()
                    cooldownFile.close()
            else:
                self.testID = "C:\\Users\\matia\\Desktop\\TEST_BLANK_DIR" #init a test empty dir
            return self.testID
        elif action == "create-sweep":
            self.sweepID = f"{self.testID}\\_SWEEP_{dt.now().strftime("%Y_%m_%d_%H_%M_%S")}"

class Window(QTabWidget):
    
    def __init__(self, parent = None):
        super().__init__(parent)
        self.cooldownDIR = False
        self.setWindowTitle("CYCLOPS - VIPA CONTROL PANEL")
        self.setFixedSize(2000,1500)
        self.voltage = 11.975
        self.connected = False 

        self.show_popup()
        self.testID = self.popup_dialog.checkFolder()
        
        try:
            self.get_manual_out = create_manual_output_interpolator(".\\manual_out_temps.csv")
        except ValueError:
            self.get_manual_out = 0
        ##file management
        #self.testID = f"CYCLOPS_RUN_{dt.now().strftime("%Y_%m_%d_%H_%M")}"
        if not os.path.exists(self.testID):
            self.testFolder = os.mkdir(self.testID)
        self.envDataFilePath = f".\\{self.testID}\\env_data_run_{dt.now().strftime("%Y_%m_%d_%H_%M")}.csv"
        self.recording = False

        self.mode = "Temp" # Temp or Power indicates servo mode
        self.data_rate = 1 #seconds per sample
        self.plot_dur = 1200 #plot duration in seconds
        self.ttarget4K1 = 4.0
        self.ttarget50K1 = 50.0
        self.pid_p = 0
        self.pid_i = 0
        self.pid_d = 0
        self.log_data = False
        self.log_filename = ""
        #sweep params----------------
        self.stage_dx = 5
        self.stage_loBound = 0
        self.stage_hiBound = 100
        self.frameCount = 60
        self.QCLtimerOffset = 1
        #---------------------------- These are edited in-program in the sweep control params menu
        #THERMOMETRY ----------------------------------------------------------------------------
        self.T4K1 = LS340.THERMOMETER("A", "CRVFILE4K", opTemp=4, location = "ON qcl")
        self.T4K2 = LS340.THERMOMETER("B", "CRVFILE4K",opTemp = 4, location = "4K Stage")
        self.T50K1 = LS340.THERMOMETER("A", "CRVFILE50K", opTemp = 50, location = '50K stage')
        self.T50K2 = LS340.THERMOMETER("B", "CRVFILE50K", opTemp = 50, location = '50K stage')
        self.T4K3 = LS340.THERMOMETER("C", "CRVFILE4K", opTemp = 4, location = 'in calibration (4K)')
        self.T4K4 = LS340.THERMOMETER("D", "CRVFIle4K", opTemp = 4, location = "4K plate")
        #HEATING PARAMS---------------------------------------------------------------------------------------------
        self.heating = False
        self.QCLtoggleState = 0

        self.heatstate = False
        self.Hrange = 0
        #pressure---------------------------------
        self.current_chamberPressure = 0
        self.starttime = time.time()
        #NRT100
        self.motor_position = 0
        #LAYOUT SETUP
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()

        
        self.addTab(self.tab1,"CONTROL")
        self.addTab(self._createMonitorLayout(), "MONITOR")
        self.addTab(self._createCameraLayout(), "CAMERA")

        self.generalLayout = QVBoxLayout()
        self.tab1.setLayout(self.generalLayout)
        layout = self._createLayout()
        self.apply_theme

        #TIMER SETUP
        self.timer = QtCore.QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.update_data)

        self.timer2 = QtCore.QTimer()
        self.timer2.setInterval(500)
        

    def _createLayout(self):
        """TOP ROW LAYOUT: 
            -> CAMERA CONNECTION
            -> K2220G CONNECTION
            -> NRT100 CONNECTION
            -> LS340 CONNECTION"""
        """RHS LAYOUT
        -> QCL CONTROLS
        -> SWEEP PARAMS
        -> SAVEFILE
        """
        """BOTTOM ROW LAYOUT:
            -> OUTPUT LINE INTERFACE"""
        #CAMERA CONNECTION----------------------------------------------------------------
        top_row = QHBoxLayout()
        self.controlBarWidth = 400

        #peripherals connection
        self.periph_connect_button = QPushButton("CONNECT PERIPHERALS")
        self.periph_connect_button.setFont(QFont("Arial",10))
        self.periph_connect_button.setFixedSize(300,40)
        self.periph_connect_button.setStyleSheet("background-color: red")
        self.periph_connect_button.clicked.connect(self.on_clicked_peripherals)

        #start data record button
        self.data_button = QPushButton("START DATA RECORD")
        self.data_button.setFont(QFont("Arial",10))
        self.data_button.setFixedSize(300,40)
        self.data_button.setStyleSheet("background-color: light blue")
        self.data_button.clicked.connect(self._begin_data)
        #motor control buttons
        self.motor_home_button = QPushButton("HOME STAGE")
        self.motor_home_button.setFont(QFont("Arial",10))
        self.motor_home_button.setFixedSize(150,40)
        self.motor_home_button.setStyleSheet("background-color: white") #TODO: change colors when motor needs to be homed, NRT100 code has stuff for this
        self.motor_home_button.clicked.connect(self.on_clicked_motor_home)

        #motor control buttons
        self.motor_sweep_button = QPushButton("SWEEP STAGE")
        self.motor_sweep_button.setFont(QFont("Arial",10))
        self.motor_sweep_button.setFixedSize(300,40)
        self.motor_sweep_button.setStyleSheet("background-color: white") #TODO: change colors when motor needs to be homed, NRT100 code has stuff for this
        self.motor_sweep_button.clicked.connect(self.on_clicked_motor_sweep)

        #motor distance input button--------------------------------------------------------------------
        self.pos_text = QTextEdit(self.tab1)
        self.pos_text.setObjectName("pos_text")
        self.pos_text.setFixedSize(75,40)
        self.pos_text.setFont(QFont("Arial",12))

        #motor current position label-------------------------------------------------------------------
        # self.motor_pos_lab = QLabel(self.tab1)
        # self.motor_pos_lab.setText("NRT100 at 0 mm")
        # self.motor_pos_lab.setFixedSize(300,40)
        # self.motor_pos_lab.setFont(QFont("Arial",16))

        #move motor to position button------------------------------------------------------------------
        self.motor_pos_button = QPushButton("MOVE TO POSITION")
        self.motor_pos_button.setFont(QFont("Arial",11))
        self.motor_pos_button.setFixedSize(225,40)
        self.motor_pos_button.setStyleSheet("background-color: white")
        self.motor_pos_button.clicked.connect(self.on_clicked_motor_move)
        #add buttons to row
        top_row.addWidget(self.periph_connect_button, alignment = Qt.AlignLeft)
        top_row.addWidget(self.data_button, alignment = Qt.AlignLeft)
        top_row.addWidget(self.motor_home_button, alignment = Qt.AlignLeft)
        top_row.addWidget(self.motor_sweep_button, alignment = Qt.AlignLeft)
        top_row.addWidget(self.pos_text)#, alignment = Qt.AlignLeft)
        top_row.addWidget(self.motor_pos_button)
        #top_row.addWidget(self.motor_pos_lab)
        self.generalLayout.addLayout(top_row)

        centerlayout = QHBoxLayout()
        #GRAPHING
        plotcenter = QHBoxLayout()
        self.times = []
        self.temps4K1 = []
        self.temps4K2 = []
        self.temps50K1 = []
        self.temps50K2 = []
        self.setpoint4K = []
        self.setpoint50K = []
        self.power = []

        pen = pg.mkPen(color='k', width=3)
        pen1 = pg.mkPen(color='r', width=3)
        pen2 = pg.mkPen(color='k', width=3, style=QtCore.Qt.DashLine)
        pen3 = pg.mkPen(color='b', width=3)
        pen4 = pg.mkPen(color = 'orange', width = 3)
        pen5 = pg.mkPen(color = 'dark green', width = 3)
        pen6 = pg.mkPen(color = 'violet', width = 3)
        self.tempWidget = pg.plot()#PlotWidget()
        self.tempWidget.setBackground('w')
        self.tempWidget.setLabel('bottom', 'Time', units='Min', **{'font-size':'12pt'})
        self.tempWidget.getAxis('bottom').setPen(pen)
        self.tempWidget.setLabel('left', 'Temp.', units='K', color="#d14116", **{'font-size':'12pt'})
        self.tempWidget.getAxis('left').setPen(pen1)
        self.tempWidget.setStyleSheet("border: 1px solid black;")

        self.temp_line4K1 = self.tempWidget.plot((np.array(self.times)-self.starttime)/60.0, self.temps4K1, pen=pen1)
        self.temp_line4K2 = self.tempWidget.plot((np.array(self.times)-self.starttime)/60.0, self.temps4K2, pen=pen4)
        self.temp_line50K1 = self.tempWidget.plot((np.array(self.times)-self.starttime)/60.0, self.temps50K1, pen=pen5)
        self.temp_line50K2 = self.tempWidget.plot((np.array(self.times)-self.starttime)/60.0, self.temps50K2, pen=pen6)

        self.setp_line4K = self.tempWidget.plot((np.array(self.times)-self.starttime)/60.0, self.setpoint4K, pen=pen2)
        # self.setp_line4K2 = self.tempWidget.plot((np.array(self.times)-self.starttime)/60.0, self.temps4K1, pen=pen4)
        self.setp_line50K = self.tempWidget.plot((np.array(self.times)-self.starttime)/60.0, self.setpoint50K, pen=pen2)
        # self.setp_line50K2 = self.tempWidget.plot((np.array(self.times)-self.starttime)/60.0, self.temps4K1, pen=pen2)



        #self.setpoint_line = self.tempWidget.plot((np.array(self.times)-self.starttime)/60.0, self.setpoint4K, pen=pen2)
        plotcenter.addWidget(self.tempWidget)
        centerlayout.addLayout(plotcenter)

        controlCenter = QVBoxLayout()
        QCL_control = QHBoxLayout()
        #QCL/Camera control
        #separating line
        self.separating_line1 = QFrame()
        self.separating_line1.setFrameShape(QFrame.HLine)
        #self.separating_line1.setStyleSheet("border: 2px dashed black;")
        self.separating_line1.setLineWidth(10)
        controlCenter.addWidget(self.separating_line1)

        #QCL ON/OFF
        self.QCL_controlButton = QPushButton()
        self.QCL_controlButton.setText("QCL (OFF)")
        self.QCL_controlButton.setFixedSize(int(1.5*self.controlBarWidth),40)
        self.QCL_controlButton.setStyleSheet("background-color: red")
        self.QCL_controlButton.setFont(QFont("Arial", 20))
        self.QCL_controlButton.clicked.connect(self._voltage_onOff)
        controlCenter.addWidget(self.QCL_controlButton, alignment = Qt.AlignTop)

        #separating line
        self.separating_line2 = QFrame()
        self.separating_line2.setFrameShape(QFrame.HLine)
        self.separating_line2.setStyleSheet("border: 2px dashed black;")
        self.separating_line2.setLineWidth(10)
        controlCenter.addWidget(self.separating_line2)

        #voltage set control label
        self.vset_label = QLabel()
        self.vset_label.setText("SET QCL VOLTAGE")
        self.vset_label.setFixedSize(self.controlBarWidth,40)
        self.vset_label.setStyleSheet("background-color: white")
        self.vset_label.setFont(QFont("Arial",12))
        controlCenter.addWidget(self.vset_label)
        #QCL Voltage Set
        self.QCL_voltSet = QTextEdit()
        self.QCL_voltSet.setFixedSize(int(self.controlBarWidth/2),40)
        self.QCL_voltSet.setFont(QFont("Arial", 12))
        QCL_control.addWidget(self.QCL_voltSet, alignment = Qt.AlignLeft)

        self.setVoltage = QPushButton()
        self.setVoltage.setText("SET VOLTAGE")
        self.setVoltage.setFont(QFont("Arial",6))
        self.setVoltage.setFixedSize(int(self.controlBarWidth),40)
        self.setVoltage.setStyleSheet("background-color: white")
        self.setVoltage.clicked.connect(self._grab_voltage)
        QCL_control.addWidget(self.setVoltage, alignment = Qt.AlignRight)

        controlCenter.addLayout(QCL_control)
        #separating line
        self.separating_line3 = QFrame()
        self.separating_line3.setFrameShape(QFrame.HLine)
        self.separating_line3.setStyleSheet("border: 2px dashed black;")
        self.separating_line3.setLineWidth(10)
        controlCenter.addWidget(self.separating_line3)
        MX_subControls = QHBoxLayout()
        #camera control label
        self.cam_label = QLabel()
        self.cam_label.setText("MICROXCAM 384-I CONTROLS")
        self.cam_label.setFixedSize(self.controlBarWidth,40)
        self.cam_label.setStyleSheet("background-color: white")
        self.cam_label.setFont(QFont("Arial",12))
        controlCenter.addWidget(self.cam_label)
        #Camera Control set
        #single image
        self.MXsimple = QPushButton()
        self.MXsimple.setText("SINGLE IMAGE")
        self.MXsimple.setFont(QFont("Arial",6))
        self.MXsimple.setFixedSize(int(self.controlBarWidth*.5),40)
        MX_subControls.addWidget(self.MXsimple)
        #flashed image
        self.MXflashed = QPushButton()
        self.MXflashed.setText("FLASHED IMAGE")
        self.MXflashed.setFont(QFont("Arial", 6))
        self.MXsimple.setFixedSize(int(self.controlBarWidth*.5),40)
        MX_subControls.addWidget(self.MXflashed)

        controlCenter.addLayout(MX_subControls)

        #separating line
        self.separating_line4 = QFrame()
        self.separating_line4.setFrameShape(QFrame.HLine)
        self.separating_line4.setStyleSheet("border: 2px dashed black;")
        self.separating_line4.setLineWidth(10)
        controlCenter.addWidget(self.separating_line4)

        #savefile label
        self.sv_label = QLabel()
        self.sv_label.setText("DIRECTORY TO SAVE IMAGES:")
        self.sv_label.setFixedSize(self.controlBarWidth,40)
        self.sv_label.setStyleSheet("background-color: white")
        self.sv_label.setFont(QFont("Arial",12))
        controlCenter.addWidget(self.sv_label)
        #save to line
        saveto_lay = QVBoxLayout()
        self.fileLocation = QTextEdit()
        self.fileLocation.setFixedSize(self.controlBarWidth,20)
        self.fileLocation.setFont(QFont("Arial",6))
        saveto_lay.addWidget(self.fileLocation, alignment = Qt.AlignTop)
        
        self.exploreButton = QPushButton()
        self.exploreButton.setFixedSize(self.controlBarWidth,20)
        self.exploreButton.setFont(QFont("Arial", 6))
        self.exploreButton.setText("REVEAL LOCATION IN FILE EXPLORER")
        self.exploreButton.clicked.connect(self.on_clicked_file_explore)
        saveto_lay.addWidget(self.exploreButton,alignment=Qt.AlignTop)
        controlCenter.addLayout(saveto_lay)
        #separating line
        self.separating_line5 = QFrame()
        self.separating_line5.setFrameShape(QFrame.HLine)
        self.separating_line5.setStyleSheet("border: 2px dashed black;")
        self.separating_line5.setLineWidth(10)
        controlCenter.addWidget(self.separating_line5)
#SWEEP CONTROLS--------------------------------------------------------------------------
        self.sweepFrame = QFrame()
        self.sweepFrame.setFrameShape(QFrame.Box)
        self.sweepFrame.setLineWidth(10)
        self.sweepFrame.setStyleSheet("QFrame { border: 2px solid dark green; background-color: white}")
        #params label
        self.sw_label = QLabel()
        self.sw_label.setText("NRT100 SWEEP CONTROL PARAMS:")
        self.sw_label.setFixedSize(self.controlBarWidth,40)
        self.sw_label.setStyleSheet("background-color: white")
        self.sw_label.setFont(QFont("Arial",12))
        controlCenter.addWidget(self.sw_label)

        sweepControls = QVBoxLayout()
        sweepControls1 = QHBoxLayout()
        sweepControls2 = QHBoxLayout()
        sweepControls3 = QHBoxLayout()
        sweepControls4 = QHBoxLayout()
        #sweep distance intervals
        self.set_sweep_dx = QTextEdit()
        self.set_sweep_dx.setFixedSize(int(self.controlBarWidth),75)
        self.set_sweep_dx.setFont(QFont("Arial", 20))

        self.set_sweep_dx_button = QPushButton()
        self.set_sweep_dx_button.setFixedSize(int(.5*self.controlBarWidth),75)
        self.set_sweep_dx_button.setText("SET dx (mm)")
        self.set_sweep_dx_button.setStyleSheet("background-color: white")
        self.set_sweep_dx_button.clicked.connect(self._grab_dx)

        #sweep bounds
        self.set_sweep_lowBound  = QTextEdit()
        self.set_sweep_lowBound.setFixedSize(int(.5*self.controlBarWidth),75)
        self.set_sweep_lowBound.setFont(QFont("Arial", 20))

        self.set_sweep_hiBound  = QTextEdit()
        self.set_sweep_hiBound.setFixedSize(int(.5*self.controlBarWidth),75)
        self.set_sweep_hiBound.setFont(QFont("Arial", 20))

        self.set_sweep_bounds = QPushButton()
        self.set_sweep_bounds.setFixedSize(int(.5*self.controlBarWidth),75)
        self.set_sweep_bounds.setText("SET BOUNDS")
        self.set_sweep_bounds.setStyleSheet("background-color: white")
        self.set_sweep_bounds.clicked.connect(self._grab_bounds)

        sweepControls4.addWidget(self.set_sweep_lowBound)
        sweepControls4.addWidget(self.set_sweep_hiBound)
        sweepControls4.addWidget(self.set_sweep_bounds)
        #frames input to camera
        self.set_frames = QTextEdit()
        self.set_frames.setFixedSize(int(self.controlBarWidth),75)
        self.set_frames.setFont(QFont("Arial", 20))

        self.set_frames_button = QPushButton()
        self.set_frames_button.setFixedSize(int(.5*self.controlBarWidth),75)
        self.set_frames_button.setText("SET Framecount")
        self.set_frames_button.setStyleSheet("background-color: white")
        self.set_frames_button.clicked.connect(self._grab_framecount)

        self.start_sweep_button = QPushButton()
        self.start_sweep_button.setFixedSize(int(1.5*self.controlBarWidth), 75)
        self.start_sweep_button.setText("BEGIN SWEEP")
        self.start_sweep_button.setStyleSheet("background-color: white")
        self.start_sweep_button.clicked.connect(self.on_clicked_motor_sweep)
#end sweep controls
#keysight signal gen controls--------------------------------------------------------------
        #frame setup
        self.ksFrame = QFrame(self)
        
        self.ksFrame.setFrameShape(QFrame.Box)
        self.ksFrame.setLineWidth(10)
        self.ksFrame.setStyleSheet("QFrame { border: 2px solid black; background-color: white}")

        #controls label
        self.kslabel = QLabel()
        self.kslabel.setText("KEYSIGHT SIGNAL GENERATOR CONTROLS")
        self.kslabel.setStyleSheet("background-color: white")
        self.kslabel.setFont(QFont("Arial",12))                       

        self.channel_controls = QHBoxLayout()
        self.channel1_controls = QVBoxLayout()
        self.channel2_controls = QVBoxLayout()  #necessary layouts for 2 - channel vertical lays
        
        #per channel control structure (want freq, phase)
        #channel 1 controls-------------------------------------------------
        self.kschan1_lab = QLabel()
        self.kschan1_lab.setText("CHANNEL 1")
        self.kschan1_lab.setFixedSize(int(.75*self.controlBarWidth),50)
        self.kschan1_lab.setFont(QFont("Arial", 10))


        #freq control - ch1
        self.kschan1_freq = QTextEdit()
        self.kschan1_freq.setFixedSize(int(1.5*self.controlBarWidth/4),50)
        self.kschan1_freq.setFont(QFont("Arial",10))

        self.kschan1_freq_button = QPushButton()
        self.kschan1_freq_button.setFixedSize(int(1.5*self.controlBarWidth/4), 50)
        self.kschan1_freq_button.setStyleSheet("background-color: white")
        self.kschan1_freq_button.setText("SET FREQ.")
        #self.kschan1_freq_button.clicked.connect()
        #phase control - ch1
        self.kschan1_phase = QTextEdit()
        self.kschan1_phase.setFixedSize(int(1.5*self.controlBarWidth/4),50)
        self.kschan1_phase.setFont(QFont("Arial",10))

        self.kschan1_phase_button = QPushButton()
        self.kschan1_phase_button.setFixedSize(int(1.5*self.controlBarWidth/4), 50)
        self.kschan1_phase_button.setStyleSheet("background-color: white")
        self.kschan1_phase_button.setText("SET PHASE (deg)")
        #self.kschan1_phase_button.clicked.connect()

        #packaging
        #freq
        self.kschan1Freq = QHBoxLayout()
        self.kschan1Freq.addWidget(self.kschan1_freq)
        self.kschan1Freq.addWidget(self.kschan1_freq_button)
        #phase
        self.kschan1Phase = QHBoxLayout()
        self.kschan1Phase.addWidget(self.kschan1_phase)
        self.kschan1Phase.addWidget(self.kschan1_phase_button)
        #channel 1
        self.channel1_controls.addWidget(self.kschan1_lab)
        self.channel1_controls.addLayout(self.kschan1Freq)
        self.channel1_controls.addLayout(self.kschan1Phase)

        #channel 2 controls-------------------------------------------------
        self.kschan2_lab = QLabel()
        self.kschan2_lab.setText("CHANNEL 2")
        self.kschan2_lab.setFixedSize(int(.75*self.controlBarWidth),50)
        self.kschan2_lab.setFont(QFont("Arial", 10))

        #freq control - ch1
        self.kschan2_freq = QTextEdit()
        self.kschan2_freq.setFixedSize(int(1.5*self.controlBarWidth/4),50)
        self.kschan2_freq.setFont(QFont("Arial",10))

        self.kschan2_freq_button = QPushButton()
        self.kschan2_freq_button.setFixedSize(int(1.5*self.controlBarWidth/4), 50)
        self.kschan2_freq_button.setStyleSheet("background-color: white")
        self.kschan2_freq_button.setText("SET FREQ.")
        #self.kschan2_freq_button.clicked.connect()
        #phase control - ch1
        self.kschan2_phase = QTextEdit()
        self.kschan2_phase.setFixedSize(int(1.5*self.controlBarWidth/4),50)
        self.kschan2_phase.setFont(QFont("Arial",10))

        self.kschan2_phase_button = QPushButton()
        self.kschan2_phase_button.setFixedSize(int(1.5*self.controlBarWidth/4), 50)
        self.kschan2_phase_button.setStyleSheet("background-color: white")
        self.kschan2_phase_button.setText("SET PHASE (deg)")
        #self.kschan2_phase_button.clicked.connect()

        #packaging - ch2
        #freq
        self.kschan2Freq = QHBoxLayout()
        self.kschan2Freq.addWidget(self.kschan2_freq)
        self.kschan2Freq.addWidget(self.kschan2_freq_button)
        #phase
        self.kschan2Phase = QHBoxLayout()
        self.kschan2Phase.addWidget(self.kschan2_phase)
        self.kschan2Phase.addWidget(self.kschan2_phase_button)
        #channel 2
        self.channel2_controls.addWidget(self.kschan2_lab)
        self.channel2_controls.addLayout(self.kschan2Freq)
        self.channel2_controls.addLayout(self.kschan2Phase)

        #packaging (KS)----------------------------------------------------------
        self.KSCONTROLS = QVBoxLayout()
        self.KSCONTROLS.addWidget(self.kslabel)
        self.channel_controls.addLayout(self.channel1_controls) #pack everything in
        self.channel_controls.addLayout(self.channel2_controls)
        self.KSCONTROLS.addLayout(self.channel_controls)
        self.ksFrame.setLayout(self.KSCONTROLS)

        #end ks controls----------------------------------------------------------------------------
        
        sweepControls1.addWidget(self.set_sweep_dx)
        sweepControls1.addWidget(self.set_sweep_dx_button)
        sweepControls2.addWidget(self.set_frames)
        sweepControls2.addWidget(self.set_frames_button)
        
        #sweepControls3.addWidget(self.qcl_timeOffset)
        #sweepControls3.addWidget(self.qcl_timeOffset_button)
        sweepControls.addLayout(sweepControls1)
        sweepControls.addLayout(sweepControls4)
        sweepControls.addLayout(sweepControls2)
        sweepControls.addLayout(sweepControls3)

        self.sweepFrame.setLayout(sweepControls)

        controlCenter.addWidget(self.sweepFrame)
        controlCenter.addWidget(self.start_sweep_button)
        
        #ks controls
        controlCenter.addWidget(self.ksFrame)


        #NRT100 POSITION
        self.NRTpos = QLabel()
        self.NRTpos.setText(f"NRT100 POSITION: {self.motor_position}")
        self.NRTpos.setFont(QFont("Arial,12"))
        self.NRTpos.setStyleSheet("background-color: white")
        self.NRTpos.setFixedSize(300,40)
        controlCenter.addWidget(self.NRTpos)

        #separating line
        self.separating_line6 = QFrame()
        self.separating_line6.setFrameShape(QFrame.HLine)
        #self.separating_line6.setStyleSheet("border: 2px dashed black;")
        self.separating_line6.setLineWidth(10)
        controlCenter.addWidget(self.separating_line6)


        centerlayout.addLayout(controlCenter)
        self.generalLayout.addLayout(centerlayout)
        
        #row to change PID settings
        
        self.pid_left = QVBoxLayout()
        self.pid_label = QHBoxLayout()
        
        self.pid_display = QLabel("Control Settings")
        self.pid_display.setFixedSize(260,30)
        self.pid_display.setFont(QFont("Arial",14))
        self.pid_display.setAlignment(QtCore.Qt.AlignCenter) 
        
        self.pid_label.addWidget(self.pid_display)
        
        self.b1 = QRadioButton("4K Plate")
        self.b1.setChecked(True)
        self.b1.setFont(QFont("Arial",14))
        #self.b1.toggled.connect(lambda:self.btnstate(self.b1))
        self.pid_label.addWidget(self.b1)
            
        self.b2 = QRadioButton("QCL Ctrl")
        self.b2.setFont(QFont("Arial",14))

        self.b3 = QRadioButton("50K Plate")
        self.b3.setFont(QFont("Arial",14))

        self.b4 = QRadioButton("VIPA")
        self.b4.setFont(QFont("Arial",14))

        #warm up
        #Write Button
        self.warm_up_button = QPushButton("WARM UP")
        #self.write_pid_button.setAlignment(QtCore.Qt.AlignCenter)
        self.warm_up_button.setFixedSize(100,30)
        self.warm_up_button.setFont(QFont("Arial",12))
        self.warm_up_button.clicked.connect(self._on_clicked_warmUP)
        


        #self.b2.toggled.connect(lambda:self.btnstate(self.b2))
        self.pid_label.addWidget(self.b2)
        self.pid_label.addWidget(self.b3)
        self.pid_label.addWidget(self.b4)
        self.pid_label.addWidget(self.warm_up_button)
        self.read_pid_button = QPushButton("Read")
        #self.write_pid_button.setAlignment(QtCore.Qt.AlignCenter)
        self.read_pid_button.setFixedSize(100,30)
        self.read_pid_button.setFont(QFont("Arial",12))
        self.read_pid_button.clicked.connect(self.read_pid_settings)
        self.pid_label.addWidget(self.read_pid_button)
        
        #Write Button
        self.write_pid_button = QPushButton("Write")
        #self.write_pid_button.setAlignment(QtCore.Qt.AlignCenter)
        self.write_pid_button.setFixedSize(100,30)
        self.write_pid_button.setFont(QFont("Arial",12))
        self.write_pid_button.clicked.connect(self.write_pid_settings)
        self.pid_label.addWidget(self.write_pid_button)
        
        self.pid_left.addLayout(self.pid_label)
        
        self.pid_settings_row = QHBoxLayout()
        
        #PWOUT
        self.ptarget_display = QLabel("Set Power (W)")
        self.ptarget_display.setFixedSize(200,30)
        self.ptarget_display.setFont(QFont("Arial",12))
        self.ptarget_display.setAlignment(QtCore.Qt.AlignCenter) 
        
        self.ptarget_input = QLineEdit()
        self.ptarget_input.setValidator(QDoubleValidator(0.0, 1000.0, 6, notation=QDoubleValidator.StandardNotation))
        self.ptarget_input.setAlignment(QtCore.Qt.AlignCenter)
        self.ptarget_input.setFixedSize(80,30)
        self.ptarget_input.setFont(QFont("Arial",12))
        self.ptarget_input.setStyleSheet("border: 1px solid black; color : black;")
        self.ptarget_input.setText(str(self.ttarget50K1))
        
        #T Target
        self.ttarget_display = QLabel("Set Temp. (K)")
        self.ttarget_display.setFixedSize(200,30)
        self.ttarget_display.setFont(QFont("Arial",12))
        self.ttarget_display.setAlignment(QtCore.Qt.AlignCenter) 
        
        self.ttarget_input = QLineEdit()
        self.ttarget_input.setValidator(QDoubleValidator(0.0, 1000.0, 6, notation=QDoubleValidator.StandardNotation))
        self.ttarget_input.setAlignment(QtCore.Qt.AlignCenter)
        self.ttarget_input.setFixedSize(80,30)
        self.ttarget_input.setFont(QFont("Arial",12))
        self.ttarget_input.setStyleSheet("border: 1px solid black; color : black;")
        self.ttarget_input.setText(str(self.ttarget4K1))
        
        #P
        self.p_display = QLabel("P")
        self.p_display.setFixedSize(20,30)
        self.p_display.setFont(QFont("Arial",12))
        self.p_display.setAlignment(QtCore.Qt.AlignCenter) 
        
        self.p_input = QLineEdit()
        self.p_input.setValidator(QDoubleValidator(0.0, 1000.0, 6, notation=QDoubleValidator.StandardNotation))
        self.p_input.setAlignment(QtCore.Qt.AlignCenter)
        self.p_input.setFixedSize(80,30)
        self.p_input.setFont(QFont("Arial",12))
        self.p_input.setStyleSheet("border: 1px solid black; color : black;")
        self.p_input.setText(str(self.pid_p))
        
        #I
        self.i_display = QLabel("I")
        self.i_display.setFixedSize(20,30)
        self.i_display.setFont(QFont("Arial",12))
        self.i_display.setAlignment(QtCore.Qt.AlignCenter) 
        
        self.i_input = QLineEdit()
        self.i_input.setValidator(QDoubleValidator(0.0, 1000.0, 6, notation=QDoubleValidator.StandardNotation))
        self.i_input.setAlignment(QtCore.Qt.AlignCenter)
        self.i_input.setFixedSize(80,30)
        self.i_input.setFont(QFont("Arial",12))
        self.i_input.setStyleSheet("border: 1px solid black; color : black;")
        self.i_input.setText(str(self.pid_i))
        
        #D
        self.d_display = QLabel("D")
        self.d_display.setFixedSize(20,30)
        self.d_display.setFont(QFont("Arial",12))
        self.d_display.setAlignment(QtCore.Qt.AlignCenter) 
        
        self.d_input = QLineEdit()
        self.d_input.setValidator(QDoubleValidator(0.0, 1000.0, 6, notation=QDoubleValidator.StandardNotation))
        self.d_input.setAlignment(QtCore.Qt.AlignCenter)
        self.d_input.setFixedSize(80,30)
        self.d_input.setFont(QFont("Arial",12))
        self.d_input.setStyleSheet("border: 1px solid black; color : black;")
        self.d_input.setText(str(self.pid_d))
        
        self.pid_settings_row.addWidget(self.ptarget_display)
        self.pid_settings_row.addWidget(self.ptarget_input)
        self.pid_settings_row.addWidget(self.ttarget_display)
        self.pid_settings_row.addWidget(self.ttarget_input)
        self.pid_settings_row.addWidget(self.p_display)
        self.pid_settings_row.addWidget(self.p_input)
        self.pid_settings_row.addWidget(self.i_display)
        self.pid_settings_row.addWidget(self.i_input)
        self.pid_settings_row.addWidget(self.d_display)
        self.pid_settings_row.addWidget(self.d_input)
        
        self.pid_left.addLayout(self.pid_settings_row)
        
       
        self.generalLayout.addLayout(self.pid_left)
        
        
        #TEMP MONITORING
        data_rows = QVBoxLayout()
        next_row = QHBoxLayout()
        #temp display
        self.temp_display4K = QLabel()#QLCDNumber()
        self.temp_display4K.setFixedSize(400,50)
        self.temp_display_font = self.temp_display4K.font()
        self.temp_display_font.setPointSize(20)
        self.temp_display4K.setFont(self.temp_display_font)
        self.temp_display4K.setStyleSheet("border: 2px solid black; color : red;") 
        self.temp_display4K.setAlignment(QtCore.Qt.AlignCenter) 
        self.current_T4K1 = 0.0
        self.temp_display4K.setText("T<sub>4K1</sub> = %.2fK"%self.current_T4K1)
        #rej temp display
        self.temp_display50K = QLabel()#QLCDNumber()
        self.temp_display50K.setFixedSize(400,50)
        self.rej_display_font = self.temp_display50K.font()
        self.rej_display_font.setPointSize(20)
        self.temp_display50K.setFont(self.rej_display_font)
        self.temp_display50K.setStyleSheet("border: 2px solid black; color : green;") 
        self.temp_display50K.setAlignment(QtCore.Qt.AlignCenter) 
        self.rej_temp = 0.0
        self.temp_display50K.setText("T<sub>50K1</sub> = %.2fK"%self.rej_temp)
        #pow display
        self.pow_display = QLabel()#QLCDNumber()
        self.pow_display.setFixedSize(400,50)
        self.pow_display_font = self.pow_display.font()
        self.pow_display_font.setPointSize(20)
        self.pow_display.setFont(self.pow_display_font)
        self.pow_display.setStyleSheet("border: 2px solid black; color : blue;")
        self.pow_display.setAlignment(QtCore.Qt.AlignCenter)        
        self.current_pow = 0.0
        self.pow_display.setText("P<sub>HEAT_QCL</sub> = %.2fW"%self.current_pow)
        #heater 2 display
        self.pow_display_4K = QLabel()
        self.pow_display_4K.setFixedSize(400,50)
        self.pow_display_font = self.pow_display_4K.font()
        self.pow_display_font.setPointSize(20)
        self.pow_display_4K.setFont(self.pow_display_font)
        self.pow_display_4K.setStyleSheet("border: 2px solid black; color : green;")
        self.pow_display_4K.setAlignment(QtCore.Qt.AlignCenter)        
        self.current_pow2 = 0.0
        self.pow_display_4K.setText("P<sub>HEAT_4K</sub> = %.2fW"%self.current_pow2)

        self.heaterswitch = QPushButton()
        self.heaterswitch.setFixedSize(400,50)
        self.heaterswitch.setText("QCL HEATER (OFF)")
        self.heaterswitch.setStyleSheet("background-color: red")
        self.heaterswitch.clicked.connect(self.htrmanager)
        
        
        #self.open_all_button.setFixedSize(318,30)
        #self.open_all_button.setStyleSheet("background-color:#f77357")
        #self.open_all_button.setStyleSheet("QPushButton{background-color : #f77357;}QPushButton::pressed{background-color : red;}")
        #self.open_all_button.clicked.connect(self.open_all_ports)
        next_row.addWidget(self.temp_display4K)
        next_row.addWidget(self.temp_display50K)
        next_row.addWidget(self.pow_display)
        next_row.addWidget(self.pow_display_4K)
        data_rows.addLayout(next_row)
        #self.generalLayout.addLayout(next_row)

        next_row2 = QHBoxLayout()
        next_row2.addWidget(self.heaterswitch)

        #pressure display
        self.pressDisp = QLabel()
        self.pressDisp.setFixedSize(400,50)
        # self.temp_display_font2 = self.temp_display4K2.font()
        # self.temp_display_font2.setPointSize(20)
        self.pressDisp.setFont(self.temp_display_font)
        self.pressDisp.setStyleSheet("border: 2px solid black; color : orange;") 
        self.pressDisp.setAlignment(QtCore.Qt.AlignCenter) 
        self.pressDisp.setText("P<sub>CH</sub> = %.6fTorr"%self.current_chamberPressure)

                #temp display
        self.temp_display4K2 = QLabel()#QLCDNumber()
        self.temp_display4K2.setFixedSize(400,50)
        self.temp_display_font2 = self.temp_display4K2.font()
        self.temp_display_font2.setPointSize(20)
        self.temp_display4K2.setFont(self.temp_display_font2)
        self.temp_display4K2.setStyleSheet("border: 2px solid black; color : orange;") 
        self.temp_display4K2.setAlignment(QtCore.Qt.AlignCenter) 
        self.current_T4K2 = 0.0
        self.temp_display4K2.setText("T<sub>4K2</sub> = %.2fK"%self.current_T4K1)
        #rej temp display
        self.temp_display50K2 = QLabel()#QLCDNumber()
        self.temp_display50K2.setFixedSize(400,50)
        self.rej_display_font2 = self.temp_display50K2.font()
        self.rej_display_font2.setPointSize(20)
        self.temp_display50K2.setFont(self.rej_display_font2)
        self.temp_display50K2.setStyleSheet("border: 2px solid black; color : violet;") 
        self.temp_display50K2.setAlignment(QtCore.Qt.AlignCenter) 
        self.rej_temp2 = 0.0
        self.temp_display50K2.setText("T<sub>50K2</sub> = %.2fK"%self.rej_temp2)

        next_row2.addWidget(self.temp_display4K2)
        next_row2.addWidget(self.temp_display50K2)
        next_row2.addWidget(self.pressDisp)
        data_rows.addLayout(next_row2)
        self.generalLayout.addLayout(data_rows)

        #TEXT WINDOW
        bottom_row = QHBoxLayout()
        self.textEdit = QTextEdit(self.tab1)
        self.textEdit.setObjectName("textEdit")
        self.textEdit.setFixedSize(750,100)
        #self.textEdit.move(25,650)

        
        self.textEdit.alignment()
        #self.textEdit.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)
        bottom_row.addWidget(self.textEdit, alignment=Qt.AlignLeft| Qt.AlignBottom)
        #bottom_row.addWidget(self.CRVBURN)
        self.generalLayout.addLayout(bottom_row)
        #self.camera_connect_button.clicked.connect(MX.MICROXCAM)

        periph_checker = QVBoxLayout()
        self.pcheck_label = QLabel()
        self.pcheck_label.setText("PERIPHERAL STATUS ------------------------------")
        self.pcheck_label.setStyleSheet('background-color: white')
        self.pcheck_label.setFont(QFont("Arial", 10))

        periph_toprow = QHBoxLayout()
        periph_botrow = QHBoxLayout()

        self.K2220G_label = QLabel()
        self.K2220G_label.setText("   K2220G PWR SPLY")
        self.K2220G_label.setFont(QFont("Arial", 10))
        self.K2220G_label.setStyleSheet("background-color: red")
        self.K2220G_label.setFixedSize(200,35)

        self.MICROXCAM_label = QLabel()
        self.MICROXCAM_label.setText("   MICROXCAM")
        self.MICROXCAM_label.setFont(QFont("Arial", 10))
        self.MICROXCAM_label.setStyleSheet("background-color: red")
        self.MICROXCAM_label.setFixedSize(200,35)

        self.NRT100_label = QLabel()
        self.NRT100_label.setText("   NRT100")
        self.NRT100_label.setFont(QFont("Arial", 10))
        self.NRT100_label.setStyleSheet("background-color: red")
        self.NRT100_label.setFixedSize(200,35)

        LS340_pack = QHBoxLayout()
        self.LS340_label = QLabel()
        self.LS340_label.setText("LS340 TC")
        self.LS340_label.setFont(QFont("Arial", 10))
        self.LS340_label.setStyleSheet("background-color: red")
        self.LS340_label.setFixedSize(100,35)

        self.LSTC_1 = QLabel()
        self.LSTC_1.setText("1")
        self.LSTC_1.setFont(QFont("Arial", 10))
        self.LSTC_1.setStyleSheet("background-color: red")
        self.LSTC_1.setFixedSize(50,35)
        
        self.LSTC_2 = QLabel()
        self.LSTC_2.setText("2")
        self.LSTC_2.setFont(QFont("Arial", 10))
        self.LSTC_2.setStyleSheet("background-color: red")
        self.LSTC_2.setFixedSize(50,35)

        LS340_pack.addWidget(self.LS340_label)
        LS340_pack.addWidget(self.LSTC_1)
        LS340_pack.addWidget(self.LSTC_2)


        periph_toprow.addWidget(self.K2220G_label)
        periph_toprow.addWidget(self.MICROXCAM_label)

        periph_botrow.addWidget(self.NRT100_label)
        periph_botrow.addLayout(LS340_pack)



        periph_checker.addWidget(self.pcheck_label)
        periph_checker.addLayout(periph_toprow)
        periph_checker.addLayout(periph_botrow)

        bottom_row.addLayout(periph_checker)

        #separating line
        self.separating_line = QFrame()
        self.separating_line.setFrameShape(QFrame.HLine)
        self.separating_line.setLineWidth(10)
        self.generalLayout.addWidget(self.separating_line)

    def _createMonitorLayout(self):
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect  # or PyQt6 equivalent
        from PyQt5.QtGui import QColor

        widget = QWidget()
        layout = QGridLayout(widget)

        plot_labels = ["T4K1", "T4K2", "T50K1", "T50K2", "Chamber Pressure", "Heater Power"]
        self.parameter_plots = {}
        self.parameter_curves = {}
        self.parameter_data = {}

        history_len = 500

        for i, label in enumerate(plot_labels):
            # --- Create the plot ---
            plot = pg.PlotWidget(title=label)
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setLabel('bottom', 'Time (s)')
            plot.setLabel('left', label)
            curve = plot.plot(pen=pg.mkPen(width=2))

            self.parameter_plots[label] = plot
            self.parameter_curves[label] = curve
            self.parameter_data[label] = {
                'x': deque(maxlen=history_len),
                'y': deque(maxlen=history_len)
            }

            # --- Wrap in a styled frame ---
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    border-radius: 15px;
                    background-color: #1e1e1e;  /* slightly lighter than window bg */
                    border: 1px solid #444;
                }
            """)
            frame_layout = QVBoxLayout(frame)
            frame_layout.addWidget(plot)
            frame_layout.setContentsMargins(5, 5, 5, 5)

            # --- Optional drop shadow ---
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setOffset(0, 4)
            shadow.setColor(QColor(0, 0, 0, 160))
            frame.setGraphicsEffect(shadow)

            # --- Add to grid ---
            row, col = divmod(i, 2)
            layout.addWidget(frame, row, col)

        widget.setLayout(layout)
        return widget

    def _createCameraLayout(self):
        self.TABlabel = QLabel()
        self.TABlabel.setText("CAMERA FEED")

    def apply_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f8f8;
                color: #222;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11pt;
            }

            QPushButton {
                background-color: #ffffff;
                border: 1px solid #bbb;
                border-radius: 8px;
                padding: 5px 12px;
            }

            QPushButton:hover {
                background-color: #f0f0f0;
            }

            QPushButton:pressed {
                background-color: #e0e0e0;
            }

            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #ffffff;
                border: 1px solid #bbb;
                border-radius: 6px;
                padding: 4px;
            }

            QLabel {
                color: #222;
                font-weight: 500;
            }

            QTabWidget::pane {
                border-top: 2px solid #ccc;
                background-color: #f8f8f8;
                border-radius: 10px;
            }

            QTabBar::tab {
                background: #ececec;
                border: 1px solid #ccc;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 6px 14px;
                margin-right: 2px;
            }

            QTabBar::tab:selected {
                background: #ffffff;
                border-bottom-color: #ffffff;
                font-weight: 600;
            }

            QScrollBar:vertical {
                border: none;
                background: #eee;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }

            QScrollBar::handle:vertical {
                background: #ccc;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical:hover {
                background: #aaa;
            }
        """)



    #Non-blocking (multithreading) functions
    @QtCore.pyqtSlot()
    def _simple_image(self):
        path = self.fileLocation.toPlainText()
        if os.path.exists(path) == True:
            os.startfile(path)
        else:
            os.mkdir(path)
            os.startfile(path)
        image = path+"\\simple_image.csv"
        self.microxcam.simple_image(image)
    @QtCore.pyqtSlot()
    def _image_proc(self):
        path = self.fileLocation.toPlainText()
        if os.path.exists(path) == True:
            os.startfile(path)
        else:
            os.mkdir(path)
            os.startfile(path)
        ONimage = path+"\\qclOFF.csv"
        OFFimage = path+"\\qclON.csv"
        self.microxcam.image_proc(path,ONimage,OFFimage,60)
    @QtCore.pyqtSlot()
    def on_clicked_peripherals(self):
        #threading.Thread(target=self._connectPeripherals, daemon=True).start()
        self._connectPeripherals()
        time.sleep(2)
        self.timer.start()
        self.update_output_interface("Starting Data Acquisition Loop...")
    @QtCore.pyqtSlot(str)
    def update_output_interface(self, message):
        self.textEdit.append(f"{dt.now().strftime("%Y-%m-%d %H:%M:%S")} :: {message}")

    @QtCore.pyqtSlot()
    def on_clicked_motor_home(self):
        self.update_output_interface("HOMING NRT100 STAGE....")
        self.NRT100.home_stage()
        self.update_output_interface("DONE!!")
    def motor_home(self):
        self.textEdit.append('Homing NRT100 Stage.....')
        self.NRT100.home_stage()
        self.textEdit.append('Done!')

    @QtCore.pyqtSlot()
    def on_clicked_motor_move(self):
        self.NRT100.movetodist(float(self.pos_text.toPlainText()))
        #self.update_output_interface(f"Moving NRT100 stage to {self.motor_pos_button.toPlainText()} mm")
    @QtCore.pyqtSlot()
    def on_clicked_motor_sweep(self):
        threading.Thread(target = self.motor_sweep, daemon = True).start()
    @QtCore.pyqtSlot()
    def motor_sweep(self):

        self.K2220G.OUTPUT_ON()
        self.start_sweep_button.setText("SWEEP IN PROGRESS..")
        self.start_sweep_button.setStyleSheet("background-color: red")

        """Moves motor along sweep parameters as user input in application"""
        print("thread init successful")

        move = float(self.stage_loBound)
        #move = 5.
        self.NRT100.movetodist(move)
        sweepfolder = f"{self.testID}\\SWEEP_{dt.now().strftime("%Y_%m_%d_%H_%M_%S")}"
        os.mkdir(sweepfolder)

        #self.NRT100.wait(0)
        print(f"loBound: {move} hiBound: {float(self.stage_hiBound)}")
        #self.update_output_interface(f"Sweeping Camera Position over increment: {self.stage_dx} mm")
        motorSweepTimerStart = time.time()
        
        self.motorSweepCounter = 0
        self.update_output_interface(f"Sweep Started. Estimated Time Remaining = {self.frameCount/4 * (self.stage_hiBound-self.stage_loBound)/self.stage_dx}")
        while move < float(self.stage_hiBound): 
            self.NRT100.movetodist(move)
            #camera stuff here
            imagefolder = f"{sweepfolder}\\IMG_{move}"
            os.mkdir(imagefolder)
            motorStaticTimeStart = time.time()
            #self.microxcam.qcl_chop(f"{imagefolder}\\imageON.csv", f"{imagefolder}\\imageOFF.csv", self.numFrames)
            

                #self.microxcam.cam_proc(f"{imagefolder}\\image_{i}\\imageON.csv",f"{imagefolder}\\image_{i}\\imageOFF.csv",60, self.K2220G)
            self.microxcam.qcl_chop(f"{imagefolder}\\imageON.csv", f"{imagefolder}\\imageOFF.csv", int(self.frameCount))
            
            
            motorStaticTime = time.time() - motorStaticTimeStart
            self.update_output_interface(f"Now Sweeping. Estimated Time Remaining = {motorStaticTime * ((self.stage_hiBound-self.stage_loBound)/self.stage_dx -self.motorSweepCounter)} seconds")
            move = move+self.stage_dx
            #simulate camera interaction
            time.sleep(1)
            #self.NRT100.wait(0)
            print(f"move: {move}")
            self.motorSweepCounter += 1
        self.K2220G.OUTPUT_OFF(channel = 2)
        self.start_sweep_button.setText("BEGIN SWEEP")
        self.start_sweep_button.setStyleSheet("background-color: white")

    @QtCore.pyqtSlot()
    def on_clicked_file_explore(self):
        """Opens a file explorer window to path designated by saveFile line"""
        path = self.fileLocation.toPlainText()
        if os.path.exists(path) == True:
            os.startfile(path)
        else:
            os.mkdir(path)
            os.startfile(path)
    @QtCore.pyqtSlot()
    def curve_burn(self):
        self.LS340_4K.loadCurve(self.T4K1.CRVlocation, 59)
        self.LS340_4K.loadCurve(self.T4K2.CRVlocation, 58)
        self.LS340_4K.loadCurve(self.T50K1.CRVlocation, 57)
        self.LS340_4K.loadCurve(self.T50K1.CRVlocation, 56)
        self.update_output_interface("Curve Burn Completed")
    @QtCore.pyqtSlot()
    def grab_motor_position(self):
        time.sleep(2)
        self.motor_position = self.NRT100.query_position()
        self.NRTpos.setText(f"NRT100 POSITION: {self.motor_position}")
        pass

    def _update_label(self, label):
        """Updates NRT100 position label"""
        self.label.setText(self.NRT100.query_position())

    def _voltage_onOff(self):
        """Activates Power supply to set voltage
            If no set voltage: will set to value stored in K2220G mem"""
        

        try:
            if self.QCLtoggleState == 0:
                self.QCL_controlButton.setText("QCL (ON) HEAT (OFF)")
                self.QCL_controlButton.setStyleSheet("background-color: green")
                self.K2220G.OUTPUT_ON()
                self.K2220G.SET_VOLTAGE_CURRENT(2,0,0)
                self.K2220G.SET_VOLTAGE_CURRENT(1,self.voltage,1)
                self.update_output_interface("QCL has been switched ON")
                self.QCLtoggleState = 1

                # self.heatstate == False
                # self.Hrange = 0
                # self.heaterswitch.setStyleSheet("background-color: red")
                # self.heaterswitch.setText("QCL HEATER - (OFF)")
                
                
            else:
                self.QCL_controlButton.setText("QCL (OFF) HEAT (ON)")
                self.QCL_controlButton.setStyleSheet("background-color: red")
                self.K2220G.OUTPUT_OFF()
                self.K2220G.SET_VOLTAGE_CURRENT(2,11.935,1)
                self.update_output_interface("QCL has been turned OFF")
                self.QCLtoggleState = 0
                
                # self.heatstate = True
                # self.Hrange = 5
                # self.heaterswitch.setStyleSheet("background-color: green")
                # self.heaterswitch.setText("QCL HEATER - (ON)")
        except AttributeError:
            self.update_output_interface("Power supply is not connected")
            if self.QCLtoggleState == 0:
                self.QCL_controlButton.setText("QCL (ON) HEAT (OFF)")
                self.QCL_controlButton.setStyleSheet("background-color: green")
                self.update_output_interface("QCL has been switched ON")
                self.QCLtoggleState = 1
                self.K2220G.SET_VOLTAGE_CURRENT(2,0,0)
            else:
                self.QCL_controlButton.setText("QCL (OFF) HEAT (ON)")
                self.QCL_controlButton.setStyleSheet("background-color: red")
                self.update_output_interface("QCL has been turned OFF")
                self.QCLtoggleState = 0
                self.K2220G.SET_VOLTAGE_CURRENT(2,11.935,1)

    def _grab_voltage(self):
        """Takes voltage from volset line, sets to K2220G mem"""
        self.voltage = float(self.QCL_voltSet.toPlainText())
        self.update_output_interface(f"Setting output voltage to {self.voltage} volts....")
        try:
            self.K2220G.SET_VOLTAGE_CURRENT(2, self.voltage, 1)
        except AttributeError:
            self.update_output_interface("Power Supply is not connected, voltage set failed")
    def _connectPeripherals(self):
        """connects to peripheral devices
        returns: 0 if no error, +1 to return for every connection error
        outputs: use outputline in gui to troubleshoot device connectivity"""
        #self.microxcam = MX.MICROXCAM()
        #self.LS340 = LS340.LS340()
        #self.NRT100 = NRT100.NRT100()
        #self.K2220G = K2220G.K2220G()

        #MICROXCAM 384-I CAMERA
        errors = 0
        self.update_output_interface("Connecting to Peripheral Devices...")
        self.update_output_interface(f"Connecting to MICROXCAM...")
        try:
            self.microxcam = MX.MICROXCAM()
            self.update_output_interface("Connected!")
            self.MICROXCAM_label.setStyleSheet("background-color: green")
        except ConnectionError:
            self.update_output_interface("Connection Failed!")
            errors+=1
        
        #NRT100 TRANSLATION STAGE
        self.update_output_interface(f"Connecting to NRT100 Translation Stage")
        try:
            self.NRT100 = NRT100.NRT100()
            self.NRT100_label.setStyleSheet("background-color: green")
            self.update_output_interface("Connected to NRT100")
        except Exception:
            self.update_output_interface("Connection Failed!")
            errors+=1

        #signal generator
        try:
            self.KS33600A = KS33600A.Keysight33600A()
        except Exception:
            self.update_output_interface("KS33600A Connection Failed")
        #LAKESHORE 340 CONTROLLER
        self.update_output_interface(f"Connecting to LAKESHORE340 Temp Controller...")
        try:
            self.LS340_4K = LS340.LS340(14)
            
            self.update_output_interface("Connected LS340 (1)!")
            self.LS340_50K = LS340.LS340(12)
            print(f"RANGE: {self.LS340_50K.query_heater_range()}")
            if self.LS340_50K.query_heater_range() > 0:
                self.heatstate = True
                self.heaterswitch.setStyleSheet("background-color: green")
                self.heaterswitch.setText("QCL HEATER (ON)")

            self.LSTC_1.setStyleSheet("background-color: green")
            self.LSTC_2.setStyleSheet("background-color: green")
            self.LS340_label.setStyleSheet("background-color: green")
           
        except pv.errors.VisaIOError:
            self.update_output_interface("Connection Failed!")
            errors+=1
        #KEITHLEY POWER SUPPLY
        self.update_output_interface(f"Connecting to Keithley 2220G Power Supply...")
        try:
            self.K2220G = K2220G.K2220G(LS340 = self.LS340_50K)
            self.update_output_interface(f"K2220G Connected!")
            self.K2220G_label.setStyleSheet("background-color: green")

        except pv.errors.VisaIOError:
            self.update_output_interface(f"Connection Failed!")
            errors+=1
        
        if errors == 0:
            self.periph_connect_button.setStyleSheet("background-color: green")
        #GRANVILLE-PHILLIPS DEWAR PRESSURE SENSOR
        self.update_output_interface(f"Connecting to Granville-Phillips Micro-Ion")
        try:
            self.pressureSensor = PS()
            self.update_output_interface("GPMI connected!!")
        except Exception:
            self.update_output_interface("Connection to GPMI failed")
            errors+=1
        self.update_output_interface(f"Connected to Peripherals with {errors} errors")
        self.timer2.timeout.connect(self.grab_motor_position)

    def write_pid_settings(self):
        self.pid_p = float(self.p_input.text())
        self.pid_i = float(self.i_input.text())
        self.pid_d = float(self.d_input.text())
        self.update_output_interface(f"P = {self.pid_p}, I = {self.pid_i}, D = {self.pid_d}")

        
        #TODO: this needs to be generalized to both temp controllers - figure out an eloquent way to do this
        #self.cc.set_PID_params(self.pid_p, self.pid_i, self.pid_d)
        if self.b1.isChecked() == True:
                self.mode = "4K"
                self.LS340_4K.set_PID(output = 1, p = self.pid_p, i = self.pid_i, d = self.pid_d)
                #self.LS340_50K.set_setpoint(1,self.ttarget4K1)
                self.ttarget4K1 = float(self.ttarget_input.text())
                try:
                    self.LS340_4K.set_setpoint(temp = self.ttarget4K1)
                    self.update_output_interface("Setting heater range")
                    self.LS340_4K.htrRange(5)
                except AttributeError:
                    self.update_output_interface("NOT CONNECTED TO LS340")
                self.update_output_interface("Cryocooler control mode set to " + self.mode)
                self.update_output_interface("New TTarget = %.2fK" % self.ttarget4K1)                
        elif self.b2.isChecked() == True:
                self.mode = "50K"
                self.LS340_50K.set_PID(output = 1, p = self.pid_p, i = self.pid_i, d = self.pid_d)
                #self.LS340_50K.set_setpoint(temp = self.ttarget50K1)
                try:
                    self.ttarget50K1 = float(self.ttarget_input.text())
                    self.LS340_50K.htrRange(5)
                except AttributeError:
                    self.update_output_interface("NOT CONNECTED TO LS340")
                self.LS340_50K.set_setpoint(temp = self.ttarget50K1)
                self.update_output_interface(f"Cryocooler control mode set to {self.mode}")
                self.update_output_interface(f"New TTarget = {self.ttarget50K1} K")
        elif self.b3.isChecked() == True:
                self.mode = "50K Plate"
                self.LS340_50K.set_PID(output = 2, p = self.pid_p, i = self.pid_i, d = self.pid_d)
                
                try:
                    self.ttarget50K2 = float(self.ptarget_input.text())
                    #self.LS340_50K.htrRange(5)
                except AttributeError:
                    self.update_output_interface("NOT CONNECTED TO LS340")
                self.LS340_50K.set_setpoint(output = 2, temp = self.ttarget50K2)
                #self.update_output_interface(f"Control mode set to {self.mode}")
                self.update_output_interface(f"New TTarget = {self.ttarget50K2} K")
        elif self.b4.isChecked() == True:
                self.mode = "4K - VIPA"
                self.LS340_50K.set_PID(output = 2, p = self.pid_p, i = self.pid_i, d = self.pid_d)
                
                try:
                    self.ttarget4K2 = float(self.ttarget_input.text())
                    self.update_output_interface(f"setting manual out to {self.get_manual_out(temp_target=self.ttarget4K2)}%")
                    self.LS340_4K.set_manual_out(output = 2, man_out = self.get_manual_out(temp_target=self.ttarget4K2))
                except AttributeError:
                    self.update_output_interface("NOT CONNECTED TO LS340")
                self.LS340_4K.set_setpoint(output = 2, temp = self.ttarget4K2)
                self.update_output_interface(f"Control mode set to {self.mode}")
                self.update_output_interface(f"New TTarget = {self.ttarget4K2} K")
        else:
            print("fix the thing")
        print("PID Settings Written")
        
    def read_pid_settings(self,channel):
        #read current PID settings
        self.update_output_interface("Reading PID Settings") 
        
        if self.b1.isChecked() == True:
            self.ttarget4K1 = self.LS340_4K.query_setpoint(output = 1)
            pid_array = self.LS340_4K.query_PID(output = 1)
            pid_array = str(pid_array).split(",")
            self.pid_p = pid_array[0]
            self.pid_i = pid_array[1]
            self.pid_d = pid_array[2]
            self.ttarget_show = self.ttarget4K1
        if self.b2.isChecked() == True:
            self.ttarget50K1 = self.LS340_50K.query_setpoint(output = 1)
            pid_array = self.LS340_4K.query_PID(output = 1)
            pid_array = str(pid_array).split(",")
            print(pid_array)
            self.pid_p = pid_array[0]
            self.pid_i = pid_array[1]
            self.pid_d = pid_array[2]
            self.ttarget_show = self.ttarget50K1
        if self.b3.isChecked() == True:
            self.ttarget50K2 = self.LS340_50K.query_setpoint(output = 2)
            pid_array = self.LS340_50K.query_PID(output=2)
            pid_array = str(pid_array).split(",")
            print(pid_array)
            self.pid_p = pid_array[0]
            self.pid_i = pid_array[1]
            self.pid_d = pid_array[2]
            self.ttarget_show = self.ttarget50K2
        if self.b4.isChecked() == True:
            self.ttarget4K2 = self.LS340_4K.query_setpoint(output = 2)
            pid_array = self.LS340_4K.query_PID(output = 2)
            pid_array = str(pid_array).split(",")
            print(pid_array)
            self.pid_p = pid_array[0]
            self.pid_i = pid_array[1]
            self.pid_d = pid_array[2]
            self.ttarget_show = self.ttarget4K2
        self.p_input.setText(str(self.pid_p))
        self.i_input.setText(str(self.pid_i))
        self.d_input.setText(str(self.pid_d))
        self.ttarget_input.setText(str(self.ttarget_show))
        #print("P = %.2f, I = %.2f, D = %.2f"%(self.pid_p, self.pid_i, self.pid_d))
    

    def update_data(self):
        """Timer rise/fall function to update sensor data"""
        cur_time = time.time()
        self.times.append(float(cur_time))  # Remove the first y element.
        #self.x.append(self.x[-1] + 1)  # Add a new value 1 higher than the last.

        try: #READING TEMPS FROM 4 SENSORS
            self.current_T4K1 = self.LS340_4K.readTemp(self.T4K1.channel)
            self.current_T4K2 = self.LS340_4K.readTemp(self.T4K2.channel)
            self.current_T50K1 = self.LS340_50K.readTemp(self.T50K1.channel)
            self.current_T50K2 = self.LS340_50K.readTemp(self.T50K2.channel)
            self.current_T4K3 = float(self.LS340_50K.readTemp(self.T4K3.channel))
            self.current_T4K4 = float(self.LS340_50K.readTemp(self.T4K4.channel))
            self.current_R4K1 = float(self.LS340_4K.readResistance(self.T4K1.channel))
            self.current_R4K2 = float(self.LS340_4K.readResistance(self.T4K2.channel))
            self.current_R50K1 = float(self.LS340_4K.readResistance(self.T50K1.channel))
            self.current_R50K2 = float(self.LS340_4K.readResistance(self.T50K2.channel))
            self.current_R4K3 = float(self.LS340_50K.readResistance(self.T4K3.channel))
            self.current_R4K4 = float(self.LS340_50K.readResistance(self.T4K4.channel))
            self.current_chamberPressure = float(self.pressureSensor.readPressure())

            self.current_pow = self.LS340_50K.query_htr_out()*8.7/100
        except AttributeError:
            print(AttributeError)
            #self.update_output_interface("LS340 is not connected...")
        # self.current_pow = self.cc.get_CH_power()
        # self.ttarget = self.cc.get_target_temp()
        # self.rej_temp = self.cc.get_reject_temp()
        
        self.temps4K1.append(float(self.current_T4K1))  # Add a new random value.
        self.temps4K2.append(float(self.current_T4K2))
        self.temps50K1.append(float(self.current_T50K1))
        self.temps50K2.append(float(self.current_T50K2))

        

        self.setpoint4K.append(self.ttarget4K1)
        self.setpoint50K.append(self.ttarget50K1)

        plot_times = np.array(self.times)
        plot_temps4K1 = np.array(self.temps4K1)
        plot_temps4K2 = np.array(self.temps4K2)
        plot_temps50K1 = np.array(self.temps50K1)
        plot_temps50K2 = np.array(self.temps50K2)
        setp4 = np.array(self.setpoint4K)
        setp50 = np.array(self.setpoint50K)

        plot_setpoint = np.array(self.setpoint4K)
        plot_power = np.array(self.power)


        plot_len = int(round(self.plot_dur/self.data_rate))
        if plot_len < 3:
            plot_len = 3
        
        # if len(plot_times) > plot_len:
        #     self.temp_line4K1.setData((plot_times[len(plot_times)-plot_len:]-self.starttime)/60.0, plot_temps4K1[len(plot_temps4K1)-plot_len:])  # Update the data.
        #     self.temp_line4K2.setData((plot_times[len(plot_times)-plot_len:]-self.starttime)/60.0, plot_temps4K2[len(plot_temps4K2)-plot_len:])
        #     self.temp_line50K1.setData((plot_times[len(plot_times)-plot_len:]-self.starttime)/60.0, plot_temps50K1[len(plot_temps50K1)-plot_len:])
        #     self.temp_line50K2.setData((plot_times[len(plot_times)-plot_len:]-self.starttime)/60.0, plot_temps50K2[len(plot_temps50K2)-plot_len:])

        #     #self.setpoint_line.setData((plot_times[len(plot_times)-plot_len:]-self.starttime)/60.0, plot_setpoint[len(plot_setpoint)-plot_len:])
        #     #self.power_line.setData((plot_times[len(plot_times)-plot_len:]-self.starttime)/60.0, plot_power[len(plot_power)-plot_len:])
        # else:
        self.temp_line4K1.setData((plot_times[3:]-self.starttime)/60.0, plot_temps4K1[3:])
        self.temp_line4K2.setData((plot_times[2:]-self.starttime)/60.0, plot_temps4K2[2:])
        self.temp_line50K1.setData((plot_times[(len(plot_times)-len(plot_temps50K1)):]-self.starttime)/60.0, plot_temps50K1)
        self.temp_line50K2.setData((plot_times[(len(plot_times)-len(plot_temps50K2)):]-self.starttime)/60.0, plot_temps50K2)            
        self.setp_line4K.setData((plot_times[(len(plot_times)-len(plot_temps50K2)):]-self.starttime)/60.0, setp4)  
        self.setp_line50K.setData((plot_times[(len(plot_times)-len(plot_temps50K2)):]-self.starttime)/60.0, setp50)   
        #self.setpoint_line.setData((plot_times-self.starttime)/60.0, plot_setpoint)
        #self.power_line.setData((plot_times-self.starttime)/60.0, plot_power)
        number = self.current_chamberPressure
        formatted = "{:.2e}".format(number)
        formatted = formatted.replace('e', ' x 10^')
        formatted = formatted.replace("x 10^-0", "x 10<sup>-")
        

        self.temp_display4K.setText(r"T<sub>4KPl</sub> = %.2fK"%float(self.current_T4K1))
        self.pow_display.setText("P<sub>HEAT_QCL</sub> = %.2fW"%float(self.current_pow))
        self.pow_display_4K.setText("P<sub>HEAT_4K</sub> = %.2fW"%float(self.current_pow2))
        self.temp_display50K.setText("T<sub>50KPl</sub> = %.2fK"%float(self.current_T50K1))
        self.temp_display4K2.setText(r"T<sub>VIPA</sub> = %.2fK"%float(self.current_T4K2)) 
        self.temp_display50K2.setText(r"T<sub>QCL</sub> = %.2fK"%float(self.current_T50K2))  
        self.pressDisp.setText(f"P<sub>CH</sub> = {formatted} </sup>Torr")
        #QCL SAFETY CHECK------------------------------------------------------------------
        self.QCLsafetyCheck()
        #TURNING ON HEATERS-----------------------------------------------------------------

        # if not self.heating and float(self.current_T4K1) <= 4.0:
        #     #ensure that resistances are set
        #     self.LS340_4K.controlDisplay(resistance = 144)
        #     self.LS340_50K.controlDisplay(resistance = 144)
        #     #turn on heaters, set to range = 1 (lowest)
        #     self.LS340_4K.htrRange(range = 1)
        #     self.LS340_50K.htrRange(range = 1)
        #     self.heating = True
        #-----------------------------------------------------------------------------------
        if self.recording == True:
            with open(self.envDataFilePath, "a+") as tempFile:
                writer = csv.writer(tempFile)
                writer.writerow(np.array([float(cur_time),float(self.current_T4K1),float(self.current_T4K2),float(self.current_T50K1),float(self.current_T50K2), self.current_R4K1, self.current_R4K2, self.current_R50K1, self.current_R50K2, self.current_R4K3, self.current_R4K4, self.current_T4K3, self.current_T4K4]))
            self.update_output_interface("Data Record Event")
        app.processEvents()
    #DATA RECORDING
    def _begin_data(self):
        self.recording  = not self.recording
        if self.recording == True:
            self.data_button.setText("STOP DATA RECORD")
        else:
            self.data_button.setText("START DATA RECORD")

        self.update_output_interface("Starting data acquisition")


    def _on_clicked_warmUP(self):
        """Sets setpoints for 4K and 50K to room temp, and turns heaters on high"""
        self.LS340_4K.set_setpoint(temp = 295)
        self.LS340_50K.set_setpoint(temp = 295)
        self.LS340_4K.htrRange(range = 4)
        self.LS340_50K.htrRange(range =4)

    #SWEEP PARAMETERS FUNCTIONS--------------------------------------------------------------------------------
    def _grab_dx(self):
        self.stage_dx = float(self.set_sweep_dx.toPlainText())
        self.update_output_interface(f"set stage dx to {self.stage_dx} mm")
    def _grab_bounds(self):
        self.stage_loBound = float(self.set_sweep_lowBound.toPlainText())
        self.stage_hiBound = float(self.set_sweep_hiBound.toPlainText())
        self.update_output_interface(f"Set sweep bounds to LOW: {self.stage_loBound}, HIGH: {self.stage_hiBound}")
    def _grab_framecount(self):
        self.frameCount = float(self.set_frames.toPlainText())
        self.update_output_interface(f"Set averaged frames to {self.frameCount}")
    def _grab_qclTimeOffset(self):
        self.qcl_timerOffset = float(self.qcl_timeOffset.toPlainText())
        self.update_output_interface(f"Set QCL flash time offset to {self.qcl_timerOffset} s")


    def htrmanager(self):
        if self.heatstate == False:
            self.Hrange = 5
            self.heaterswitch.setStyleSheet("background-color: green")
            self.heaterswitch.setText("QCL HEATER - (ON)")
            self.LS340_50K.htrRange(self.Hrange)
            self.heatstate = True

        else:
            self.Hrange = 0
            self.heaterswitch.setStyleSheet("background-color: red")
            self.heaterswitch.setText("QCL HEATER - (OFF)")
            self.LS340_50K.htrRange(self.Hrange)
            self.heatstate = False

    def QCLsafetyCheck(self):
        if (float(self.current_T50K1) > 65) or (float(self.current_T50K2) > 65):
            self.K2220G.OUTPUT_OFF(2) #turns off qcl in event of temperature raise due to compressor shutoff, power loss etc.
            self.K2220G.OUTPUT_OFF(1) #turn off output 1 for good measure
            self.update_output_interface("QCL ERROR 0001: Temperature too high!")
        return 0
    
    def show_popup(self):
        # Pass 'self' (the main window) as the parent
        self.popup_dialog = _FILEsystemPopUp(self)
        # Use .exec() for a modal dialog (blocks main window input)
        self.popup_dialog.exec() 
        
    def _FILEmanager(self, action):
        self.USER = os.environ.get("USERNAME")
        """Use this function for any of the file handeling for this software, all actions can go thru this"""
        self.DATA_PIPE = "C:\\Users\\{self.USER}\\Desktop\\CYCLOPS_DATA\\COOLDOWNS"

        if action == "create":
            """create a cooldown file - TODO: map this to correct buttons"""
            self.testID = f"{self.DATA_PIPE}\\CYCLOPS_RUN_{dt.now().strftime("%Y_%m_%d")}"
            with open(".\\localMEM\\local_cooldown.txt", "w") as cooldownFile:
                cooldownFile.writelines(self.testID)
        elif action == "load":
            """loads cooldown file from memory, this will be stored in //.localMEM"""
            with open(".\\localMEM\\local_cooldown.txt", "r") as cooldownFile:
                self.testID = cooldownFile.readline()
                cooldownFile.close()
        elif action == "create-sweep":
            self.sweepID = f"{self.testID}\\_SWEEP_{dt.now().strftime("%Y_%m_%d_%H_%M_%S")}"




if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec_())