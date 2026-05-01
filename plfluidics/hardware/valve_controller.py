import logging
import ftd2xx
from ft4222 import FT2XXDeviceError
from plfluidics.drivers.ft4222_hub import FT4222Hub
from plfluidics.drivers.drv81008 import DRV81008_FT4222
from plfluidics.hardware.valve import Valve, ValveRGS, ValvePLRD1

logger = logging.getLogger(__name__)

class ValveController():
    """Base class for the operation of multiple valves.
    
    Attributes
    ----------
    ValvesDict: dict        - Valve alias:address pairings
    ValvesObj: list         - List of valve objects under control
    
    Methods
    -------
    getValvesStates()       - Returns list of valve states
    setValvesOpen(list)     - Sets valve addresses in list to open
    setValvesClosed(list)   - Sets valve addresses in list to closed
    """

    def __init__(self, valve_param_list):
        """Initializes valve objects under control.

        Parameters
        ----------
        valve_param_list: list  - [[addr1, pol1, state1, alias (optional)], 
                                   [addr2, pol2, state2, alias (optional)], 
                                   ...,
                                   [addrN, polN, stateN, alias (optional)]]
        """
        self.valve_dict = {}
        self._initValveBanks(valve_param_list)
        self._initValves(valve_param_list)

    def setValveOpen(self, valve):
        self.valve_dict[valve].open()
        logger.info('Valve set to open - {}'.format(valve))

    def setValvesOpen(self, valve_list: list):
        for valve in valve_list:
            self.setValveOpen(valve)

    def setValveClose(self, valve):
        self.valve_dict[valve].close()
        logger.info('Valve set to closed - {}'.format(valve))

    def setValvesClose(self, valve_list: list):
        for valve in valve_list:
            self.setValveClose(valve)

    def getValvesStates(self):
        states = []
        for valve in self.valve_dict.keys():
            states.append([valve, self.valve_dict[valve].getState()])
        logger.info('Valve states - {}'.format(states))
        return states

    def _initValves(self, valve_param_list):
        valve_number = 0
        for valve in valve_param_list:
            valve_obj = self._valveConstructor(addr=valve[0], pol=valve[1], state=valve[2])
            if len(valve) > 3:
                name = valve[3]
            else:
                name = valve_number
            self.valve_dict[name] = valve_obj
            logger.info('Valve initialized. {} : {}'.format(name,valve[0]))
            valve_number += 1

    def _initValveBanks(self, valve_param_list):
        pass

    def _valveConstructor(self, addr, pol, state):
        pass


class ValveControllerRGS(ValveController):
    """Valve controller class for the operation of R.G-S. designed controller.

    https://sites.google.com/site/rafaelsmicrofluidicspage/valve-controllers/usb-based-controller

    All three valve banks are tied to a single USB interface, so multidevice operation is likely limited if one controller per device is assumed. Class is designed to grab first FTDI device detected. May cause issues.    
    """
    def __init__(self, valve_param_list):
        super().__init__(valve_param_list)

    def __del__(self):
        try:
            self.device.close()
        except Exception:
            pass

    def _initValveBanks(self, valve_param_list):
        self.device=ftd2xx.open(0) # Grab first device, not ideal

        logger.info('Initializing valve bank A.')
        self.device.write(b'!A\x00') # !A0, not ideal
        logger.info('Initializing valve bank B.')
        self.device.write(b'!B\x00') # !B0, not ideal
        logger.info('Initializing valve bank C.')
        self.device.write(b'!C\x00') # !C0, not ideal

        self.device.write(b'A\x00')
        self.device.write(b'B\x00')
        self.device.write(b'C\x00')

    def _valveConstructor(self, addr, pol, state):
        return ValveRGS(USB_device=self.device, address=addr,default_state=state, polarity_inverted=pol)
    
    
class ValveControllerPLRD1(ValveController):

    def __init__(self, valve_param_list):
        super().__init__(valve_param_list)

    def __del__(self):
        try:
            for dev in self.device.values():
                dev.close()
        except Exception:
            pass

    def _initValveBanks(self, valve_param_list):
        logger.debug('Initializing PLRD1 valve controller.')
        self.hub = FT4222Hub()
        self.hub.detectDevices()
        if ( self.hub.num_devices != 4):
            raise ValueError(f'PLRD1 has 4 subunits. Only {self.hub.num_devices} were detected.')
        else:
            try:
                logger.debug('Initializing FT4222 A')
                flag = "DRV A"
                drvA = DRV81008_FT4222(self.hub.initSPIDevice('A'))
                drvA.readRegisters()
                logger.debug('Initializing FT4222 B')
                flag = "DRV B"
                drvB = DRV81008_FT4222(self.hub.initSPIDevice('B'))
                drvB.readRegisters()
                logger.debug('Initializing FT4222 C')
                flag = "DRV C"
                drvC = DRV81008_FT4222(self.hub.initSPIDevice('C'))
                logger.debug('Initializing FT4222 D')
                flag = "GPIO"
                gpio = self.hub.initGPIODevice('FT4222 D', outputs=[2,3])
                self.device = {'A':drvA, 'B': drvB, 'C': drvC, 'LED':gpio}

            except FT2XXDeviceError as e:
                raise ConnectionError(f'Unable to connect and initialize PLRD1 {flag} - {e}')
            
        logger.info('PLRD1 device initialized.')
            
    def _valveConstructor(self, addr, pol, state):
        if addr < 8:
            return ValvePLRD1(USB_device=self.device['A'], address=addr,default_state=state, polarity_inverted=pol)
        if addr < 16:
            return ValvePLRD1(USB_device=self.device['B'], address=addr-8,default_state=state, polarity_inverted=pol)
        if addr < 24:
            return ValvePLRD1(USB_device=self.device['C'], address=addr-16,default_state=state, polarity_inverted=pol)
        else:
            raise ValueError(f'Address exceeds capacity of the system. Addr: {addr}')




class SimulatedValveController(ValveController):

    def _valveConstructor(self, addr, pol, state):
        return Valve(addr, pol, state)
