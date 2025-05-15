'''Model in model-view-controller framework for microfluidic hardware control application.

Model:
- Represents server state, hardware state
- Stores methods that are called by controller
- Updates state as dictated
- Returns to controller
'''
from time import time
import json
from plfluidics.valves.valve_controller import ValveControllerRGS


class ModelValves():

    def __init__(self):
        config_fields = ['config_name','author','date', 'device','driver','valves']
        driver_options = ['rgs', 'none']
        valve_fields = ['valve_alias','solenoid_number', 'default_state_closed','inv_polarity']
        valve_commands = ['open', 'close']
        self.options = {'config_fields': config_fields, 
                        'driver_options': driver_options, 
                        'valve_fields': valve_fields, 
                        'valve_commands': valve_commands}
        
        self.reset()

    def reset(self):
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
        curr_config = self.configGet()
        for key in curr_config.keys():
            curr_config[key] = new_config[key]

        self.reset()
        self.data['config']=curr_config
        self.data['server']['status'] = 'driver_not_initialized'
        
    def driverSet(self):
        config = self.configGet()
        if config['driver'] == 'rgs':
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

            self.data['controller'] = ValveControllerRGS(valve_list)
            self.data['server']['valve_states']= valve_def_position

        elif config['driver'] == 'none':
            self.data['controller'] = []
            self.data['server']['valve_states']={}
    
    def openValve(self, valve):
        self.data['controller'].setValveOpen(valve)
        self.data['server']['valve_states'][valve] = 'open'

    def closeValve(self, valve):
        self.data['controller'].setValveClose(valve)
        self.data['server']['valve_states'][valve] = 'close'


class ModelConfig():
    def __init__(self, options):
        self.options = options
        self.file_list = None
        self.selected = None
        self.error = None
        self.preview_text = None

    def processConfig(self, data):
        '''Validate configuration format and extract data'''
        formatted_data = self.lowercaseDict(data)
        config_fields = set(self.options['config_fields'])
        config_set = set(formatted_data)
        if config_fields.difference(config_set):
            raise KeyError(f'Key missing in config: {config_fields.difference(config_set)}')   
        if config_set.difference(config_fields):
            raise KeyError(f'Extra keys found in config: {config_set.difference(config_fields)}')
        if formatted_data['driver'] not in self.options['driver_options']:
            raise ValueError(f'Driver not in recognized list: {self.options['driver_options']}')
        new_config={}
        for field in self.options['config_fields']:
            new_config[field] = formatted_data[field]
        return new_config

    def configLinearize(self, data):
        # Linearize valve data from dict of dicts to list of dicts
        self.error = None
        try:
            valves = data['valves']
            valve_fields = self.options['valve_fields']
            valve_fields.remove('valve_alias')
            valve_data = []
            for valve in valves:
                try:
                    temp_valve = {'valve_alias': valve}
                    temp_valve = temp_valve | {key:valves[valve][key] for key in valve_fields}
                except Exception as e:
                    self.error = f'Field missing from valve configuration: {e}'
                    raise KeyError(self.error)
                valve_data.append(temp_valve)
            data['valves'] = valve_data
        except Exception as e:
            if not self.error:
                self.error = f'Error transforming config to model format. {e}'
            raise KeyError(self.error)
        return data

    def lowercaseDict(self, data):
        '''Change text in dict to be lowercase.'''
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
                raise ValueError(f'Config not formatted properly. Key: {key}')
        return new_dict


class ModelScript():
            
    def __init__(self, user_queue, script_queue, valve_list):
        self.operations = ['open','close', 'wait', 'pump']
        self.wait_units = ['s', 'm', 'h']
        self.pump_units = ['hz']
        self.preview_text = []
        self.resetTimers()
        self.flag_wait = False
        self.state = 'idle'
        self.script = []
        self.userQ = user_queue
        self.scriptQ = script_queue
        self.valve_list = valve_list

    def engine(self):
        """State machine for executing scripts. Designed to be run as a threaded process.
        
            Future considerations - 
            If idle or paused, state machine can be blocked until message is presented by user.
            This would require reworking the logic for termination on a None signal, but would increase cpu availability, if needed.
        """

        while(1):
            next_state = self.state
            interrupt = ''
            try:
                interrupt = self.userQ.get_nowait()
            except Exception as e:
                pass

            if interrupt == None:
                self.scriptQ.put(None)
                break

            # IDLE #
            if self.state == 'idle':
                if interrupt == 'start-pause':
                    if self.script:
                        next_state = 'running'
            
            # PAUSED #
            if self.state == 'paused':
                if interrupt == 'start-pause':
                    self.time_step_next = time.time() + self.time_step_remaining
                    next_state = 'running'

                if interrupt == 'skip':
                    self.advance()
                    if self.script != []:
                        next_state = 'paused'
                    else:
                        next_state = 'idle'

                if interrupt == 'stop':
                    next_state = self.stop()

            # RUNNING #
            if self.state == 'running':
                if interrupt == 'stop':
                    next_state = self.stop()

                elif interrupt == 'start-pause':
                    self.time_step_remaining = self.time_step_next - time()
                    next_state = 'paused'

                elif interrupt == 'skip':
                    self.advance()
                    next_state = 'running'

                else:
                    if not self.time_step_next:
                        self.execute()

                    if self.time_step_next < time():
                        self.advance()

                    if self.script != []:
                        next_state = 'running'
                    else:
                        next_state = self.stop()

            self.state = next_state

    def resetStepTimers(self):
        self.time_step_next = 0
        self.time_step_remaining = 0

    def resetTimers(self):
        self.time_expected = 0
        self.time_accumulated = 0
        self.resetStepTimers()

    def advance(self):
        step = self.script.pop(0)
        if step[0] == 'wait':
            self.resetStepTimers()
            self.time_accumulated += step[1]
        self.line_count += 1

    def execute(self, cmd):
        if cmd[0] == 'open':
            self.scriptQ.put(['open', cmd[1]])
            self.flag_wait = False
        elif cmd[0] == 'closed':
            self.scriptQ.put(['close', cmd[1]])
            self.flag_wait = False
        elif cmd[0] =='wait':
            self.time_accumulated = cmd[1]
            self.time_step_next = time() + self.time_accumulated

    def stop(self):
        self.scriptQ.put(None)
        self.resetTimers()
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
        try:
            approx_time = 0
            line_number = 0
            new_script = []
            input_list = input.lower().split('\r\n')  # Split script into list based on carriage returns
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

                if new_line:
                    new_script.append(new_line)

        except Exception as e:
            raise e

        self.script = new_script
        self.time_expected = approx_time

        return new_script, approx_time