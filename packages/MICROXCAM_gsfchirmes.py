
from ctypes import *
import os

import numpy as np
import threading as thread
import sys

sys.path.insert(1, "C:\\CYCLOPSpanel\\packages")
import queue

#import numpy as np
import time

#os.add_dll_directory(r"C:\\Users\\gsfchirmes\\Desktop\\CYCLOPSpanel\\include")
#libc = ctypes.LoadLibrary(r"C:\Users\matia\Desktop\c++code\lib\MICROXCAM-384I_CAPI.lib")
fname = "C:\\Users\\gsfchirmes\\Desktop\\camera\\MICROXCAM-384I_CAPI.dll"
fname2 = "C:\\Users\\gsfchirmes\\Desktop\\camera\\imports.dll"
pstrpath = b"C:\\Users\\gsfchirmes\\Desktop\\main\\Bin"

microxcam = cdll.LoadLibrary(fname) #loads in camera main lib dll
main = cdll.LoadLibrary("C:\\CYCLOPSpanel\\packages\\main_gsfchirmes.dll")

imports = cdll.LoadLibrary(fname2)
#func prototype input-outputs---------------------------------------
microxcam.fn_DetectCamera.argtypes = [c_char_p] 
microxcam.fn_DetectCamera.restype = c_int
microxcam.fn_GetDetectedCameraIP.argtypes = [c_int]
microxcam.fn_GetDetectedCameraIP.restype = c_char_p
microxcam.fn_Initialize.argtypes = [c_char_p, c_bool, c_char_p]
microxcam.fn_Initialize.restype = c_int
microxcam.fn_ErrorToText.argtypes = [c_int]
microxcam.fn_ErrorToText.restype = c_char_p
microxcam.fn_DeInitialize.restype = c_int
microxcam.fn_GetCameraImage.argtypes = [POINTER(c_float*110592), POINTER(c_byte*110592), c_int]#[POINTER(c_float*110592), POINTER(c_byte*110592), c_int]
microxcam.fn_GetCameraImage.restype = c_int
microxcam.fn_GetCameraImageOffset.argtypes = [c_ushort, c_int]
microxcam.fn_GetCameraImageOffset.restype = c_int
microxcam.fn_GetImageSize.argtypes = [POINTER(c_int),POINTER(c_int)]
microxcam.fn_GetImageSize.restype = c_int
microxcam.fn_SetRAWProcessOption.argtypes = [c_int]
microxcam.fn_SetRAWProcessOption.restypes = c_int
microxcam.fn_TakeOffset.argtypes = [c_int,c_bool,c_bool]
microxcam.fn_TakeOffset.restype = c_int
microxcam.fn_SetContrast.argtypes = [c_int]
microxcam.fn_SetContrast.restype = c_int
microxcam.fn_SetBrightness.argtypes = [c_int]
microxcam.fn_SetBrightness.restype = c_int
microxcam.fn_GetFPATemp.argtypes = [POINTER(c_double)]
microxcam.fn_GetFPATemp.restype = int
microxcam.fn_TakeOffset.argtypes = [c_int, c_bool, c_bool]
microxcam.fn_TakeOffset.restypes = c_int
microxcam.fn_GetCameraImageOffset = [c_ushort*110592, c_int]
microxcam.fn_GetCameraImageOffset = c_int

imports.float_input.argtypes = [c_int]
imports.float_input.restype = POINTER(c_float*110592)
imports.b_array.argtypes = [c_int]
imports.b_array.restype = POINTER(c_byte*110592)

main.camera_image.argtypes = [c_char_p, c_bool, c_int]
main.camera_image.restype = POINTER(c_int)

main.cameraSpamAvg.argtypes = [c_char_p, c_bool, c_int]
main.cameraSpamAvg.restype = c_int

main.qcl_flash.argtypes = [c_char_p, c_char_p, c_int, c_int]
main.qcl_flash.restype = c_int



