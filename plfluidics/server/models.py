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
from plfluidics.valves.valve_controller import ValveControllerRGS, SimulatedValveController

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
        if formatted_data['driver'] not in self.options['driver_options']:
            msg = f'Driver not in recognized list: {self.options['driver_options']}'
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
            elif isinstance(value, str):
                new_dict[key.lower()] = value.lower()
            elif isinstance(value, bool):
                new_dict[key.lower()] = value 
            elif isinstance(value, dict):
                new_dict[key.lower()] = self.lowercaseDict(value)
            else:
                msg = f'Config not formatted properly. Key: {key}'
                self.logger.debug(msg)
                raise ValueError(msg)
        self.logger.debug('Dict data converted to lowercase.')
        return new_dict
    

class ModelValves():

    def __init__(self, logger_name=None):
        if logger_name:
            self.logger = logging.getLogger(logger_name)
        else:
            self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')
        self.logger.setLevel(logging.DEBUG)
        config_fields = ['config_name','author','date', 'device','driver','valves']
        driver_options = ['rgs', 'simulation','none']
        valve_fields = ['valve_alias','solenoid_number', 'default_state_closed','inv_polarity']
        valve_commands = ['open', 'close']
        self.options = {'config_fields': config_fields, 
                        'driver_options': driver_options, 
                        'valve_fields': valve_fields, 
                        'valve_commands': valve_commands}
        
        self.reset()
        self.logger.debug('ModelValves initialized.')

    def reset(self):
        self.logger.debug('Resetting ModelValves to default values.')
        server_status = {'status': 'no_config', 
                         'valve_states':{}}
        config_status = {'config_name':'none',
                         'driver':'none',
                         'device':'none',
                         'valves':[]}
        self.data = {'server': server_status, 'config': config_status, 'controller':[]}

    def optionsGet(self):
        return self.options

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
        self.logger.info(f'Configuration set: {self.data['config']['config_name']}')
        
    def driverSet(self):
        self.logger.debug('Setting driver for valve controller.')
        config = self.configGet()
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
    
        if config['driver'] == 'rgs':
            self.data['controller'] = ValveControllerRGS(valve_list)
        elif config['driver'] == 'simulation':
            self.data['controller'] = SimulatedValveController(valve_list)
        elif config['driver'] == 'none':
            self.data['controller'] = []

        self.data['server']['valve_states']= valve_def_position
        self.logger.info(f'Valve controller driver set: {config['driver']}')         
    
    def openValve(self, valve):
        self.logger.debug(f'Opening valve: {valve}')
        self.data['controller'].setValveOpen(valve)
        self.data['server']['valve_states'][valve] = 'open'
        self.logger.info(f'Valve opened: {valve}')

    def closeValve(self, valve):
        self.logger.debug(f'Closing valve: {valve}')
        self.data['controller'].setValveClose(valve)
        self.data['server']['valve_states'][valve] = 'closed'
        self.logger.info(f'Valve closed: {valve}')


class ModelScript():
            
    def __init__(self, user_queue, script_queue, valve_list, logger_name=None):
        if logger_name:
            self.logger = logging.getLogger(logger_name)
        else:
            self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')
        self.logger.setLevel(logging.DEBUG)
        self.operations = ['open','close', 'wait', 'pump','pause']
        self.wait_units = ['s', 'm', 'h']
        self.pump_units = ['hz']
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

                if interrupt == 'skip':
                    self.logger.info(f'Skipping line: {self.line_count} {self.script[0]} ')
                    self.advance()
                    if self.script != []:
                        next_state = 'paused'
                    else:
                        self.logger.info('End of script.')
                        next_state = self.stop()
                        self.logger.debug(f'Changing to {next_state} from {self.state}')

                if interrupt == 'stop':
                    next_state = self.stop()
                    self.logger.debug(f'Changing to {next_state} from {self.state}')


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
            sleep(.01)
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

    def execute(self):
        cmd = self.script[0]
        self.logger.info(f'Line: {self.line_count} {cmd}')
        if cmd[0] == 'open':
            self.scriptQ.put(['open', cmd[1]])
        elif cmd[0] == 'close':
            self.scriptQ.put(['close', cmd[1]])
        elif cmd[0] == 'wait':
            self.time_step_duration = cmd[1]
            self.time_step_next = time() + self.time_step_duration
            self.scriptQ.put(['t_n',cmd[1]])
        elif cmd[0] == 'pause':
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

                        if (op[0] == 'open') or (op[0] == 'close'):
                            if len(op) < 2:  # Identify missing argument
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `{op[0]} requires a valve.')
                            valve = op[1]
                            if valve not in self.valve_list:  # Identify typos
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Valve `{valve}` in operation `{op}` not recognized.')
                            new_line = [op[0],valve]

                        if op[0] =='wait':
                            if len(op) < 3:  # Identify missing argument
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `wait` requires a duration and unit of time.')
                            if not op[1].isdigit():  # Check if wait duration is an integer
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `wait` duration length is not an integer - {op[1]}')
                            if op[2] not in self.wait_units:  # Check if wait unit is recognized
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `wait` duration unit must be one of the following - {self.wait_units}')                    
                            step_time = 0
                            if op[2] == 'm':
                                step_time = 60 * int(op[1])
                            elif op[2] == 'h':
                                step_time = 3600 * int(op[1])
                            else:
                                step_time = int(op[1])
                            approx_time += step_time
                            new_line = [op[0], step_time]

                        if op[0] == 'pump':
                            if len(op) < 3:  # Identify missing argument
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `pump` requires a frequency value and unit.')
                            if not op[1].isdigit():  # Check if frequency value is an integer
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `pump` frequency value is not an integer - {op[1]}')
                            if op[2] not in self.pump_units:  # check if frequency unit is recognized
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `pump` unit must be one of the following - {self.pump_units}')
                            new_line = [op[0], op[1]]

                        if op[0] == 'pause':
                            new_line = [op[0]]

                if new_line:
                    new_script.append(new_line)

        except Exception as e:
            raise e
        
        self.script = new_script
        self.time_expected = approx_time

        return new_script