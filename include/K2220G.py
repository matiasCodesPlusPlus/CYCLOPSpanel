import pyvisa as pv
import time
import numpy as np
import queue
class K2220G:
    def __init__(self, LS340 = None):
        rm = pv.ResourceManager("C:\\Windows\\System32\\visa64.dll") #path to visa64.dll
        print(rm.list_resources()) #list connected resources, K2220 will be GPIB0::x::INSTR
        self.ctrl = rm.open_resource("GPIB0::1::INSTR")
        print(self.ctrl.query("*IDN?"))
        self.ctrl.write("SYST:REM")
        self.LS340 = LS340
        pass
    def OUTPUT_ON(self):
        """Turns on OUPUT"""
        self.ctrl.write("OUTP ON")
        # if self.LS340!=None:
        #     self.LS340.htrRange(0)
        # pass
    def OUTPUT_OFF(self, channel = 1):
        """Turns off OUTPUT"""
        self.ctrl.write(f"APPL CH{channel}, 0V, 0A")
        # if self.LS340!=None:
        #     self.LS340.htrRange(5)
        #     self.SET_VOLTAGE_CURRENT(2,11.935,1)
        # pass
    def SET_VOLTAGE_CURRENT(self,channel, desired_voltage, desired_current):
        """Sets voltage to a given channel
        INPUTS: 
        -channel : channel to set (1 or 2)
        -desired voltage : voltage to set
        -desired current : current to set 
        OUTPUTS:
        -command to apply voltage and current to channel"""
        self.ctrl.write(f"APPL CH{channel}, {desired_voltage}V, {desired_current}A")
    def MEAS_CURRENT(self,channel):
        """Measures Current over a channel
        IMPUTS:
        -Channel to scope (1 or 2)
        RETURNS:
        -Current """
        current = self.ctrl.query(f"MEASure:CURRent:DC? CH{channel}")
        return float(current)
    def MEAS_VOLTAGE(self,channel):
        """Measures voltage over a channel
        INPUTS:
        -Channel to scope (1 or 2)
        RETURNS:
        -Voltage"""
        voltage = self.ctrl.query(f"MEASure:VOLTage:DC? CH{channel}")
        return float(voltage)
    def instr_close(self):
        self.ctrl.close()


    def timing(self, start_time, voltage, result_queue):
        print("Thread init successful")
        time.sleep(2)
        t1 = time.time_ns()- start_time
        self.SET_VOLTAGE_CURRENT(1,voltage,1)
        self.OUTPUT_ON()
        t2 = time.time_ns()-start_time
        time.sleep(5)
        t3 = time.time_ns() - start_time
        self.OUTPUT_OFF(1)
        t4 = time.time_ns()-start_time
        time.sleep(5)
        t5 = time.time_ns()-start_time
        self.OUTPUT_ON()
        t6 = time.time_ns()-start_time
        time.sleep(5)
        t7 = time.time_ns() - start_time
        self.OUTPUT_OFF(1)
        reslist = [t1, t2, t3, t4, t5, t6, t7]
        arr = np.array(reslist, dtype = int)
        result_queue.put(arr)
#class testing     
if __name__ == "__main__":
    PSUP = K2220G()
    PSUP.SET_VOLTAGE_CURRENT(2,12.08,1)
    PSUP.SET_VOLTAGE_CURRENT(1,0,0)
    PSUP.OUTPUT_ON()
    print(f"meas: {PSUP.MEAS_VOLTAGE(1)}")
    
    
    
    