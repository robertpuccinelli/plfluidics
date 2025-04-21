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
valve_names = ['OUT', 'IN', 'WASH', 'BSA', 'STREP', 'AB', 'EXTRA', 'PHAGE', 'WASTE', 'P1', 'P2', 'P3']

pol = False
state = False

for i in range(7):
    valves.append([i,pol,state,valve_names[i]])

valves.append([7,pol,state])
valves.append([9,pol,state,valve_names[7]]) # Defunct wiring
valves.append([8,pol,state,valve_names[8]])

for i in range(10,16):
    valves.append([i,pol,state])

valves.append([16, pol, state, valve_names[9]])
valves.append([17, pol, state, valve_names[10]])
valves.append([18, pol, state, valve_names[11]])

for i in range(19,24):
    valves.append([i,pol,state])

print(valves)

VCRGS = ValveControllerRGS(valves)

logger.info('Opening valves sequentially.')
for valve in valve_names:
    VCRGS.setValvesOpen([valve])
    sleep(0.01)

logger.info('Closing valves sequentially.')
for valve in valve_names:
    input('Press enter close valve {} '.format(valve))
    VCRGS.setValvesClosed([valve])

