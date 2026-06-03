import ftd2xx
import logging


class FT245RHub():
    
    def __init__(self):
        self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')
        self.serials = []
        self.devices = {}
        self.device_states = {}

    def __del__(self):
        for device in self.devices:
            try:
                device.close()
            except:
                pass

    def detectDevices(self):
        self.num_devices = ftd2xx.createDeviceInfoList()
        self.serials = []
        if self.num_devices != 0:
            for i in range(self.num_devices):
                serial = ftd2xx.getDeviceInfoDetail(i)['serial']
                self.serials.append(serial)
                self.logger.debug(f"FT245R device detected : {serial}")
        else:
            self.logger.warning("No FT245R devices detected.")

    def connectDevice(self, serial):
        try:
            dev = ftd2xx.openEx(serial)
            dev.setBitMode(0xFF, 0x01)
            self.devices[serial] = dev
            self.device_states[serial] = 0x00
        except ftd2xx.DeviceError as e:
            raise ValueError(f"FT245R device not found : {serial}")
        
    def disconnectDevice(self, serial):
        try:
            dev = self.devices[serial]
            del self.devices[serial]
            del self.device_states[serial]
            dev.close()

        except Exception as e:
            self.logger.warning(f"FT245R device encountered an issue when closing! {serial} : {e}")

    def writeState(self, serial, data):
        self.logger.debug(f"Writing {data} to FT245R {serial}")
        self.devices[serial].write(bytes([data]))

    def setOutputOff(self, serial, output):
        self.logger.debug(f"Setting output {output} off for FT245R {serial}")
        state = self.devices[serial].getBitMode()
        state = state &~ (0x01 << output)
        self.writeState(serial, state)

    def setOutputOn(self, serial, output):
        self.logger.debug(f"Setting output {output} on for FT245R {serial}")
        state = self.devices[serial].getBitMode()
        print(state)
        state = state | (0x01 << output)
        print(state)
        self.writeState(serial, state)