from plfluidics.drivers.ne import NEUSB, NEInterface
from enum import IntEnum, StrEnum
from abc import ABC, abstractmethod

class SyringePumpBase(ABC):
    """Base class for controlling a single syringe pump.

    This class serves as an abstract base class for syringe pumps and is 
    designed to be inherited to give all syringe pumps an equivalent
    interface at the program level even if their hardware implementation 
    differs. This class is not directly instantiable, but implementation 
    of its children classes should work similar to the example below.
    The initialization will raise a RuntimeError if any errors occur.

    Arguments
    ---------
    interface: obj      - Initialized driver for communicating with pump
    address: str        - Location of pump to be controlled
    diameter: float     - Default syringe inner diameter in mm
    direction: str      - Initial pumping direction (inject/withdraw)
    mode: str           - Initial control mode (flow/volume)

    Example
    -------
    > driver = DriverClass('COM6')
    > pump = SyringePumpClass(interface=driver, address = "1", diameter=10.00)
    > pump.units_rate = SyringePumpClass.Units.mh
    > pump.rate = 1
    > pump.start()
    > pump.stop()
    
    Properties
    ----------
    addr -> str
    alarm  -> SyringePumpBase.Alarm
    diameter : float
    direction : SyringePumpBase.Direction
    error -> SyringePumpBase.Error
    mode : SyringePumpBase.Mode
    rate : float
    state -> SyringePumpBase.State
    units_rate
    units_vol : str
    vol : float

    Methods
    -------
    changeAddr(str) -> SyringePumpBase.Status
    getStatus()     -> SyringePumpBase.Status
    getVolCount()   -> SyringePumpBase.Status
    resetVolCount() -> SyringePumpBase.Status
    start()         -> SyringePumpBase.Status
    stop()          -> SyringePumpBase.Status
    purge()         -> SyringePumpBase.Status

    Subclasses
    ----------
    Mode
    Unit
    Direction
    State
    Status
    Error
    Alarm
    """

    class Mode(StrEnum):
        flw = "FLOW"
        vol = "VOL"


    class Unit(StrEnum):
        ml  = "mL"
        ul  = "uL"
        mh  = "mLh"
        uh  = "uLh"
        mm  = "mLm"
        um  = "uLm"
        unk = "?"


    class Direction(StrEnum):
        inj = "INJ"
        wth = "WTH"
        rev = "REV"
        stk = "STK"


    class State(StrEnum):
        inj = "INJECTING"
        wth = "WITHDRAWING"
        stp = "STOPPED"
        pas = "PAUSED"
        pur = "PURGING"
        unk = "UNKNOWN"


    class Status(IntEnum):
        ok  = 0
        alm = 1
        err = 2


    class Error(StrEnum):
        unk = "CMD_UNK" # Command unknown
        na  = "CMD_NA"  # Command currently not applicable
        oor = "CMD_OOR" # Command data is out of range
        com = "COM"     # Invalid packet received
        ign = "PHA_IGN" # Command ignored due to phase start
        vol = "SET_VOL" # Set a volume >0 for volume mode

    class Alarm(StrEnum):
        reset = "PWR_RST" # Power reset detected
        stall = "STALL"   # Motor stall detected
        time  = "TIMEOUT" # Watchdog timeout
        pgm_e = "PGM_ERR" # Error in program
        pgm_o = "PGM_OOR" # Out of range in program


    def __init__(self, interface, address: str, diameter: float, 
                 direction=Direction.inj, mode=Mode.flw, rate = 1, 
                 rate_units = Unit.uh, volume=0, volume_units=Unit.ul):
        self._alarm = False
        self._error = False
        self._reg_vol = 0
        self._mode = None
        self._addr = address.encode('utf-8')
        self.device = interface
        self.diameter = diameter
        self._raiseError()
        self.direction = direction
        self._raiseError()
        self.mode = mode
        self._raiseError()
        self.rate = rate
        self._raiseError()
        self.rate_units = rate_units
        self._raiseError()
        self.vol = volume
        self._raiseError()
        self.vol_units = volume_units
        self._raiseError()


    ##############
    # PROPERTIES #
    ##############

    @property
    def addr(self):
        return self._addr.decode('ascii')

    @property
    def alarm(self):
        return self._alarm

    @property
    def diameter(self) -> float:
        return self._dia

    @diameter.setter
    @abstractmethod
    def diameter(self):
        pass

    @property
    def direction(self) -> str:
        return self._dir

    @direction.setter
    @abstractmethod
    def direction(self):
        pass

    @property
    def error(self):
        return self._error

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    @abstractmethod
    def mode(self):
        pass

    @property
    def rate(self) -> float:
        return self._rate

    @rate.setter
    @abstractmethod
    def rate(self):
        pass

    @property
    def state(self) -> str:
        return self._state

    @property
    def units_rate(self):
        return self._rate_units

    @units_rate.setter
    @abstractmethod
    def units_rate(self):
        pass

    @property
    def units_vol(self) -> str:
        return self._vol_units

    @units_vol.setter
    @abstractmethod
    def units_vol(self):
        pass

    @property
    def vol(self):
        return self._vol

    @vol.setter
    @abstractmethod
    def vol(self):
        pass

    ###########
    # METHODS #
    ###########

    @abstractmethod
    def changeAddr(self, new_addr: str):
        pass

    def getStatus(self):
        if not self._alarm and not self._error:
            return self.Status.ok
        elif self._alarm:
            return self.Status.alm
        elif self._error:
            return self.Status.err

    @abstractmethod
    def getVolCount():
        pass

    @abstractmethod
    def resetVolCount():
        pass

    @abstractmethod
    def start():
        pass

    @abstractmethod
    def stop():
        pass

    @abstractmethod
    def purge():
        pass

    #############
    # UTILITIES #
    #############

    def _raiseError(self):
        if self.getStatus() == self.Status.err:
            raise RuntimeError(self.error)


