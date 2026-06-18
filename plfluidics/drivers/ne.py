"""
A driver for interfacing with New Era 500 series syringe pumps.
"""
from serial import Serial
from enum import Enum

class NEInterface():
    class Commands(bytes, Enum):
        run     = b"RUN"  # Start
        stp     = b"STP"  # Stop
        pas     = b"PAS"  # Pause
        pur     = b"PUR"  # Start purge
        dia     = b"DIA"  # Define syringe inner diameter
        rat     = b"RAT"  # Pumping rate
        dir     = b"DIR"  # Direction of pumping
        vol     = b"VOL"  # Volume to dispense or set units
        fil     = b"FIL"  # Fill syringe to specified volume
        dis     = b"DIS"  # Volume dispensed or filled
        cld     = b"CLD"  # Clear dispense counter 
        ter     = b"\r"   # End of command character


    class Setup(bytes, Enum):
        adr     = b"ADR"  # Pump network address
        pf      = b"PF"   # Power failure mode
        ln      = b"LN"   # Low noise mode
        al      = b"AL"   # Alarm mode
        trg     = b"TRG"  # Operational trigger default config
        din     = b"DIN"  # Dir control TTL input setup
        rom     = b"ROM"  # Pump motor ttl logic output config
        loc     = b"LOC"  # Lock out mode
        bp      = b"BP"   # Notification beep
        buz     = b"BUZ"  # Buzzer control


    class Units(bytes, Enum):
        ml      = b"ML"   # Use with vol
        ul      = b"UL"   # Use with vol 
        mh      = b"MH"   # mL / hour - use with rat
        uh      = b"UH"   # uL / hour - use with rat
        mm      = b"MM"   # mL / min - use with rat
        um      = b"UM"   # uL / min - use with rat


    class Directions(bytes, Enum):
        inf     = b"INF"
        wth     = b"WDR"
        rev     = b"REV"
        stk     = b"STK"


    class Responses(bytes, Enum):
        inf     = b"I"  # Infusing
        wth     = b"W"  # Withdrawing
        stopped = b"S"  # Stopped
        pause   = b"P"  # Program paused
        phpause = b"T"  # Phase paused
        trig    = b"U"  # Trigger wait
        purge   = b"X"  # Purging
        alarm   = b"A"  # Alarm raised
        delim   = b"?"  # Delimiter for error and alarm


    class Alarms(bytes, Enum):
        reset   = b"R"  # Power interrupted
        stall   = b"S"  # Motor stalled
        time    = b"T"  # Safe mode comm timeout
        err     = b"E"  # Pump program error
        range   = b"O"  # Pump program phase out of range


    class Errors(bytes, Enum):
        unk     = b""    # Command unknown
        na      = b"NA"  # Command currently not applicable
        oor     = b"OOR" # Command data is out of range
        com     = b"COM" # Invalid packet received
        ign     = b"IGN" # Command ignored due to phase start


class NEUSB(Serial):

    def __init__(self, port: str, baudrate=19200, timeout=0.1 ):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

    def __del__(self):
        if self.is_open:
            self.close()

    def send(self, cmd):
        self.write(cmd)
        return self.read_until(b'\x03')[1:-1]

