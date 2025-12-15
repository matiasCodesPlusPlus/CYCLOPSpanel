import sys
sys.path.append(".\\include")

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

from pressure_sensor import pressureSensor as PS
from collections import deque
#instrumentation imports
try:
    import MICROXCAM_gsfchirmes as MX
except FileNotFoundError:
    print("use gsfc fresco for real testing")
import LAKESHORE340 as LS340
import NRT100 as NRT100
import K2220G as K2220G

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
from include.MoutInterpolator import create_manual_output_interpolator

class schedulerPopUp(QDialog):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setWindowTitle("TEST SCHEDULER TOOL")
        layout = QVBoxLayout()
        self.label = QLabel("SCHEDULE TEST\n============================================", self)
        


        #what do we need to track
        self.testConditionalTemp = 50 #conditional temp to start at
        self.dx = 3.5 #sweep param dx
        self.loBound = 0 #lower sweep bound mm
        self.hiBound = 100 #upper sweep bound mm
        
        
        self.setLayout(layout)
        # Optional: set a specific size
        self.resize(500, 180)

    def packageScheduleAndSend(self):
        return np.array([self.testConditionalTemp, self.dx, self.loBound, self.hiBound])