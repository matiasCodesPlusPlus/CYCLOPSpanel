import pyvisa as pv
import numpy as np
from os import path as path
import time
from scipy import interpolate
class THERMOMETER():
    def __init__(self,channel, CRVlocation, opTemp = 50, location = '50K plate'):
        self.channel = channel
        self.CRVlocation = CRVlocation
        self.opTemp = opTemp
        self.location = location
        pass
class LS340:
    def __init__(self, GPIB_num):
        self.connectflag = 0
        
        rm = pv.ResourceManager()
        #print(f"resources: {rm.list_resources()}")
        try:
            self.ctrl = rm.open_resource(f"GPIB0::{GPIB_num}::INSTR")
            self.ctrl.write_termination = "[term]"
            #print(f"ID: {self.ctrl.query("*IDN?")}")
            self.ctrl.write("SYST:REM")
            self.connectflag = 1
        except pv.errors.VisaIOError:
            self.connectflag = 0
            print("failed")
        
        pass
    def read_connectflag(self):
        return self.connectflag
    def readTemp(self,channel):
        temp = self.ctrl.query('KRDG? ' + str(channel))
        return temp
    def readResistance(self,channel):
        res = self.ctrl.query('SRDG? ' + str(channel))
        return res
    def loadCurve(self,curveFile, userCurve):
        curveID = print(path.split(curveFile)[1].strip(".tbl"))
        data_array = np.loadtxt(curveFile,  skiprows=1)
        formString = "CRVHDR "+str(userCurve)+ ", "+"USER"+str(userCurve) + ", " +str(curveID)+ ", "+ "3, 400, 1"
        self.ctrl.write(formString)
        for index, vals in enumerate(data_array):
            comstr = "CRVPT "+str(userCurve)+", "+str(index+1) + ", "+str(round(vals[1],4))+", "+str(round(vals[0],4))+"[term]"
            self.ctrl.write(comstr)
            print(comstr)
        self.ctrl.write("CRVSAV")
        
        pass
    def set_temp_limit(self, ch = 'A', temp = 0):
        #sets temperature limit for a given input, if exceeded, all outputs are turned off, temp given in K
        self.ctrl.write("TLIMIT " + ch + ",%.3f")
        return self.query_temp_limit(ch = ch)
        
        
    def query_temp_limit(self, ch = 'A'):
        #queries current temp limit for a given channel
        if ch == 'A':
            self.temp_limit_A = float(self.ctrl.query("TLIMIT? " + ch))
            return self.temp_limit_A
        elif ch == 'B':
            self.temp_limit_B = float(self.ctrl.query("TLIMIT? " + ch))
            return self.temp_limit_B
        elif ch == 'C':
            self.temp_limit_C = float(self.ctrl.query("TLIMIT? " + ch))
            return self.temp_limit_C
        elif ch == 'D':
            self.temp_limit_D = float(self.ctrl.query("TLIMIT? " + ch))
            return self.temp_limit_D
        else:
            print(ch + " is not a known channel")
            return -1
            
    def set_setpoint(self, output=1, temp = 0.0):
        #sets the control setpoint for a given output channel, 2 is the low power output
        self.ctrl.write("SETP " + str(output)+ ", " + str(temp))
        return self.query_setpoint(output = output)
        
    def query_setpoint(self, output = 2):
        #queries the output temperature set point
        if output == 1:
            self.output1_setp = float(self.ctrl.query("SETP? 1"))
            return self.output1_setp
        if output == 2:
            self.output2_setp = float(self.ctrl.query("SETP? 2"))
            return self.output2_setp
        else:
            print("Output %d not recognized" % output)
            return -1
        
    def set_heater_range(self, output = 2, range = 0):
        #sets the output heater range, 0 is off, 1-5 are increasing ranges in decades of power output
        if range < 5:
            self.ctrl.write("RANGE %d,%d" %(int(round(output)),int(round(range))))
        else:
            print("Range %d cannot be greater than 5" % range)
        return self.query_heater_range(output = output)
        
    def query_heater_range(self, output = 2):
        #queries the current heater range setting
        if output == 1:
            self.output1_range = int(self.ctrl.query("RANGE? 1"))
            return self.output1_range
        if output == 2:
            self.output2_range = int(self.ctrl.query("RANGE? 2"))
            return self.output2_range
        else:
            print("Output %d not recognized" % output)
            return -1
            
    def set_output_mode(self, output = 2, mode = "OFF", input_ch = 'A', power_up_enable = 0):
        #sets the output mode for a given output, controlled by a given input
        #inputs 1 = A, 2 = B
        #modes, 0 = OFF, 1 = PID, 2 = Zone, 3 = Open Loop, 4 = Monitor Out, 5 = Warmup
        if mode == "OFF":
            mode_num = 0
        elif mode == "PID":
            mode_num = 1
        elif mode == "Zone":
            mode_num = 2
        elif mode == "OpenLoop":
            mode_num = 3
        elif mode == "MonitorOut":
            mode_num = 4
        elif mode == "Warmup":
            mode_num = 5
        else:
            print("Mode : " + mode + " not recognized")
            mode_num = 0
        if input_ch == 'A':
            input = 1
        elif input_ch == 'B':
            input = 2
        elif input_ch == 'C':
            input = 3
        elif input_ch == 'D':
            input = 4
        else:
            print("Channel " + input_ch + " not recognized")
            input = 1
        self.ctrl.write("OUTMODE %d,%d,%d,%d" %(output, mode_num, input, power_up_enable))
        return self.query_output_mode(output = output)
        
    def query_output_mode(self, output = 2):
        #queries the current output mode
        if output == 1:
            self.output1_mode = self.ctrl.query("OUTMODE? 1")
            return self.output1_mode
        if output == 2:
            self.output2_mode = self.ctrl.query("OUTMODE? 2")
            return self.output2_mode
        else:
            print("Output %d not recognized" % output)
            return -1
            
    def set_PID(self, output = 1, p = 50, i = 20, d = 50):
        #sets the pid control parameters for an output = p*(error + i*(integral of error + d/100*derivative of error))
        self.ctrl.write("PID %d,%.1f,%.1f,%d" % (output, p, i, d))
        return self.query_PID(output = output)
        
    def query_PID(self, output):
        return self.ctrl.query("PID? "+ str(output))
        #queries the current pid parameters for an output
        # if output == "A":
        #     self.output1_pid = self.ctrl.query("PID? A")
        #     return self.output1_pid
        # if output == "B":
        #     self.output2_pid = self.ctrl.query("PID? B")
        #     return self.output2_pid
        # else:
        #     print("Output %d not recognized" % output)
        #     retur
            
    def set_manual_out(self, output = 2, man_out = 0):
        #sets the manual output value for a given output in % of max power
        self.ctrl.write("MOUT %d, %.3f" %(output, man_out))
        return self.query_manual_out(output = output)
        
    def query_manual_out(self, output = 2):
        #queries the current manual output level for a given output
        if output == 1:
            self.output1_mout = self.ctrl.query("MOUT? 1")
            return self.output1_mout
        if output == 2:
            self.output2_mout = self.ctrl.query("MOUT? 2")
            return self.output2_mout
        else:
            print("Output %d not recognized" % output)
            return -1
            
    def query_htr_out(self, output = 1):
        #queries the current heater output in % of max
        if output == 1:
            self.output1_output = float(self.ctrl.query("HTR? 1"))
            return self.output1_output
        if output == 2:
            self.output2_output = float(self.ctrl.query("HTR? 2"))
            return self.output2_output
        else:
            print("Output %d not recognized" % output)
            return -1
            
    def wait_for_settle(self, ch = "B", min_wait_time = 100, settling_test_period = 10, settling_accuracy = 0.01, target_temp = None):
        #waits for the temperature of a given channel to settle
        averaging_time = 5 #sec, how long to average temp measurements
        start_time = time.time()
        print("Waiting %.1f seconds until starting to monitor for temperature settling" % min_wait_time)
        #time.sleep(min_wait_time)
        print("Starting to monitor temperatures for settling")
        if target_temp == None: #meaning we are just waiting for it to settle to an arbitrary temperature, but unknown
            time_start = time.time()
            temps = []
            while time.time() - time_start < averaging_time:
                temps.append(self.readTemp("B"))
                time.sleep(0.1)
            temp_avg = np.average(np.array(temps, dtype = float))
            print("Current Temp = %.5f K" % temp_avg)
            prev_temp_avg = 0.0
            #check for settling, make sure it is settled within errors twice
            settled_last_time = False
            while np.absolute(temp_avg - prev_temp_avg) > settling_accuracy or not settled_last_time:
                print(settling_accuracy)
                settling_accuracy = .0005*temp_avg
                if np.absolute(temp_avg - prev_temp_avg) < settling_accuracy:
                    settled_last_time = True
                    print("Settled for last test period, waiting one more")
                else:
                    settled_last_time = False
                    print("Not settled for last test period")
                print("Waiting %.1f seconds for settling test" % settling_test_period)
                time.sleep(settling_test_period)
                prev_temp_avg = temp_avg
                #take data for another averaging period
                time_start = time.time()
                temps = []
                while time.time() - time_start < averaging_time:
                    temps.append(self.readTemp(ch))
                    time.sleep(0.1)
                temp_avg = np.average(np.array(temps, dtype = float))
                print("Current Temp = %.5f K" % temp_avg)
            print("Temperature settled for two consecutive test periods")
            return 1
        else: #for this option, we have a target temperature to settle to, so check that out settled temp is also accurate
            time_start = time.time()
            temps = []
            while time.time() - time_start < averaging_time:
                temps.append(self.read_temp(ch))
                time.sleep(0.1)
            temp_avg = np.average(np.array(temps))
            print("Current Temp = %.5f K" % temp_avg)
            prev_temp_avg = 0.0
            #check for settling, make sure it is settled within errors twice
            settled_last_time = False
            accurate_last_time = False
            while np.absolute(temp_avg - prev_temp_avg) > settling_accuracy or np.absolute(temp_avg - target_temp) > settling_accuracy or not settled_last_time or not accurate_last_time:
                settling_accuracy = .0005*temp_avg
                if np.absolute(temp_avg - prev_temp_avg) < settling_accuracy:
                    settled_last_time = True
                    print("Settled for last test period, waiting one more")
                else:
                    settled_last_time = False
                    print("Not settled for last test period")
                if np.absolute(temp_avg - target_temp) < settling_accuracy:
                    accurate_last_time = True
                    print("Temp at setpoint for last test period, waiting one more")
                else:
                    accurate_last_time = False
                    print("Temp not at setpoint for last test period")
                print("Waiting %.1f seconds for settling test" % settling_test_period)
                time.sleep(settling_test_period)
                prev_temp_avg = temp_avg
                #take data for another averaging period
                time_start = time.time()
                temps = []
                while time.time() - time_start < averaging_time:
                    temps.append(self.read_temp(ch))
                    time.sleep(0.1)
                temp_avg = np.average(np.array(temps))
                print("Current Temp = %.5f K" % temp_avg)
            print("Temperature settled and accurate for two consecutive test periods")
            return 1
    
    def time_constant_func(self, T, a, b, c, d, e):
        return a + b*T**1.0 + c*T**2.0 + d*T**3.0 + e*T**4.0
    
    def quick_step(self, target_temp = 1.0, heater_range = 2, mult_factor = 1.0, temp_trigger_delta = 0.05):
        #takes in data on the DC load curve and heat capacity of the BB vs. temperature to input the corect amount of energy to step the blackbody quickly
        
        #heater information
        heater_resistance = 1008.5 #ohms, just for plotting purposes, best guess from 4-wire measurements
        full_resistance = 1179.0 #ohms
        if heater_range == 2:
            max_voltage = 3.560 #volts, as measured for this particular range
        if heater_range == 3:
            max_voltage = 11.860 #volts, extrapolated from 20K setpoint ~ 7.65V at 64.5% max current
        max_current = max_voltage/full_resistance #amperes
        max_power = max_current**2.0*heater_resistance #watts
        print("Maximum heater power available = %.2f mW" % (max_power*1000.0))
        
        #take in load curve
        data_loadcurve = np.load(self.loadcurve)

        powers_lc = data_loadcurve['powers']*max_power/100.0 # in Watts
        temps_lc = data_loadcurve['tempsA'] #in K

        #make interpolating function for load curve
        power_vs_temp = interpolate.interp1d(temps_lc, powers_lc, bounds_error = False, fill_value = 'extrapolate', kind = 'cubic')

        #now generate an interpolating function for the heat capacity using the time constant fit and load curve
        time_constant_fit = [4.26308677e+01, -9.00312803e+00,  1.04061940e+01, -1.41326718e-01, 5.77891464e-03]#[ 51.45528942, -26.27331439,  21.3930056,   -2.67752966,   0.2072773 ]
        model_temps = np.linspace(0.821, 10, 1001)
        
        time_constants = self.time_constant_func(model_temps, time_constant_fit[0], time_constant_fit[1], time_constant_fit[2], time_constant_fit[3], time_constant_fit[4])
        #now for each temperature where we have a time constant mesaurement, calculate C
        heat_caps = []
        for i in range(0, len(model_temps)):
            #calculate G, Q = G*(T2-T1), where T1 is ~0.82K
            power_at_temp = power_vs_temp(model_temps[i])
            G = power_at_temp/(model_temps[i] - 0.82)
            #now tau = C/G so C = tau*G
            heat_caps.append(G*time_constants[i])
        heat_caps = np.array(heat_caps)
                
        heatcap_vs_temp = interpolate.interp1d(model_temps, heat_caps, bounds_error = False, fill_value = 'extrapolate')
        
        #take curent temperature
        temp_current = self.read_temp(ch = 'A')
        
        #now integrate the heat capacity from the current temp to the target temperature
        temps_int = np.linspace(temp_current, target_temp, 1001)
        heat_cap_integral = 0
        for i in range(0, len(temps_int)-1):
            heat_cap_integral = heat_cap_integral + heatcap_vs_temp(0.5*(temps_int[i] + temps_int[i+1]))*(temps_int[i+1]-temps_int[i])
        
        #steady state manual output at target temp
            man_out_final = power_vs_temp(target_temp)*100.0/max_power
            if man_out_final > 100.0:
                man_out_final = 100.0
                print("Error: target temperature too high for heater range")
                
        #now calculate the time required to add in the amount of sensible heat required to raise / lower temp
        if heat_cap_integral > 0: #we are heating up!
            
            print("Heating Blackbody from %.3fK to %.3fK" % (temp_current, target_temp))
            print("Sensible heat change = %.3fmJ" % (1000.0*heat_cap_integral))
            min_time = mult_factor*heat_cap_integral/(max_power - power_vs_temp(temp_current))
            print("Minimum time to change temp = %.2f sec" % min_time)
            
            #dont want to make the move in <10 sec for accuracy reasons, so if min_time < 10, calculate the output power level to make it 10
            if min_time < 5.0:
                set_power = power_vs_temp(temp_current) + mult_factor*heat_cap_integral/5.0
                set_power_perc = 100.0*set_power/max_power
                print("Move would be too fast, instead setting power to %.3fmW to make move time 5sec" % (set_power*1000.0))
            else:
                set_power_perc = 100.0
                print("Setting heater to maximum power = %.3f mW" % (max_power*1000.0))
                
                
            #turn heater to max and integrate deposited energy until we've reached the heat_cap_integral
            time_start = time.time()
            time_prev = time_start
            integrated_power_delivered = 0
            #set to open loop mode and set manual output
            self.set_output_mode(output = 2, mode = "OpenLoop", input_ch = 'A')
            self.set_heater_range(output = 2, range = heater_range)
            self.set_manual_out(output = 2, man_out = set_power_perc)
            #now wait for the correct amount of integrated power minus parasitic loads to be delivered to the BB
            while integrated_power_delivered < mult_factor*heat_cap_integral:
                time.sleep(0.1)
                print("Energy delivered in %.3f sec = %.3fmJ" %(time_prev - time_start, integrated_power_delivered*1000.0))
                temp_current = self.read_temp(ch = 'A')
                time_cur = time.time()
                integrated_power_delivered = integrated_power_delivered + (set_power_perc/100.0*max_power - power_vs_temp(temp_current))*(time_cur-time_prev)
                time_prev = time_cur           
        
        #now we are hopefully hotter than desired
        if self.read_temp(ch = 'A') > target_temp + temp_trigger_delta:
            #set manual output to 0 until BB has cooled to desired temp
            print("Heater power OFF, temp at %.3fK" % (self.read_temp(ch = 'A')))
            self.set_output_mode(output = 2, mode = "OpenLoop", input_ch = 'A')
            self.set_manual_out(output = 2, man_out = 0)
            cur_temp = self.read_temp(ch = 'A')
            while cur_temp > target_temp + temp_trigger_delta:
                print("Waiting to cool, current temp = %.3fK" % cur_temp)
                time.sleep(0.1)
                cur_temp = self.read_temp(ch = 'A')
                
        #set manual output to DC level now that we've waited to cool below target_temp + temp_trigger_delta
        print("Setting temperature controller to steady state output = %.3fmW = %.2f percent" % (man_out_final*max_power*10.0, man_out_final))
        self.set_manual_out(output = 2, man_out = 0)
        self.set_heater_range(output = 2, range = 0)
        #time.sleep(wait_after_pulse) #wait N sec for transient to die out and BB to internally thermalize
        #turn back on PID
        self.set_setpoint(output = 2, temp = target_temp)
        self.set_output_mode(output = 2, mode = "PID", input_ch = 'A')
        #set PID parameters intelligently (to do)
        self.set_PID(output = 2, p = 50, i = 20, d = 0) #set PID parameters for the heater output
        self.set_manual_out(output = 2, man_out = man_out_final)
        self.set_heater_range(output = 2, range = heater_range)
        #self.set_manual_out(output = 2, man_out = man_out_final) 
        #finished, ready to return control to program
        return 1
    def configureControl(self, loop = 1, mode = 4):
        """sets up control loop in variety of modes, default is mode 1 on Autotune PID"""
        self.ctrl.write("CMODE "+str(loop)+", "+str(mode))
    def queryControl(self, loop = 1):
        self.ctrl.query("CMODE? "+str(loop))
    def controlDisplay(self, loop = 1, numloops = 1, resistance = 144, currPow = 2, largeOutput = 0):
        self.ctrl.write("CDISP "+str(loop)+", "+str(numloops)+", "+str(resistance)+", "+str(currPow)+", "+str(largeOutput))
    def controlRamp(self, loop = 1, onOff = 1, kpmin = 5):
        self.ctrl.write("RAMP "+ str(loop)+", "+str(onOff)+", "+str(kpmin))
    def htrRange(self, range):
        """input a range from 0-5 0 = heater OFF"""
        self.ctrl.write("RANGE "+str(range))
if __name__ == "__main__":
    Mout = np.linspace(100,60,9)
    
    temps2 = []
    LS340 = LS340(14)

    for val in Mout:
        print(f"value: {val}%")
        LS340.set_manual_out(output = 2, man_out = val)
        LS340.wait_for_settle()
        tval = LS340.readTemp(channel = "B")
        temps2.append([Mout, tval])
    for row in temps2:
        print(row)
    #LS340.loadCurve("",37)
    
    
    