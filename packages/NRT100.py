"""DIRECTIONS FOR DEPENDENCY FIXES core python - > ucrt python installation:
    - Moved MSL folders to ucrt python3.12 site-packages
    - pacman installed pyserial via ucrt terminal
    - pacman installed pyzmq via ucrt terminal
    - """
"""
TODO: Fix for bug where stage will stop after homing when starting in an extended position [MAYBE FIXED, NEEDS ECT]
"""
import os
import time
from pprint import pprint
from scipy.ndimage import gaussian_filter

from msl.equipment import (
    EquipmentRecord,
    ConnectionRecord,
    Backend,
)
from msl.equipment.resources.thorlabs import MotionControl

# ensure that the Kinesis folder is available on PATH
os.environ['PATH'] += os.pathsep + 'C:/Program Files/Thorlabs/Kinesis'

record = EquipmentRecord(
    manufacturer='Thorlabs',
    model='BSC101',  # update for your device
    serial='40450744',  # update for your device
    connection=ConnectionRecord(
        address='SDK::Thorlabs.MotionControl.Benchtop.StepperMotor.dll',
        backend=Backend.MSL,
    )
)
#TODO: improve wait function for dynamic usage in multi-command operations

class NRT100():
    def __init__(self):
    # avoid the FT_DeviceNotFound error
        MotionControl.build_device_list()
        # connect to the Benchtop Stepper Motor
        self.motor = record.connect()
        print('Connected to {}'.format(self.motor))
        # set the channel number of the Benchtop Stepper Motor to communicate with
        self.channel = 1
        # load the configuration settings, so that we can call
        # the get_real_value_from_device_unit() method
        self.motor.load_settings(self.channel)
        # the SBC_Open(serialNo) function in Kinesis is non-blocking and therefore we
        # should add a delay for Kinesis to establish communication with the serial port
        time.sleep(1) #this blind delay stuff is bad, TODO: Pull request from public repository with fix
        # start polling at 200 ms
        self.motor.start_polling(self.channel, 200)
        self.home_stage()
        time.sleep(1)
        pass


    def home_stage(self):
        # home the device
        self.motor.home(self.channel)
        
        
        
    #TODO: improve wait function for dynamic usage in multi-command operations
    def wait(self,value):
        try:
            self.motor.clear_message_queue(self.channel)
        except AttributeError:
            print("0")
        message_type, message_id, _ = self.motor.wait_for_message(self.channel)
        while message_type != 2 or message_id != value:
            position = self.motor.get_position(self.channel)
            real = self.motor.get_real_value_from_device_unit(self.channel, position, 'DISTANCE')
            print('  at position {} [device units] {:.3f} [real-world units]'.format(position, real))
            message_type, message_id, _ = self.motor.wait_for_message(self.channel)
    # def wait2(self,commandval):
    #     message_type,message_id, _ = self.motor.wait_for_messaage(self.channel)

    def movetodist(self,real_value):
        steps = self.motor.get_device_unit_from_real_value(self.channel, real_value, 'DISTANCE')
        self.motor.set_move_absolute_position(self.channel, steps)
        self.motor.move_absolute(self.channel)
        #NRT100.wait(NRT100,1)
        pass
    def query_position(self):
        position = self.motor.get_position(self.channel)
        val = self.motor.get_real_value_from_device_unit(self.channel, position, 'DISTANCE')
        return val
    def request_analytics(self):
        power_params = self.motor.get_power_params(self.channel) #power analytics
        print(power_params)
        pass

if __name__ == "__main__":
    NRT100 = NRT100()
    NRT100.home_stage()
    print(f"position: {NRT100.query_position()}")

    # for i in range(20,80,5):
    #     NRT100.movetodist(i)
    #     print(NRT100.motor.check_connection())
    # wait(NRT100,1)
    # time.sleep(1)
    # NRT100.movetodist(1)
    # wait(NRT100,1)
    # print("flag2")
    # NRT100.home_stage()
    # NRT100.wait(0)
    
    
    