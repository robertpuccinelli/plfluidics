import logging
from plfluidic.drivers.ne_syringe_pump import NEUSB
from plfluidic.hardware.syringe_pump import NEPump

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


class SyringeControllerBase():
    def __init__(self):
        self.driver = []
        self.pumps = {}

    def _createPumps(self, pump_config_list):
        for pump in pump_config_list:
            alias = pump.alias
            pass

    def _loadDriver(self, driver_param_list):
        pass

    def processCmd(self, pump_alias, cmd, *args, **kwargs):
        pass