##run routine/time testing-------------------------------------------------------------------
class MICROXCAM:
    def __init__(self):
        #initialize camera--------------------------------------------------------------------------
        main.init_camera()
        #-------------------------------------------------------------------------------------------
        pass
    def cam_proc(self,imageon, imageoff, frames, Psup):
        
        #Psup = K2220G.K2220G() #init power supply
        Psup.OUTPUT_OFF(2)
        time.sleep(2)
        error_off = main.camera_image(c_char_p(bytes(imageoff.encode("utf-8"))), False) #taking image with QCL OFF
        time.sleep(.5)
        Psup.SET_VOLTAGE_CURRENT(2,12.25,1) # turning on power supply, setting to 11.79 V cv
        
        Psup.OUTPUT_ON() 

        print("taking images...")
        #time.sleep(5)
        #time1 = time.time() #timing camera image capture
        cam_Error = main.cameraSpamAvg(c_char_p(bytes(imageon.encode("utf-8"))), False, c_int(frames))
        #time2 = time.time()
        
        Psup.OUTPUT_OFF(2) #turning off power supply
        
        #Psup.instr_close() #closing power supply instance
        #print(f"time for averager (50 counts): {time2-time1}")
        pass

    def cam_proc_ext(self,path, frames, Psup):
        offpath = f"{path}\\imageOFF.csv"
        #Psup = K2220G.K2220G() #init power supply
        Psup.OUTPUT_OFF()
        
        error_off = main.camera_image(c_char_p(bytes(offpath.encode("utf-8"))), False) #taking image with QCL OFF
        time.sleep(.5)
        Psup.SET_VOLTAGE_CURRENT(1,11.935,1) # turning on power supply, setting to 11.79 V cv
        Psup.OUTPUT_OFF(2)
        Psup.OUTPUT_ON() 

        #print("taking images...")
        time.sleep(5)
        #time1 = time.time() #timing camera image capture
        for i in range(0,frames):
            imageon = f"{path}\\imageON_{i}.csv"
            main.camera_image(c_char_p(bytes(imageon.encode("utf-8"))), False)
        #time2 = time.time()
        Psup.SET_VOLTAGE_CURRENT(2,11.935,1)
        Psup.OUTPUT_OFF() #turning off power supply
        
        #Psup.instr_close() #closing power supply instance
        #print(f"time for averager (50 counts): {time2-time1}")
        pass
    def simple_image(self, image, RAWPROC):
        """inputs:
           -image.csv path (itll just write to that bad boi)"""
        error = main.camera_image(c_char_p(bytes(image.encode("utf-8"))), False, RAWPROC)
        return 0
    
    # def noise_image(self, folderPath, frames):
    #     main.noise_image(c_char_p(bytes(folderPath.encode("utf-8"))), False, frames)
    #     pass

    def camera_averaging(self,image,frames):
        """takes an image of averaged # frames
            inputs:
            -image.csv path 
            -frames (# of requested, each added adds .02sec to runtime)"""
        error = main.cameraSpamAvg(c_char_p(bytes(image.encode("utf-8"))), False, c_int(frames))
        return microxcam.fn_ErrorToText(error)
    
    def camera_spamming(self, folder,Psup, numframes = 100):
        for i in range(0,numframes):
            print(f"Taking image {i}")
            subfolder = f"{folder}\\images_{i}"
            os.mkdir(subfolder)
            self.cam_proc(f"{subfolder}\\imageON.csv",f"{subfolder}\\imageOFF.csv",60, Psup)

    def camera_meas_timeConst(self, iter, folder):
        testFolder = folder
        if not os.path.exists(testFolder):
            os.mkdir(testFolder)
        os.mkdir(f"{testFolder}\\image_{iter}")
        result_queue = queue.Queue()
        timestart = time.time_ns()
        #thread1 = thread.Thread(target = K2220G_timer, args = (timestart, 12.601, result_queue))
        # thread1.start()
        # while(thread1.is_alive()):
        #     self.simple_image(f"{testFolder}\\image_{iter}\\image_{time.time_ns()-timestart}.csv")
        time_arr = result_queue.get()
        np.savetxt(f"{testFolder}\\image_{iter}\\timeData.csv", time_arr.reshape(1,-1), delimiter = ",")

    def camera_meas_timeConst_simple(self, folder):
        testFolder = folder
        if not os.path.exists(testFolder):
            os.mkdir(testFolder)
        timestart = time.time_ns()
        while(True):
            self.simple_image(f"{testFolder}\\image_{time.time_ns()-timestart}.csv")
        

    def qcl_chop(self,onFile, offFile, numFrames, RAWPROC=1):
        main.qcl_flash(c_char_p(bytes(onFile.encode("utf-8"))), c_char_p(bytes(offFile.encode("utf-8"))), c_int(numFrames), RAWPROC)
        return 0   
            

if __name__ == "__main__":
    cam = MICROXCAM()
    cam.qcl_chop(".\\SHORT_EXP_ON_0.csv",".\\SHORT_EXP_OFF_0.csv",500) 
    

    #TO JAKE:

        #-> press the play button in the upper right after ensuring that qcl is on/flashing

        #-> the software will handle everything else, i'll have the power to the qcl shut off upon completion of the test

        #-> If you get an error saying "NOT INITIALIZED" just ensure that the camera is not connected to the INO GUI and re-run
            #there will be no extra setup involved

        #-> should get a readout updates roughly 25 seconds apart with some basic stats on the most recent image taken, after verifying 
        #that the first one of these has come through, the system can be left to do its thing

        #-> Images will be saved under the fileNames entered in the input to qcl_chop, but I'll handle the stuff with that tomorrow morning

        #IF YOU DO FEEL LIKE TAKING A FEW SHORT EXPOSURES:
        #-------------------------------------------------
            #->CONTROLLING EXPOSURE TIME: 
                #numFrames (the func input) = exposure_time_in_seconds*(qcl switch freq (4Hz)) IT WILL TAKE numFrames OFF and numFrames ON, it is currently set for a roughly 10 hour exposure

            #-> I do not have a way of managing files in a nice way for this yet, as I'm still working out how I want to do the overall data collection system (In the process of changing this in our Application)
                #this means you  have to drag the new images into a diff folder before starting the next run (or change the filename input so they dont get overwritten)

                #you can find them in the "EXPLORER" tab on the LHS of the IDE in the ".\\LONG_EXP_IMAGES" directory
                #Im sorry I know this is super annoying (apologies)

            #->If you want to look at images go to the quick_image_proc tab, it just has basic image subtraction/average noise removal code (can be run by play button, already set to run for current output)