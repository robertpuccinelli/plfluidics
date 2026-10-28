'''Model in model-view-controller framework for microfluidic hardware control application.

Model:
- Represents server state, hardware state
- Stores methods that are called by controller
- Updates state as dictated
- Returns to controller
'''
from time import time, sleep
import json
import logging
from enum import StrEnum
from plfluidic.hardware.valve_controller import ValveControllerRGS, SimulatedValveController, ValveControllerPLRD1, ValveControllerFT425R
from plfluidic.hardware.syringe_controller import SyringeControllerNE, SyringeControllerSimulation, PumpConfig
from plfluidic.hardware.syringe_pump import SyringePumpBase

class ModelConfig():
    def __init__(self, options, logger_name=None):
        if logger_name:
            self.logger = logging.getLogger(logger_name)
        else:
            self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')
        self.logger.setLevel(logging.DEBUG)
        self.options = options
        self.file_list = None
        self.selected = None
        self.file_name = None
        self.error = None
        self.preview_text = "<center>Previewed files can be edited.<br>Edited configs can be loaded without saving.</center>"
        self.logger.debug('ModelConfig initialized.')

    def processConfig(self, data):
        '''Validate configuration format and extract data'''
        self.logger.debug(f'Processing config data: {data}')
        formatted_data = self.lowercaseDict(data)
        config_fields = set(self.options['config_fields'])
        config_set = set(formatted_data)
        if config_fields.difference(config_set):
            msg = f'Key missing in config: {config_fields.difference(config_set)}'
            self.logger.debug(msg)
            raise KeyError(msg)   
        if config_set.difference(config_fields):
            msg = f'Extra keys found in config: {config_set.difference(config_fields)}'
            self.logger.debug(msg)
            raise KeyError(msg)
        if formatted_data['valve_driver'] not in self.options['valve_driver_options']:
            msg = f'Valve driver not in recognized list: {self.options["valve_driver_options"]}'
            self.logger.debug(msg)
            raise ValueError(msg)
        if formatted_data['pump_driver'] not in self.options['pump_driver_options']:
            msg = f'Pump driver not in recognized list: {self.options["pump_driver_options"]}'
            self.logger.debug(msg)
            raise ValueError(msg)
        new_config={}
        for field in self.options['config_fields']:
            new_config[field] = formatted_data[field]
        self.logger.info('Configuration data processed successfully.')
        return new_config

    def configLinearize(self, data):
        # Linearize valve data from dict of dicts to list of dicts
        self.logger.debug(f'Linearizing config data: {data}')
        msg = []
        try:
            valves = data['valves']
            valve_fields = self.options['valve_fields'].copy()
            valve_fields.remove('valve_alias')
            valve_data = []

            for valve in valves:
                try:
                    temp_valve = {'valve_alias': valve}
                    temp_valve = temp_valve | {key:valves[valve][key] for key in valve_fields}
                except Exception as e:
                    msg = f'Field missing from valve configuration: {e}'
                    raise KeyError(msg)
                valve_data.append(temp_valve)
            data['valves'] = valve_data

            pumps = data['pumps']
            pump_fields = self.options['pump_fields'].copy()
            pump_fields.remove('pump_alias')
            pump_data = []

            for pump in pumps:
                try:
                    temp_pump = {'pump_alias': pump}
                    temp_pump = temp_pump | {key:pumps[pump][key] for key in pump_fields}
                except Exception as e:
                    msg = f'Field missing from pump configuration: {e}'
                    raise KeyError(msg)
                pump_data.append(temp_pump)
            data['pumps'] = pump_data

        except Exception as e:
            if not msg:
                msg = f'Error transforming config to model format. {e}'
            self.logger.debug(msg)
            raise KeyError(self.error)
        self.logger.debug('Configuration data linearized successfully.')
        return data

    def lowercaseDict(self, data):
        '''Change text in dict to be lowercase.'''
        self.logger.debug(f'Converting dict to lowercase format: {data}')
        if isinstance(data,str):
            data = json.loads(data)
        new_dict = {}
        for key in set(data):
            value = data[key]
            if isinstance(value, int):
                new_dict[key.lower()] = value 
            elif isinstance(value, float):
                new_dict[key.lower()] = value
            elif isinstance(value, str):
                new_dict[key.lower()] = value.lower()
            elif isinstance(value, bool):
                new_dict[key.lower()] = value 
            elif isinstance(value, dict):
                new_dict[key.lower()] = self.lowercaseDict(value)
            else:
                msg = f'Config not formatted properly. Key: {key}, Value: {value}'
                self.logger.debug(msg)
                raise ValueError(msg)
        self.logger.debug('Dict data converted to lowercase.')
        return new_dict
    

