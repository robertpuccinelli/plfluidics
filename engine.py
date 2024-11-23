"""
Runs a state machine for translating inputs into device states.

Inputs include config file, steps file, and user input.
Output includes device state. 
"""



from enum import Enum, auto
from time import time, localtime, strftime
import logging

from plfluidics import ValveControllerRGS
from pyconfighandler import validateConfig

logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s [%(name)s]', datefmt='%H:%M:%S')

class Engine():
        
    class States (Enum):
        """Fluidic engine state machine states."""
        IDLE    = auto()    # Idle state for inactive system
        RUN     = auto()    # Run state for active system
        HOLD    = auto()    # Holding state for pausing program command stream
        PROC    = auto()    # Processing state for digesting commands
        EXE     = auto()    # Execution state for processed commands

    
    class Commands (Enum):
        """Tasks that run on an independent scheduler."""
        PUMP    = auto()
        VALVE   = auto()


    class ConfigFields(Enum):
        """Required fields for initializing engine from config file."""
        NAME        = auto()    # Name of run type
        CTLR_TYPE   = auto()    # Controller type, ie RGS
        PROGRAM_DEF = auto()    # Default program to load
        PROGRAM_LOG = auto()    # Default program log location


    def __init__(self, config = None, program = None):
        self.buffer = []
        self.config = config
        self.program = program

        self.flag_config = False
        self.flag_program = False
        self.flag_task = False
        self.flag_input = False
        self.flag_hold = False
        self.flag_exe = False

        if self.config:
            self.buffer.append(["load", "config",self.config])
            if self.program:
                self.buffer.append(["load","program", self.program])


        self.time_run_now   = time()
        self.time_run_next  = self.time_run_now
        self.time_pump_now  = self.time_run_now
        self.time_pump_next = self.time_run_now

        self.state_curr = self.States.IDLE
        self.action = []

        self.run()

    def run(self):
        state_func = {
            self.States.IDLE:   self.funcIdle,
            self.States.RUN:    self.funcRun,
            self.States.HOLD:   self.funcHold,
            self.States.EXE:    self.funcExe,
        }

        while(1):
            state_func[self.state_curr]()


    def funcIdle(self):
        if self.buffer:
            self.state_curr = self.State.PROC

    def funcRun(self):
        if self.buffer:
            self.state_curr = self.State.PROC

    def processInput(self):
        logger.debug("Entered Proc state")
        line = self.buffer.pop(0)
        logger.debug("Line to be processed: {}".format(line))
        arg1 = line[0].upper()

        try:
            if arg1 == "LOAD":
                arg2 = line[1].upper()
                assert arg2 == "CONFIG" or "PROG", "Can only load config or prog"
                assert len(line) == 3, "Need filepath for load operations"
                self.action = [arg2, line[3]]
                logger.debug("Loading input processed: {}".format(self.action))

            elif arg1 == "VALVE":
                arg2 = line[1].upper()  # Valve ID
                arg3 = line[2].upper()  # Valve action
                if len(line) > 3:       # Time to hold on step
                    arg4 = line[3]
                    unit = arg4[-1].upper()
                    if unit == 'S':
                        arg4_s = float(arg4[0:-1])
                    elif unit == 'M':
                        arg4_s = float(arg4[0:-1])*60
                    elif unit == 'H':
                        arg4_s = float(arg4[0:-1])*3600
                    else:
                        arg4_s = 0
                        logger.warning("Unit '{}' not recognized. Time set to 0.".format(unit)) 
                else:
                    arg4_s = 0
                self.action = [arg1, arg2, arg3, arg4_s]
                logger.debug("Valve input processed: {}".format(self.action))

            elif arg1 == "PUMP":
                arg2 = []   # Valves in pump
                for valve in line[1]:
                    arg2.append(valve.upper())
                arg3 = line[2].upper()  # Pump action
                arg4 = float(line[3])   # Cycle frequency
                if len(line > 4):
                    arg5 = int(line[4])     # Number of cycles
                else:
                    arg5 = -1
                self.action = [arg1, arg2, arg3, arg4, arg5]
                logger.debug("Pump input processed: {}".format(self.action))

            elif arg1 == "HOLD":
                self.action = arg1
                logger.debug("Hold input processed")
                return

            elif arg1 == "RESUME":
                self.action = arg1
                logger.debug("Resume input processed")
                return
            
            elif arg1 == "STOP":
                self.action = arg1
                logger.debug("Stop input processed")

        except Exception as e:
            logger.warning("Unexpected input received in buffer: {}. Error message: {}".format(line, e))

    def processConfig(self, config_file):
        """Translates config file to system settings.
        
        Config file has a few objectives:
        1. Define aliases for valves, groups and tasks. These aliases are used for facilitating human readable programs.
        2. Define valve sets for groups and tasks such as pumps.
        3. Describe hardware such as valve controller and addresses
        4. Define interface parameters such as logfile location
        """
        try:
            config, opts = validateConfig(self.config_path, self.ConfigFields)
            name    = config['DEFAULT']['NAME']
            vc_type = config['DEFAULT']['CTLR_TYPE']
            program = config['DEFAULT']['PROGRAM_DEF']
            logfile = config['DEFAULT']['PROGRAM_LOG'] + name + strftime("_%Y%m%d_%H%M",localtime()) + '.log'
            loglevel = config['DEFAULT']['LOG_LEVEL']

            # Add handler to existing logger to store the current session
            handler_file = logging.FileHandler(logfile, mode='a')
            if loglevel.upper() == 'DEBUG':
                handler_file.setLevel(logging.DEBUG)
            else:
                handler_file.setLevel(logging.INFO)
            handler_file.setFormatter(formatter)
            logger.addHandler(handler_file)

            # Process config by valve controller type
            if vc_type is 'RGS':
                default_state = config['RGS']['VALVE_STATE'].upper()
                default_polarity = config['RGS']['VALVE_POL'].upper()
                num_valves = config['DEFAULT'].getint('VALVE_NUM')
                valves = []

                if default_polarity == 'INV':
                    pol = True
                else:
                    pol = False

                if default_state == 'OPEN':
                    state = True
                else:
                    state = False

                for i in range(0, num_valves):
                    alias = config['RGS']['VALVE'+ str(i)]
                    valves.append([i, pol, state, alias])

                self.vc = ValveControllerRGS(valves)
            else:
                raise RuntimeError("Valve controller type is not recognized: {}".format(vc_type))

            # Process valve groups
            vg_items = [item for item in list(config['VALVE_GROUPS'].items()) if item not in list(config['DEFAULT'].items())]

            self.valve_groups = {}
            if vg_items:
                for key, value in vg_items:
                    self.valve_groups[key.upper()] = value.upper().split(',')


        except ValueError:
            logger.warning("Configuration file not found: {}".format(self.config_path))

        except KeyError as e:
            logger.warning("Key not found in configuration file: {}".format(e))

        except RuntimeError as e:
            logger.warning("Runtime error encountered. {}".format(e))

    def funcExe(self):
        match self.action[0]:

            case "VALVE":
                pass

            case "PUMP":
                pass

            case "HOLD":
                pass

            case "RESUME":

                pass

            case "STOP":
                pass

            case "LOAD":
                act = self.action[1]
                if act == "CONFIG":
                    pass
                    
                elif act == "PROG":
                    pass

            case _:
                pass

    def funcHold():
        pass


    