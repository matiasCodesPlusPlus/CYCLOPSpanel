import pyvisa

class Keysight33600A:
    def __init__(self, resource_name: str = r"TCPIP0::A-33600-00000-2.local::inst0::INSTR"):
        rm = pyvisa.ResourceManager()
        
        self.inst = rm.open_resource(resource_name)
        self.inst.timeout = 5000
        self.idn = self.inst.query('*IDN?').strip()

    def reset(self):
        """Reset instrument to default state."""
        self.inst.write('*RST')

    def clear(self):
        """Clear status registers."""
        self.inst.write('*CLS')

    def set_waveform(self, channel: int, waveform: str):
        """
        Set waveform type.
        waveform: SIN, SQU, RAMP, PULS, NOIS, DC, USER
        """
        self.inst.write(f'SOURce{channel}:FUNCtion {waveform}')

    def set_frequency(self, channel: int, frequency_hz: float):
        """Set frequency in Hz."""
        self.inst.write(f'SOURce{channel}:FREQuency {frequency_hz}')

    def set_amplitude(self, channel: int, amplitude_vpp: float):
        """Set amplitude in volts peak-to-peak."""
        self.inst.write(f'SOURce{channel}:VOLTage {amplitude_vpp}')

    def set_offset(self, channel: int, offset_v: float):
        """Set DC offset voltage."""
        self.inst.write(f'SOURce{channel}:VOLTage:OFFSet {offset_v}')

    def set_phase(self, channel: int, phase_deg: float):
        """Set output phase in degrees."""
        self.inst.write(f'SOURce{channel}:PHASe {phase_deg}')

    def output_on(self, channel: int):
        """Enable output."""
        self.inst.write(f'OUTPut{channel}:STATe ON')

    def output_off(self, channel: int):
        """Disable output."""
        self.inst.write(f'OUTPut{channel}:STATe OFF')

    def close(self):
        """Close VISA session."""
        self.inst.close()

    def set_square_high_low(self, channel: int, v_high: float, v_low: float):
        """
        Configure square wave mode and set HI/LO output voltage levels.

        Parameters
        ----------
        channel : int
            Output channel (1 or 2)
        v_high : float
            High level voltage in volts
        v_low : float
            Low level voltage in volts
        """

        # Ensure wave type is square
        self.inst.write(f"SOURce{channel}:FUNCtion SQUare")

        # Set HI/LO voltage levels
        self.inst.write(f"SOURce{channel}:VOLTage:LEVel:IMMediate:HIGH {v_high}")
        self.inst.write(f"SOURce{channel}:VOLTage:LEVel:IMMediate:LOW {v_low}")

if __name__ == "__main__":
    key = Keysight33600A()
    key.set_square_high_low(2,5.924,5.92)
    