class ModelHardware():

    config_fields = ['config_name','author','date', 'device','valve_driver','valves', 'pump_driver','pumps']
    valve_driver_options = ['rgs', 'plrd1', 'ft245r_8', 'simulation','none']
    valve_fields = ['valve_alias','solenoid_number', 'default_state_closed','inv_polarity']
    valve_commands = ['open', 'close']
    pump_driver_options = ['ne', 'simulation', 'none']
    pump_fields = ['pump_alias', 'interface', 'address', 'diameter', 'direction', 'mode', 'rate', 'rate_units', 'vol', 'vol_units']
    pump_commands = ['start', 'stop', 'purge', 'dir', 'mode', 'rate', 'vol']
    
    options = {'config_fields': config_fields, 
                    'valve_driver_options': valve_driver_options, 
                    'valve_fields': valve_fields, 
                    'valve_commands': valve_commands,
                    'pump_driver_options': pump_driver_options,
                    'pump_fields': pump_fields,
                    'pump_commands': pump_commands}

    def __init__(self, logger_name=None):
        if logger_name:
            self.logger = logging.getLogger(logger_name)
        else:
            self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')
        self.logger.setLevel(logging.DEBUG)        
        self.reset()
        self.logger.debug('ModelHardware initialized.')

    def reset(self):
        self.logger.debug('Resetting ModelHardware to default values.')
        server_status = {'status': 'no_config', 
                         'valve_states':{}}
        config_status = {'config_name': 'none',
                         'device': 'none',
                         'valve_driver': 'none',
                         'valves':[],
                         'pump_driver': 'none',
                         'pumps': []}
        self.data = {'server': server_status, 'config': config_status, 'valve_controller':[], 'pump_controller':[]}

    @classmethod
    def optionsGet(cls):
        return cls.options

    def statusGet(self):
        return self.data['server']

    def configGet(self):
        return self.data['config']

    def configSet(self, new_config):
        self.logger.debug(f'Setting new configuration: {new_config}')
        curr_config = self.configGet()
        for key in curr_config.keys():
            curr_config[key] = new_config[key]
        self.reset()
        self.data['config']=curr_config
        self.data['server']['status'] = 'driver_not_initialized'
        self.logger.info(f'Configuration set: {self.data["config"]["config_name"]}')
        
    def driverSet(self):
        self.logger.debug('Setting driver for valve controller.')
        config = self.configGet()

        # Process valves
        valves = config['valves']
        valve_list = []
        valve_def_position = {}
        for valve in valves:
            v_name = valve['valve_alias']
            v_num = valve['solenoid_number']
            pol = valve['inv_polarity']
            ds = valve['default_state_closed'] 
            valve_list.append([v_num,pol,ds,v_name])
            if ds:
                valve_def_position[v_name] = 'open'
            else:
                valve_def_position[v_name] = 'closed'

        valve_driver = config['valve_driver']
    
        if valve_driver == 'rgs':
            self.data['valve_controller'] = ValveControllerRGS(valve_list)
        elif valve_driver == 'simulation':
            self.data['valve_controller'] = SimulatedValveController(valve_list)
        elif valve_driver == 'plrd1':
            self.data['valve_controller'] = ValveControllerPLRD1(valve_list)
        elif valve_driver == 'ft245r_8':
            self.data['valve_controller'] = ValveControllerFT425R(valve_list)
        elif valve_driver == 'none':
            self.data['valve_controller'] = []

        self.data['server']['valve_states'] = valve_def_position
        self.logger.info(f'Valve controller driver set: {config["valve_driver"]}') 

        # Process syringe pumps
        pumps = config['pumps']
        pump_list = []
        for pump in pumps:
            pconfig = PumpConfig()
            pconfig['alias'] = pump['pump_alias']
            pconfig['interface'] = pump['interface']
            pconfig['address'] = pump['address']
            pconfig['diameter'] = pump['diameter']
            pconfig['direction'] = pump['direction'] 
            pconfig['mode'] = pump['mode']
            pconfig['rate'] = pump['rate']
            pconfig['rate_units'] = pump['rate_units']
            pconfig['vol'] = pump['vol']
            pconfig['vol_units'] = pump['vol_units']

            pump_list.append(pconfig)

        pump_driver = config['pump_driver']

        if pump_driver == 'ne':
            self.data['pump_controller'] = SyringeControllerNE(pump_list)
            self.data['pump_controller'].createPumps()

        elif pump_driver == 'simulation':
            self.data['pump_controller'] = SyringeControllerSimulation(pump_list)
            self.data['pump_controller'].createPumps()
    
        elif pump_driver == 'none':
            self.data['pump_controller'] = []

        self.logger.info(f'Pump controller driver set: {config["pump_driver"]}')
    
    def openValve(self, valve):
        self.logger.debug(f'Opening valve: {valve}')
        self.data['valve_controller'].setValveOpen(valve)
        self.data['server']['valve_states'][valve] = 'open'
        self.logger.info(f'Valve opened: {valve}')

    def closeValve(self, valve):
        self.logger.debug(f'Closing valve: {valve}')
        self.data['valve_controller'].setValveClose(valve)
        self.data['server']['valve_states'][valve] = 'closed'
        self.logger.info(f'Valve closed: {valve}')

    def startPump(self, pump):
        self.logger.debug(f'Starting pump: {pump}')
        self.data['pump_controller'].setPumpStart(pump)
        self.logger.info(f'Pump started: {pump}')

    def stopPump(self, pump):
        self.logger.debug(f'Stopping pump: {pump}')
        self.data['pump_controller'].setPumpStop(pump)
        self.logger.info(f'Pump stopped: {pump}')

    def purgePump(self, pump):
        self.logger.debug(f'Purging pump: {pump}')
        self.data['pump_controller'].setPumpPurge(pump)
        self.logger.info(f'Pump purging: {pump}')

    def dirPump(self, pump, dir):
        self.logger.debug(f'Setting pump direction: {pump} - {dir}')
        self.data['pump_controller'].setPumpDir(pump, dir)
        self.logger.info(f'Pump direction set: {pump} - {dir}')

    def modePump(self, pump, mode):
        self.logger.debug(f'Setting pump mode: {pump} - {mode}')
        self.data['pump_controller'].setPumpMode(pump, mode)
        self.logger.info(f'Pump mode set: {pump} - {mode}')

    def ratePump(self, pump, quantity, units):
        self.logger.debug(f'Setting pump rate: {pump} - {quantity} {units}')
        self.data['pump_controller'].setPumpRate(pump, quantity, units)
        self.logger.info(f'Pump rate set: {pump} - {quantity} {units}')

    def volPump(self, pump, quantity, units):
        self.logger.debug(f'Setting pump volume: {pump} - {quantity} {units}')
        self.data['pump_controller'].setPumpVol(pump, quantity, units)
        self.logger.info(f'Pump volume set: {pump} - {quantity} {units}')

    def modePump(self, pump, mode):
        self.logger.debug(f'Setting pump mode: {pump} - {mode}')
        self.data['pump_controller'].setPumpMode(pump, mode)
        self.logger.info(f'Pump mode set: {pump} - {mode}')

