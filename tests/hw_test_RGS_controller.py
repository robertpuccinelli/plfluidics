import logging
from logging.handlers import TimedRotatingFileHandler
import os
from time import sleep
from plfluidics.server.valve_controller import ValveControllerRGS

cdir = os.path.dirname(os.path.abspath(__file__))
ndir = os.path.join(cdir, "logs")
os.makedirs(ndir, exist_ok=True)
filename = os.path.basename(__file__)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s [%(name)s]', datefmt='%H:%M:%S')
handler_file = TimedRotatingFileHandler(filename=cdir + '/logs/' + filename + '.log', when='m', interval=1, backupCount=1)
handler_file.setLevel(logging.INFO)
handler_file.setFormatter(formatter)

logger.addHandler(handler_file)

logger.info('Beginning script : HW Test RGS Controller')

valves = []

for i in range(0,24):
    valves.append([i,False,False,'V'+str(i)])

VCRGS = ValveControllerRGS(valves)

logger.info('Opening valves sequentially.')
for valve in valves:
    VCRGS.setValvesOpen([valve[3]])
    sleep(0.01)

logger.info('Closing valves sequentially.')
for valve in valves:
    VCRGS.setValvesClosed([valve[3]])
    sleep(0.01)

