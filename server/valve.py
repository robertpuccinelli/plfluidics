'''Classes for controlling microfluidic valves'''
import logging
import ftd2xx as ftd

logger = logging.getLogger(__name__)

class Valve():
    """Base class for operation of a single valve.

    Attributes
    ----------
    address: str    - location of valve to be controlled
    polarity: bool  - inverts commands (depends on NO/NC solenoid)
    state: bool     - indicates if valve is open
    
    Methods
    -------
    getAddress()        - returns valve address
    setAddress(str)     - sets valve address
    getPolarity()       - returns valve polarity
    getState()          - returns valve state
    open()      - sets valve state open
    close()    - sets valve state closed
    """

    def __init__(self, address, default_state=False, polarity_inverted=False):
        """Initializes microfluidic valve with default parameters.

        Parameters
        ----------
        address: str            - location of valve to be controlled
        default_state: bool     - initialize valve open(True) or closed (False)
        polarity_inverted: bool - inverts commands (depends on NO/NC solenoid)
        """
        self.address = address
        self.polarity = polarity_inverted
        logger.info('Initializing valve : {}'.format(address))
        if default_state:
            self.open()
        else:
            self.close()
        logger.debug(
            'Valve initialized. Addr: {}; Pol: {}; State: {}'.format(
                self.address, 
                self.polarity, 
                self._state))

    def getAddress(self):
        return self.address

    def getPolarity(self):
        return self.polarity
    
    def getState(self):
        return self._state

    def close(self):
        logger.info('Closing valve : {}'.format(self.address))
        self._setState(True)

    def open(self):
        logger.info('Opening valve : {}'.format(self.address))
        self._setState(False)

    def _setState(self, operation):
        '''Performs and xor operation between polarity and desired state before writing output to address.'''
        output = self.polarity^operation
        logger.debug('Writing to valve. Valve:{}, State:{}, Output:{}'.format(
            self.address,
            operation,
            output))
        self._writeState(output)
        self._state = operation
    
    def _writeState(self, output):
        pass


class ValveRGS(Valve):
    """Valve class for the USB valve controller in the R.G-S. design.
    https://sites.google.com/site/rafaelsmicrofluidicspage/valve-controllers/usb-based-controller

    USB controller device passed to valve as an argument. Valve will only operate on the address it possesses.
    """
    def __init__(self, USB_device, address, default_state=False, polarity_inverted=False):
        self.device = USB_device
        super().__init__(address, default_state, polarity_inverted)

    def _writeState(self, output):
        if output:
            cmd = self._command('H',self.address)
        else:
            cmd = self._command('L', self.address)
        self.device.write(cmd)     
        logger.debug('Valve set. {} : {}'.format(self.address, cmd))

    def _numToByte(self,num):
        return num.to_bytes(1, 'big')

    def _strToByte(self,string):
        return string.encode('ascii')
 
    def _joinBytes(self,A,B):
        return b''.join([A,B])

    def _command(self,A,B):
        return self._joinBytes(self._strToByte(A), self._numToByte(B))