class ModelScript():

    class ScriptOperation(StrEnum):
        """A class that presents all operations supported in scripts. Suffix _v for valves and _s for syringes."""
        wait = "wait"
        pause = "pause"
        open_v = "open"
        close_v = "close"
        start_s = "start"
        stop_s = "stop"
        purge_s = "purge"
        dir_s = "dir"
        mode_s = "mode"
        rate_s = "rate"
        vol_s = "vol"

    class Unit_Wait(StrEnum):
        """A class that presents all supported wait duration units."""
        millisecond = "ms"
        second = "s"
        minute = "m"
        hour = "h"

            
    def __init__(self, user_queue, script_queue, valve_list=None, pump_list=None, logger_name=None):
        if logger_name:
            self.logger = logging.getLogger(logger_name)
        else:
            self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')
        self.logger.setLevel(logging.DEBUG)
        self.operations = [key.value for key in self.ScriptOperation]
        self.mode_values = [key.value for key in SyringePumpBase.Mode]
        self.rate_units = [key.value for key in SyringePumpBase.Unit_Rate]
        self.vol_units = [key.value for key in SyringePumpBase.Unit_Vol]
        self.wait_units = [key.value for key in self.Unit_Wait]
        self.file_list = []
        self.flag_thread_engine = False
        self.flag_pause = False
        self.line_count = 1
        self.preview_text = "Loaded script text\nis editable.\n\nScripts that are\nactively being executed\ncannot be edited."
        self.resetTimers()
        self.state = 'idle'
        self.selected = []
        self.script = []
        self.userQ = user_queue
        self.scriptQ = script_queue
        self.valve_list = valve_list
        self.pump_list = pump_list
        self.logger.debug('ModelScript initialized.')

    def engine(self):
        """State machine for executing scripts. Designed to be run as a threaded process.
        
            Future considerations - 
            If idle or paused, state machine can be blocked until message is presented by user.
            This would require reworking the logic for termination on a None signal, but would increase cpu availability, if needed.
        """
        self.logger.debug('Script engine initializing.')
        self.flag_thread_engine = True
        while(1):
            next_state = self.state
            interrupt = ''
            try:
                interrupt = self.userQ.get_nowait()
                self.userQ.task_done()
                self.logger.debug(f'Interrupt received: {interrupt}')
            except Exception as e:
                pass

            # IDLE #
            if self.state == 'idle':
                if interrupt == 'start-pause':
                    if self.script:
                        self.logger.info('Executing script.')
                        self.scriptQ.put(['t_e',self.time_expected])
                        self.line_count = 1
                        self.scriptQ.put(['line', self.line_count])
                        next_state = 'running'
                        self.logger.debug(f'Changing to {next_state} from {self.state}')

                if self.script == []:
                    self.scriptQ.put(None)  # Terminate controller thread
                    break
            
            # PAUSED #
            if self.state == 'paused':
                if interrupt == 'start-pause':
                    if self.time_step_next:
                        self.time_step_next = self.time_step_remaining + time()
                    next_state = 'running'
                    self.flag_pause = False
                    self.logger.debug(f'Changing to {next_state} from {self.state}')

                elif interrupt == 'skip':
                    self.logger.info(f'Skipping line: {self.line_count} {self.script[0]} ')
                    self.advance()
                    if self.script != []:
                        next_state = 'paused'
                    else:
                        self.logger.info('End of script.')
                        next_state = self.stop()
                        self.logger.debug(f'Changing to {next_state} from {self.state}')

                elif interrupt == 'stop':
                    next_state = self.stop()
                    self.logger.debug(f'Changing to {next_state} from {self.state}')

                elif interrupt == 'poll':
                    self.scriptQ.put(['line', self.line_count])
                    self.scriptQ.put(['t_e',self.time_expected])
                    self.scriptQ.put(['t_n',self.time_step_duration])
                    t_r = round(self.time_step_remaining)
                    self.scriptQ.put(['t_r', t_r, self.time_step_duration - t_r])
                    self.scriptQ.put(['t_a',self.time_expected - self.time_accumulated - self.time_step_duration + t_r, self.time_accumulated + self.time_step_duration - t_r])

            # RUNNING #
            if self.state == 'running':
                if interrupt == 'stop':
                    next_state = self.stop()
                    self.logger.debug(f'Changing to {next_state} from {self.state}')

                elif interrupt == 'start-pause':
                    self.time_step_remaining = self.time_step_next - time()
                    next_state = 'paused'
                    self.logger.debug(f'Changing to {next_state} from {self.state}')

                elif interrupt == 'skip':
                    self.logger.info(f'Skipping line: {self.line_count} {self.script[0]} ')
                    self.advance()
                    if self.script != []:
                        next_state = self.state
                    else:
                        next_state = self.stop()
                        self.logger.debug(f'Changing to {next_state} from {self.state}')

                elif interrupt == 'poll':
                    self.scriptQ.put(['line', self.line_count])
                    self.scriptQ.put(['t_e',self.time_expected])
                    self.scriptQ.put(['t_n',self.time_step_duration])
                    t_r = round(self.time_step_next - time())
                    self.scriptQ.put(['t_r', t_r, self.time_step_duration - t_r])
                    self.scriptQ.put(['t_a',self.time_expected - self.time_accumulated - self.time_step_duration + t_r, self.time_accumulated + self.time_step_duration - t_r])


                else:
                    if not self.time_step_next:
                        self.execute()

                    t_r = self.time_step_next - time()
                    if t_r < 0:
                        self.advance()
                    else: # Increment progress bar on interface every second
                        t_r_new = round(t_r)
                        if t_r_new != self.t_r_old:
                            self.scriptQ.put(['t_r', t_r_new, self.time_step_duration - t_r_new])
                            self.scriptQ.put(['t_a',self.time_expected - self.time_accumulated - self.time_step_duration + t_r_new, self.time_accumulated + self.time_step_duration - t_r_new])
                            self.t_r_old = t_r_new

                    if self.script != []:
                        if self.flag_pause == True:
                            next_state = 'paused'
                        else:
                            next_state = 'running'
                    else:
                        self.logger.info('End of script.')
                        next_state = self.stop()
                        self.logger.debug(f'Changing to {next_state} from {self.state}')
            self.state = next_state
            sleep(0.0001)
        self.flag_thread_engine = False
        self.logger.debug('Script engine terminated.')

    def resetStepTimers(self):
        self.logger.debug('Resetting step timers.')
        self.time_step_next = 0
        self.time_step_remaining = 0
        self.time_step_duration = 0
        self.t_r_old = 0

    def resetTimers(self):
        self.logger.debug('Resetting timers.')
        self.time_expected = 0
        self.time_accumulated = 0
        self.resetStepTimers()

    def advance(self):
        step = self.script.pop(0)
        self.logger.debug(f'Removing step {step} from script queue.')
        if step[0] == 'wait':
            self.resetStepTimers()
            self.time_accumulated += step[1]
            self.scriptQ.put(['t_n', 0])
            self.scriptQ.put(['t_r',0,0])
            self.scriptQ.put(['t_a',self.time_expected - self.time_accumulated,self.time_accumulated])

        self.line_count += 1
        self.scriptQ.put(['line', self.line_count])

    def execute(self):
        cmd = self.script[0]
        self.logger.info(f'Line: {self.line_count} {cmd}')
        if cmd[0] in [self.ScriptOperation.open_v, self.ScriptOperation.close_v, self.ScriptOperation.start_s, self.ScriptOperation.stop_s, self.ScriptOperation.purge_s]:
            self.scriptQ.put([cmd[0], cmd[1]])

        elif cmd[0] in [self.ScriptOperation.dir_s, self.ScriptOperation.mode_s]:
            self.scriptQ.put([cmd[0], cmd[1], cmd[2]])

        elif cmd[0] in [self.ScriptOperation.rate_s, self.ScriptOperation.vol_s]:
            self.scriptQ.put([cmd[0], cmd[1], cmd[2], cmd[3]])
        
        elif cmd[0] in [self.ScriptOperation.wait]:
            self.time_step_duration = cmd[1]
            self.time_step_next = time() + self.time_step_duration
            self.scriptQ.put(['t_n',self.time_step_duration])

        elif cmd[0] in [self.ScriptOperation.pause]:
            # Create a delay so that script does not advance
            # this gives controller time to interrupt script engine
            self.flag_pause = True
            self.scriptQ.put(['pause'])

    def stop(self):
        self.logger.info('Stopping script execution.')
        self.resetTimers()
        self.flag_pause = False
        self.script=[]
        self.line_count = 1
        next_state = 'idle'
        return next_state

    def processScript(self, input):
        """Process user submitted script.
        
        1. Breaks lines by carriage returns
        2. Skips empty lines
        3. Removes leading spaces
        4. Skips `#` comment lines
        5. Identifies operation
        6. Extracts necessary parameters (Ignores end of line comments)
        7. Returns processed script
        """
        self.logger.debug('Processing script.')
        try:
            approx_time = 0
            line_number = 0
            new_script = []
            input_list = input.lower().split('\n')  # Split script into list based on new lines
            for line in input_list:
                new_line = []
                if line:  # Skip empty lines
                    no_space = line.lstrip()  # Remove leading spaces
                    if no_space[0] !='#':  # Skip commented lines
                        line_number += 1
                        op = no_space.split(' ')  # Split line arguments by space
                        if op[0] not in self.operations:  # Identify operation
                            raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `{op[0]}` not in recognized list: {self.operations}.')

                        if op[0] in [self.ScriptOperation.open_v, self.ScriptOperation.close_v]:
                            if len(op) < 2:  # Identify missing argument
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `{op[0]} requires a valve.')
                            valve = op[1]
                            if valve not in self.valve_list:  # Identify typos
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Valve `{valve}` in operation `{op}` not recognized.')
                            new_line = [op[0],valve]

                        if op[0] in [self.ScriptOperation.start_s,self.ScriptOperation.stop_s,self.ScriptOperation.purge_s]:
                            if len(op) < 2:  # Identify missing argument
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `{op[0]} requires a pump.')
                            pump = op[1]
                            if pump not in self.pump_list:  # Identify typos
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Pump `{pump}` in operation `{op}` not recognized.')
                            new_line = [op[0],pump]

                        if op[0] in  [self.ScriptOperation.dir_s, self.ScriptOperation.mode_s]:
                            if len(op) < 3:  # Identify missing argument
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `{op[0]} requires a pump and value.')
                            pump = op[1]
                            if pump not in self.pump_list:  # Identify typos
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Pump `{pump}` in operation `{op}` not recognized.')
                            if (op[2] not in SyringePumpBase.Direction) and (op[2] not in SyringePumpBase.Mode):
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Argument `{op[2]}` in operation `{op}` not recognized.')
                            new_line = [op[0],pump, op[2]]

                        if op[0] in  [self.ScriptOperation.rate_s]:
                            if len(op) < 4:  # Identify missing argument
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `{op[0]} requires a pump, value, and unit.')
                            pump = op[1]
                            if pump not in self.pump_list:  # Identify typos
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Pump `{pump}` in operation `{op}` not recognized.')
                            try:  # Check if rate is numeric
                                float(op[2])
                            except:
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Quantity argument is not numeric - {op[2]}')
                            if op[3] not in (self.rate_units):
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Units `{op[3]}` in operation `{op}` not recognized.')
                            new_line = [op[0],pump, op[2], op[3]]

                        if op[0] in [self.ScriptOperation.vol_s]:
                            if len(op) < 4:  # Identify missing argument
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `{op[0]} requires a pump, value, and unit.')
                            pump = op[1]
                            if pump not in self.pump_list:  # Identify typos
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Pump `{pump}` in operation `{op}` not recognized.')
                            try:  # Check if volume is numeric
                                float(op[2])
                            except:
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Quantity argument is not numeric - {op[2]}')
                            if op[3] not in (self.vol_units):
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Units `{op[3]}` in operation `{op}` not recognized.')
                            new_line = [op[0],pump, op[2], op[3]]

                        if op[0] in [self.ScriptOperation.wait]:
                            if len(op) < 3:  # Identify missing argument
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `wait` requires a duration and unit of time.')
                            if not op[1].isdigit():  # Check if wait duration is an integer
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `wait` duration length is not an integer - {op[1]}')
                            if op[2] not in self.wait_units:  # Check if wait unit is recognized
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `wait` duration unit must be one of the following - {self.wait_units}')                    
                            step_time = 0
                            if op[2] == self.Unit_Wait.minute:
                                step_time = 60 * int(op[1])
                            elif op[2] == self.Unit_Wait.hour:
                                step_time = 3600 * int(op[1])
                            elif op[2] == self.Unit_Wait.millisecond:
                                step_time = 0.001 * int(op[1])
                            elif op[2] == self.Unit_Wait.second:
                                step_time = int(op[1])
                            approx_time += step_time
                            new_line = [op[0], step_time]

                        if op[0] in [self.ScriptOperation.pause]:
                            new_line = [op[0]]

                if new_line:
                    new_script.append(new_line)

        except Exception as e:
            raise e
        
        self.script = new_script
        self.time_expected = approx_time

        return new_script