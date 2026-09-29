import logging
from plfluidic.drivers.ne_syringe_pump import NEUSB
from plfluidic.hardware.syringe_pump import NEPump
from abc import ABC, abstractmethod

from typing import TypedDict

logger = logging.getLogger(__name__)


class PumpConfig(TypedDict):
    alias: str
    interface: object
    address: str
    diameter: float
    direction: str
    mode: str
    rate: float
    rate_units: str
    vol: float
    vol_units: str


class SyringeControllerBase(ABC):
    def __init__(self, driver_params):
        self.pumps = {}
        self.pump_aliases = []
        self.driver = None
        self.driver = self._loadDriver(driver_params)

    def createPumps(self, pump_config_list):
        for pump in pump_config_list:
            try:
                self.pumps[pump.alias] = self._initializePump(pump)
            except:
                self.pumps = {}
            
    @abstractmethod
    def _loadDriver(self, *args, **kwargs):
        pass

    @abstractmethod
    def _initializePump(self, pump: PumpConfig):
        pass

    def setPumpStart(self, pump_alias):
        self.pumps[pump_alias].start()

    def setPumpStop(self, pump_alias):
        self.pumps[pump_alias].stop()

    def setPumpPurge(self, pump_alias):
        self.pumps[pump_alias].purge()

    def setPumpDir(self, pump_alias, dir):
        self.pumps[pump_alias].direction = dir

    def setPumpMode(self, pump_alias, mode):
        self.pumps[pump_alias].mode = mode

    def setPumpRate(self, pump_alias, quantity, units):
        self.pumps[pump_alias].units_rate = units
        self.pumps[pump_alias].rate = quantity

    def setPumpVol(self, pump_alias, quantity, units):
        self.pumps[pump_alias].units_vol = units
        self.pumps[pump_alias].vol = quantity


class SyringeControllerNE(SyringeControllerBase):

    def __init__(self, *args, **kwargs):
        super.__init__(self, *args, **kwargs)

    def _loadDriver(self, port):
        try:
            driver = NEUSB(port)
            driver.open()

        except:
            driver = None

        return driver

    def _initializePump(self, pump: PumpConfig):
        try:
            pump = NEPump(interface=self.driver,
                          address= pump.address,
                          diameter= pump.diameter, 
                          direction=pump.direction, 
                          mode=pump.mode, 
                          rate = pump.rate, 
                          rate_units = pump.rate_units, 
                          volume=pump.vol, 
                          volume_units=pump.vol_units)
        except:
            pump = None

        return pump