class NEPump(SyringePumpBase):
    """New Era syringe pump class.

    Builds off of SyringePumpBase to interface with New Era pumps. During implementation, using volume
    mode requires a volume greater than 0 to be set.
    
    """

    
    _resp_list = [resp.value for resp in NEInterface.Responses][:-1]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    ##############
    # PROPERTIES #
    ##############

    @SyringePumpBase.diameter.setter
    def diameter(self,id_mm: float):
        cmd = self._addr + NEInterface.Commands.dia + f"{id_mm}".encode('utf-8') + NEInterface.Commands.ter
        self._send(cmd)
        if self.getStatus() == self.Status.ok:
            self._dia = id_mm

    @SyringePumpBase.direction.setter
    def direction(self, direction: str):
        cmd = None
        if direction in self.Direction:
            if direction == self.Direction.inj:
                cmd = self._addr + NEInterface.Commands.dir +  NEInterface.Directions.inf + NEInterface.Commands.ter
            elif direction == self.Direction.wth:
                cmd = self._addr + NEInterface.Commands.dir +  NEInterface.Directions.wth + NEInterface.Commands.ter
            elif direction == self.Direction.rev:
                cmd = self._addr + NEInterface.Commands.dir +  NEInterface.Directions.rev + NEInterface.Commands.ter
            elif direction == self.Direction.stk:
                cmd = self._addr + NEInterface.Commands.dir +  NEInterface.Directions.stk + NEInterface.Commands.ter
            else:
                self._error = self.Error.unk

        if cmd:
            self._send(cmd)
            if self.getStatus() == self.Status.ok:
                self._dir = direction

    @SyringePumpBase.mode.setter
    def mode(self, mod: str):
        if mod in self.Mode:
            _mod = self.mode
            self._mode = mod

            # Change current volume to 0 if not in flow mode
            if (self._mode == self.Mode.flw) & (_mod != self.Mode.flw):
                self.vol = 0

            # Restore volume from a hidden volume register
            elif self._mode == self.Mode.vol:
                self.vol = self._reg_vol
            
            if self.getStatus() != self.Status.ok:
                self._mode = _mod

    @SyringePumpBase.rate.setter
    def rate(self, value: float):
        cmd = self._addr + NEInterface.Commands.rat + f"{value}".encode('utf-8') + NEInterface.Commands.ter
        self._send(cmd)
        if (self.getStatus() == self.Status.ok) & ((self.state != self.State.inj) | (self.state != self.State.wth)):
            self._rate = value

    @SyringePumpBase.units_rate.setter
    def units_rate(self, unit: str):
        cmd = None
        if unit == self.Unit.ml:
            cmd = self._addr + NEInterface.Commands.vol + NEInterface.Units.ml + NEInterface.Commands.ter
        elif unit == self.Unit.ul:
            cmd = self._addr + NEInterface.Commands.vol + NEInterface.Units.ul + NEInterface.Commands.ter
        else:
            self._error = self.Error.unk
        
        if cmd:
            self._send(cmd)
            if self.getStatus() == self.Status.ok:
                self._rate_units = unit

    @SyringePumpBase.units_vol.setter
    def units_vol(self, unit: str):
        cmd = None
        if unit in self.Unit:
            if unit == self.Unit.mh:
                cmd = self._addr + NEInterface.Commands.vol + NEInterface.Units.mh + NEInterface.Commands.ter
            elif unit == self.Unit.uh:
                cmd = self._addr + NEInterface.Commands.vol + NEInterface.Units.uh + NEInterface.Commands.ter
            elif unit == self.Unit.mm:
                cmd = self._addr + NEInterface.Commands.vol + NEInterface.Units.mm + NEInterface.Commands.ter
            elif unit == self.Unit.um:
                cmd = self._addr + NEInterface.Commands.vol + NEInterface.Units.mh + NEInterface.Commands.ter
        else:
            self._error = self.Error.unk
        
        if cmd:
            self._send(cmd)
            if self.getStatus() == self.Status.ok:
                self._vol_units = unit

    def vol(self, vol:float):
        """Set volume to be injected/withdrawn. 
        Flow mode defaults to setting the hardware volume to 0 while storing the requested volume.
        """
        # Store current volume to hidden register and load new volume
        self._reg_vol = self.vol
        cmd = self._addr + NEInterface.Commands.vol + f"{vol}".encode('utf-8') + NEInterface.Commands.ter
        self._send(cmd)
        if self.getStatus() == self.Status.ok:

            # If in flow mode, restore previous volume setting
            if self.mode == self.Mode.flw:
                cmd = self._addr + NEInterface.Commands.vol + f"0".encode('utf-8') + NEInterface.Commands.ter
                self._send(cmd)
                if self.getStatus() == self.Status.ok:
                    self._vol = 0
            else:
                self._vol = vol

    ###########
    # METHODS #
    ###########

    def changeAddr(self, new_addr: str):
        val = f"{new_addr}".encode('utf-8')
        cmd = self._addr + NEInterface.Setup.addr + val + NEInterface.Commands.ter
        self._send(cmd)
        if (self.getStatus() == self.Status.ok):
            self._addr = val
        return self.getStatus()

    def getVolCount(self) -> list:
        cmd = self._addr + NEInterface.Commands.dis + NEInterface.Commands.ter
        resp = self._send(cmd)
        inj = float(resp[1:6])
        wth = float(resp[7:12])
        return [inj, wth]

    def resetVolCount(self):
        cmd = self._addr + NEInterface.Commands.cld + NEInterface.Directions.inf + NEInterface.Commands.ter
        self._send(cmd)
        cmd = self._addr + NEInterface.Commands.cld + NEInterface.Directions.wth + NEInterface.Commands.ter
        self._send(cmd)
        return self.getStatus()
    
    def start(self):
        error = False
        if (self._mode == self.Mode.vol ) & (self.vol == 0):
            self._error = self.Error.vol
            error = True
        if not error:
            cmd = self._addr + NEInterface.Commands.run + NEInterface.Commands.ter
            self._send(cmd)
        return self.getStatus()
    
    def stop(self):
        cmd = self._addr + NEInterface.Commands.stp + NEInterface.Commands.ter
        self._send(cmd)
        return self.getStatus()

    def purge(self):
        cmd = self._addr + NEInterface.Commands.pur + NEInterface.Commands.ter
        self._send(cmd)
        return self.getStatus()
    
    #############
    # UTILITIES #
    #############

    def _send(self, cmd):
        resp = self.device.send(cmd)
        return self._processResp(resp)
        
    def _processResp(self, response):
        resp = None
        self._alarm = False
        self._error = False
        length = len(response)
        self._setState(response[2:3])
        byte3 =  response[2:3]

        if length > 3:
            # Example: b'01A?S'
            if byte3 == NEInterface.Responses.alarm:
                if response[4:] == NEInterface.Alarms.reset:
                    self._alarm == self.Alarm.reset
                elif response[4:] == NEInterface.Alarms.stall:
                    self._alarm == self.Alarm.stall
                elif response[4:] == NEInterface.Alarms.time:
                    self._alarm == self.Alarm.time
                elif response[4:] == NEInterface.Alarms.err:
                    self._alarm == self.Alarm.pgm_e
                elif response[4:] == NEInterface.Alarms.range:
                    self._alarm == self.Alarm.pgm_o

            # Example: b'01?'
            elif byte3 == NEInterface.Responses.delim:
                if response[3:] == NEInterface.Errors.na:
                    self._error = self.Error.na
                elif response[3:] == NEInterface.Errors.oor:
                    self._error = self.Error.oor
                elif response[3:] == NEInterface.Errors.unk:
                    self._error = self.Error.unk
                elif response[3:] == NEInterface.Errors.com:
                    self._error = self.Error.com
                elif response[3:] == NEInterface.Errors.ign:
                    self._error = self.Error.ign

            # Example: b'b01S?OOR'
            elif (byte3 in self._resp_list) & (response[3:4] == NEInterface.Responses.delim):
                if response[4:] == NEInterface.Errors.na:
                    self._error = self.Error.na
                elif response[4:] == NEInterface.Errors.oor:
                    self._error = self.Error.oor
                elif response[4:] == NEInterface.Errors.unk:
                    self._error = self.Error.unk
                elif response[4:] == NEInterface.Errors.com:
                    self._error = self.Error.com
                elif response[4:] == NEInterface.Errors.ign:
                    self._error = self.Error.ign

            else:
                resp = response[3:]

        return resp
    
    def _setState(self, value: bytes):
        val = self.State.unk
        if value == NEInterface.Responses.inf:
            val = self.State.inj
        elif value == NEInterface.Responses.wth:
            val = self.State.wth
        elif value == NEInterface.Responses.pause:
            val = self.State.pas
        elif value == NEInterface.Responses.stopped:
            val = self.State.stp
        elif value == NEInterface.Responses.purge:
            val = self.State.pur
        self._state = val


