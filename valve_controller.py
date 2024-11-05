import logging
import ftd2xx
from .valve import ValveRGS

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

    def setValvesOpen(self, valve_list: list):
        for valve in valve_list:
            self.valve_dict[valve].setStateOpen()
            logger.info('Valve set to open - {}'.format(valve))

    def setValvesClosed(self, valve_list: list):
        for valve in valve_list:
            self.valve_dict[valve].setStateClosed()
            logger.info('Valve set to closed - {}'.format(valve))

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

    def _initValveBanks(valve_param_list):
        pass

    def _valveConstructor(addr, pol, state):
        pass


class ValveControllerRGS(ValveController):
    """Valve controller class for the operation of R.G-S. designed controller.

    https://sites.google.com/site/rafaelsmicrofluidicspage/valve-controllers/usb-based-controller

    All three valve banks are tied to a single USB interface, so multidevice operation is likely limited if one controller per device is assumed. Class is designed to grab first FTDI device detected. May cause issues.    
    """
    def __init__(self, valve_param_list):
        super().__init__(valve_param_list)

    def _initValveBanks(self, valve_param_list):
        self.device=ftd2xx.open(0) # Grab first device, not ideal
        a=0
        b=0
        c=0
        for valve in valve_param_list:
            if valve[0] < 9:
                a += 1
            elif valve[0] > 16:
                c += 1
            else:
                b += 1

        if a > 0:
            logger.info('Initializing valve bank A.')
            self.device.write(b'!A\x00') # !A0, not ideal
        if b > 0:
            logger.info('Initializing valve bank B.')
            self.device.write(b'!B\x00') # !B0, not ideal
        if c > 0:
            logger.info('Initializing valve bank C.')
            self.device.write(b'!C\x00') # !C0, not ideal

    def _valveConstructor(self, addr, pol, state):
        return ValveRGS(USB_device=self.device, address=addr,default_state=state)