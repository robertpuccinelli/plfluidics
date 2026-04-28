import logging
import ft4222
from ft4222.SPI import Cpha, Cpol
from ft4222.SPIMaster import Mode, Clock, SlaveSelect

logger = logging.getLogger(__name__)


class FT4222Hub():
    def __init__(self):
#        self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')
        self.subunits = {}
        self.device_details = {}

    def __del__(self):
        for subunit in self.subunits:
            logger.debug(f'Closing FT4222 device: {subunit}')
            subunit.device.close()

    def detectDevices(self):
        self.device_details = {}
        self.num_devices = ft4222.createDeviceInfoList()
        logger.debug(f'Detected {self.num_devices} FT4222 devices.')

        if self.num_devices == 0:
            logger.warning('No FT4222 devices detected.')
            return

        for i in range(self.num_devices):
            self.device_details[str(i)] = ft4222.getDeviceInfoDetail(i)
            logger.debug(f'Device {i}: {self.device_details[str(i)]}')

    def initSPIDevice(self, 
                      device_id, 
                      mode=1, 
                      clock=Clock.DIV_32,  # 1.875 MHz
                      clock_pol=Cpol.IDLE_LOW, 
                      clock_phase=Cpha.CLK_TRAILING, 
                      slave_select=0):
        logger.debug(f'Opening device : {device_id}. Mode={mode}, clk={clock}, clk_pl={clock_pol}, clk_ph={clock_phase}, ss={slave_select}')
        device = self._openDevice(device_id)
        if  device != None:
            if slave_select == 0:
                ss = SlaveSelect.SS0
            elif slave_select == 1:
                ss = SlaveSelect.SS1
            elif slave_select == 2:
                ss = SlaveSelect.SS2
            elif slave_select == 3:
                ss = SlaveSelect.SS3
            if mode == 1:
                spi_device = FT4222SPIDevice_Single(device=device,
                                                    clock=clock,
                                                    clock_pol=clock_pol, 
                                                    clock_phase=clock_phase, 
                                                    slave_select=ss)
        
            self.subunits[device_id] = spi_device
        else:
            print('Device not found')
            logger.warning(f'Device ID not found: `{device_id}`')
        return spi_device

    def initGPIODevice(self,
                       device_id,
                       outputs,
                       suspend=False,
                       wake=False):
        device = self._openDevice(device_id)
        if  device != None:
            out_list = []
            for i in range(4):
                    if i in outputs:
                        out_list.append(1)
                    else:
                        out_list.append(0)

            gpio_device = FT4222GPIODevice(device, out_list, suspend=suspend, wake=wake)
            self.subunits[device_id] = gpio_device
        else:
            logger.warning(f'Device ID not found: `{device_id}`')
        return gpio_device
    
    def _openDevice(self, device_id):
        device = None

        if device_id.encode('utf-8') in [self.device_details[item]['serial'] for item in self.device_details]:
            device = ft4222.openBySerial(device_id)
            logger.debug(f'FT4222 device opened by serial: `{device_id}`')

        if device_id.encode('utf-8') in [self.device_details[item]['description'] for item in self.device_details]:
            device = ft4222.openByDescription(device_id)
            logger.debug(f'FT4222 device opened by description: `{device_id}`')

        return device
    
    def test(self):
        print('test')
    

class FT4222SPIDevice_Single():
    def __init__(self,
                 device: ft4222.FT4222, 
                 clock=Clock.DIV_32,  # 1.875 MHz
                 clock_pol=Cpol.IDLE_LOW, 
                 clock_phase=Cpha.CLK_TRAILING, 
                 slave_select=SlaveSelect.SS0):
        logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')
        self.device = device
        self.device.spiMaster_Init(clock=clock,
                                   mode=Mode.SINGLE, 
                                   cpol=clock_pol, 
                                   cpha=clock_phase, 
                                   ssoMap=slave_select)

    def read(self, num_bytes=2, term=True):
        return self.device.spiMaster_SingleRead(bytesToRead=num_bytes, isEndTransaction=term)

    def write(self, data, term=True):
        return self.device.spiMaster_SingleWrite(data=data, isEndTransaction=term)

    def readWrite(self, data, term=True):
        return self.device.spiMaster_SingleReadWrite(data=data, isEndTransaction=term)

class FT4222GPIODevice():
    def __init__(self, 
                 device: ft4222.FT4222, 
                 output_list, 
                 suspend=False, 
                 wake=False):
        pin_dirs = []
        for gpio in output_list:
            if gpio:
                pin_dirs.append(ft4222.GPIO.Dir.OUTPUT)
            else:
                pin_dirs.append(ft4222.GPIO.Dir.INPUT)
        self.device = device
        self.setSuspend(suspend)
        self.setWake(wake)
        self.device.gpio_Init(*pin_dirs)

    def setSuspend(self, state: bool):
        self.device.setSuspendOut(state)

    def setWake(self, state: bool):
        self.device.setWakeUpInterrupt(state)

    def write(self, pin, state: bool):
        if pin == 0:
            port = ft4222.GPIO.Port.P0
        elif pin == 1:
            port = ft4222.GPIO.Port.P1
        elif pin == 2:
            port = ft4222.GPIO.Port.P2
        elif pin == 3:
            port = ft4222.GPIO.Port.P3
        self.device.gpio_Write(port, state)