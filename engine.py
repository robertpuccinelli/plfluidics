"""
Runs a state machine for translating inputs into device states.

Inputs include config file, steps file, and user input.
Output includes device state. 
"""



"""
Program state machine

Idle > user input > config > idle    <
                             ||     ||
                program < user input ^



    states:
    1. Idle
    2. Running
    3. Process
    4. Execute
"""

from enum import Enum
import logging

logger = logging.getLogger()


class Engine():
        
    class States (Enum):
        IDLE    = 0
        RUN     = 1
        HOLD    = 2
        PROC    = 3
        EXE     = 4

    def __init__(self, config = None, program = None):
        self.buffer = []
        self.config = config
        self.program = program

        if self.config:
            self.buffer.append(["load", "config",self.config])
            if self.program:
                self.buffer.append(["load","program", self.program])

        self.flag_pump = False
        self.flag_running = False
        self.state_curr = self.States.IDLE
        self.action = []

        self.run()

    def run(self):
        state_func = {
            self.States.IDLE:   self.funcIdle,
            self.States.RUN:    self.funcRun,
            self.States.HOLD:   self.funcHold,
            self.States.PROC:   self.funcProc,
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

    def funcProc(self):
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

            self.state_curr = self.States.EXE
                
        except Exception as e:
            logger.warning("Unexpected input received in buffer: {}. Error message: {}".format(line, e))
            if self.flag_running:
                self.state_curr = self.States.RUN
            else:
                self.state_curr = self.States.IDLE

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


    