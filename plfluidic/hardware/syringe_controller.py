import logging
from plfluidic.drivers.ne_syringe_pump import NEUSB
from plfluidic.hardware.syringe_pump import NEPump, SimulatedPump
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
    def __init__(self, pump_list):
        self._pump_config_list = pump_list
        self.pumps = {}
        self.pump_aliases = []
        self.driver = None
        self._loadDriver()

    def createPumps(self, pump_config_list=None):

        if pump_config_list == None:
            pump_config_list = self._pump_config_list

        for pump_config in pump_config_list:
            try:
                self.pumps[pump_config['alias']] = self._initializePump(pump_config)
                self.pump_aliases.append(pump_config['alias'])
            except Exception as e:
                self.pumps = {}
                raise 
            
    @abstractmethod
    def _loadDriver(self):
        pass

    @abstractmethod
    def _initializePump(self, pump_config: PumpConfig):
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
        super().__init__(*args, **kwargs)

    def _loadDriver(self):
        port = self._pump_config_list[0]['interface']
        try:
            driver = NEUSB(port)
            driver.open()

        except Exception as e:
            driver = None
            raise ConnectionError(f"Syringe pump driver could not be opened at {port}")

        self.driver = driver

    def _initializePump(self, pump_config: PumpConfig):
        try:
            pump = NEPump(interface=self.driver,
                          address= pump_config['address'],
                          diameter= pump_config['diameter'], 
                          direction=pump_config['direction'], 
                          mode=pump_config['mode'], 
                          rate = pump_config['rate'], 
                          rate_units = pump_config['rate_units'], 
                          volume=pump_config['vol'], 
                          volume_units=pump_config['vol_units'])
        except Exception as e:
            pump = None
            raise ValueError(f'Failed to initialize pump. {e}')

        return pump

class SyringeControllerSimulation(SyringeControllerBase):

    def _initializePump(self, pump_config: PumpConfig):
        try:
            pump = SimulatedPump(interface=self.driver,
                          address= pump_config['address'],
                          diameter= pump_config['diameter'], 
                          direction=pump_config['direction'], 
                          mode=pump_config['mode'], 
                          rate = pump_config['rate'], 
                          rate_units = pump_config['rate_units'], 
                          volume=pump_config['vol'], 
                          volume_units=pump_config['vol_units'])
        except:
            pump = None

        return pump

    def _loadDriver(self):
        pass