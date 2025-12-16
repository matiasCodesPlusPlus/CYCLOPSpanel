import os
if (os.environ.get("USERNAME") == "gsfchirmes"):
    from labjack import ljm

class pressureSensor():
    def __init__(self):
        self.handle = ljm.openS("T4", "ETHERNET", "ANY")
        print(self.handle)
        
        self.AIN0_register = "AIN0"
        self.GND = "GND"
        
        print(ljm.eReadName(self.handle,self.AIN0_register))

    def readPressure(self):
        """reads ain0 for analog voltage measurement"""
        V_out = ljm.eReadName(self.handle, self.AIN0_register)
        self.current_press_torr = 10**((V_out - 5.5)/0.5)
        return self.current_press_torr
if __name__ == "__main__":
    ps = pressureSensor()
    while  1:
        print(ps.readPressure())