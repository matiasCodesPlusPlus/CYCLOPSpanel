#Automated qcl power phase for maximizing SNR 
from KS33600A import Keysight33600A as KS
from MICROXCAM_gsfchirmes import MICROXCAM as MX
from K2220G import K2220G
import numpy as np
import os
import time

#set up peripherals
waveGen = KS()
psup = K2220G()
cam = MX()
#set min, max (will be deleted later)
phaseMIN = 0
phaseMAX = 30
step = 12
#
phases = np.linspace(phaseMIN, phaseMAX, step)
testPath = f"QCLphase_test4"
os.mkdir(testPath)

waveGen.set_amplitude(1,5.0)
waveGen.set_offset(1,0)
waveGen.set_phase(1,0)
waveGen.set_frequency(1,10)

waveGen.set_amplitude(2,5.0)
waveGen.set_offset(2,0)
waveGen.set_phase(2,0)
waveGen.set_frequency(2,5)

for phase in phases:
    folderPath = f"{testPath}\\phase_{phase}"
    os.mkdir(folderPath)
    waveGen.set_phase(2,phase)
    time.sleep(2)
    cam.qcl_chop(f"{folderPath}\\qcl_ON.csv", f"{folderPath}\\qcl_OFF.csv", numFrames=100)
