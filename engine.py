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

    class ValveActions(Enum):
        """Allowable actions for valves."""
        OPEN    = auto()
        CLOSE   = auto()


    class ConfigFields(Enum):
        """Required fields for initializing engine from config file."""
        NAME        = auto()    # Name of run type
        CTLR_TYPE   = auto()    # Controller type, ie RGS
        PROGRAM_LOG = auto()    # Default program log location
        LOG_LEVEL   = auto()    # Log level to capture in run


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
        1. Define aliases for valves and groups. These aliases are used for facilitating human readable programs.
        2. Define valve sets for groups and tasks such as pumps.
        3. Describe hardware such as valve controller and addresses
        4. Define interface parameters such as logfile location
        """
        try:
            config, opts = validateConfig(self.config_path, self.ConfigFields)
            name        = config['DEFAULT']['NAME']
            vc_type     = config['DEFAULT']['CTLR_TYPE']
            logfile     = config['DEFAULT']['PROGRAM_LOG'] + name + strftime("_%Y%m%d_%H%M",localtime()) + '.log'
            loglevel    = config['DEFAULT']['LOG_LEVEL']

            # Add handler to existing logger to store the current session in a designated file/level
            handler_file = logging.FileHandler(logfile, mode='a')
            if loglevel.upper() == 'DEBUG':
                handler_file.setLevel(logging.DEBUG)
            elif loglevel.upper() == 'WARNING':
                handler_file.setLevel(logging.WARNING)
            else:
                handler_file.setLevel(logging.INFO)
            handler_file.setFormatter(formatter)
            logger.addHandler(handler_file)

            # Process config by valve controller type
            if vc_type is 'RGS':
                # Extract parameters
                default_state = config['RGS']['VALVE_STATE'].upper()
                default_polarity = config['RGS']['VALVE_POL'].upper()
                num_valves = config['DEFAULT'].getint('VALVE_NUM')
                valves = []

                # Translate default values
                if default_polarity == 'INV':
                    pol = True
                else:
                    pol = False

                if default_state == 'OPEN':
                    state = True
                else:
                    state = False

                # Structure valve settings w/ aliases
                alias = []
                for i in range(0, num_valves):
                    alias.append(config['RGS']['VALVE'+ str(i)])
                    valves.append([i, pol, state, alias[i]])

                # Initialize valve controller + valves
                vc = ValveControllerRGS(valves)
            else:
                raise ValueError("Valve controller type is not recognized: {}".format(vc_type))

            # Extract valve groups
            vg_items = [item for item in list(config['VALVE_GROUPS'].items()) if item not in list(config['DEFAULT'].items())]

            # Validate and store valve groups in dictionary
            valve_groups = {}
            if vg_items:
                for key, value in vg_items():
                    item_list = value.upper().split(',')
                    if not set(item_list).issubset(alias):
                        raise ValueError('Valve alias in group not recognized. {}:{}'.format(key,item_list))
                    valve_groups[key.upper()] = item_list

            self.vc = vc
            self.alias = alias
            self.valve_groups = valve_groups

        except ValueError as e:
            logger.warning("Value error encountered. {}".format(e))

        except KeyError as e:
            logger.warning("Key error encountered: {}".format(e))

    def processProgram(self, program_file):
        """Process program script to catch errors before execution and estimate duration."""
        try:
            with open(program_file, 'r') as f:
                line_num = 1
                prog_timer = 0
                buffer = []
                for line in f:
                    line_args = line.upper().strip().split(' ')
                    assert line_args[0] in self.Commands.__members__, 'Command key not recognized: {}'.format(line_args[0])
                    
                    match line_args[0]:

                        case 'VALVE':
                            # Format: [VALVE,VALVE1,OPEN,5S] - Open Valve1 and wait 5s
                            if line_args[1] in self.alias or self.valve_groups:
                                assert line_args[2] in self.ValveActions.__members__, "Valve action not recognized - {}".format(line_args[2])
                                if len(line_args) > 3:
                                    try:
                                        duration = int(line_args[3])
                                    except ValueError:
                                        raise ValueError('Duration argument is not numeric: {}'.format(line_args[3]))
                                else:
                                    duration = 0

                                # Add line to buffer
                                if line_args in self.alias:
                                    buffer.append(line_args[0:3] + [duration])

                                # Split group into individual commands and append timer to last entry
                                else:
                                    for group, valves in self.valve_groups:
                                        if line_args[1] == group:
                                            for valve in valves[:-1]:
                                                buffer.append(line_args[0] + [valve] + line_args[2] + [0])
                                            buffer.append(line_args[0] + valves[-1] + line_args[2] + [duration])
                                                                 
                        case 'PUMP':
                            # Format: [PUMP,PUMP1,5,5S] - Pump Pump1 for 5 seconds at 5Hz
                            pass
                    
                    prog_timer += duration
                    line_num += 1


        except Exception as e:
            logger.warning("Program error on line {}. {}".format(line_num, e))

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


    