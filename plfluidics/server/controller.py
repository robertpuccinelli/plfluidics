'''Controller in model-view-controller framework for microfluidic hardware control application.
'''
import os
import json
import time
import importlib.resources
from logging import Logger
from flask import request, render_template, redirect, url_for
from plfluidics.server.models import ModelMicrofluidicController, ModelConfig


class MicrofluidicController():

    def __init__(self):
        self.config_model = ModelConfig()
        self.ctrl_model = ModelMicrofluidicController()
        self.error = None
        self.script_operations = ['open','close', 'wait', 'pump']
        self.script_wait_units = ['s', 'm', 'h']
        self.script_pump_units = ['hz']
        self.script_time_step_next = 0
        self.script_time_accumulated = 0
        self.script_time_step_duration = 0
        self.script_time_expected = 0
        self.script_wait = False
        self.script_run = False
        self.script_pause = False
        self.script_state
        self.script = []

    ################
    # PAGE SERVICE #
    ################

    def renderPage(self):
        if self.ctrl_model.data['server']['status'] == 'no_config':
            self.config_model.file_list, self.config_model.error = self.loadFileList('configs')
            return self.configPage()
        else:
            self.control_model.file_list, self.ctrl_model.error = self.loadFileList('scripts')
            return self.controlPage()

    def configPage(self):
        return render_template('config.html', model=self.config_model)

    def controlPage(self):
        return render_template(self.ctrl_model['config']['device'] + '.html', model = self.ctrl_model)
    
    def index(self):
        server_status = self.ctrl_model.data['server']['status']
        config_name = self.ctrl_model.data['config']['config_name']
        driver = self.ctrl_model.data['config']['driver']
        device_name = self.ctrl_model.data['config']['device']
        valve_states = self.ctrl_model.data['server']['valve_states']
        return render_template('index.html', 
                               status = server_status,
                               config_name = config_name,
                               driver = driver,
                               device_name = device_name,
                               valve_states=valve_states)

    def templatesDir(self):
        return f'{importlib.resources.files('plfluidics.server.templates').joinpath('config.html').parent}'
    
    ##########
    # CONFIG #
    ##########

    def configPreview(self):
        self.config_model.error = None
        try:
            file_name = request.form.get('item_selected')
            self.config_model.preview_text = self.configRead(file_name)
            self.config_model.selected = file_name
        except Exception as e:
            self.config_model.error = f'Error opening {file_name} : {e}'
        return self.renderPage()
 
    def configSave(self):
        self.config_model.error = None
        try:
            data=request.form.get('preview_content')
            self.config_model.preview_text=data
            config = self.processConfig(data)
            file_name = config['config_name']
            file_path = importlib.resources.files('plfluidics.server.configs').joinpath(file_name + '.config')
            with open(file_path, 'w') as f:
                json.dump(config,f, indent=4)
        except Exception as e:
            self.config_model.error = f'Error saving config. {e}'
        return self.renderPage()

    def configLoad(self):
        self.config_model.error = None
        try: 
            if self.config_model.preview_text:
                data=self.config_model.preview_text
            else:
                file_name = request.form.get('item_selected')  
                data = self.configRead(file_name)
            config = self.processConfig(data)
            linear_config = self.configLinearize(config)
            self.ctrl_model.configSet(linear_config)
            self.ctrl_model.driverSet()
        except Exception as e:
            self.config_model.error = f'Error loading config. {e}'
        return self.renderPage()

    def configChange(self):
        self.__init__()
        return self.renderPage()

    def configReload(self):
        self.ctrl_model.reset()
        self.configLoad()
        return self.renderPage()

    ####################
    # CONFIG UTILITIES #
    ####################

    def configRead(self, file_name):
            file_path = importlib.resources.files('plfluidics.server.configs').joinpath(file_name)
            with open(file_path, 'r') as f:
                file_content = f.read()
            return file_content

    def processConfig(self, data):
        '''Validate configuration format and extract data'''
        formatted_data = self.lowercaseDict(data)
        fields = self.ctrl_model.optionsGet()
        config_fields = set(fields['config_fields'])
        config_set = set(formatted_data)
        if config_fields.difference(config_set):
            raise KeyError(f'Key missing in config: {config_fields.difference(config_set)}')   
        if config_set.difference(config_fields):
            raise KeyError(f'Extra keys found in config: {config_set.difference(config_fields)}')
        if formatted_data['driver'] not in fields['driver_options']:
            raise ValueError(f'Driver not in recognized list: {fields['driver_options']}')
        new_config={}
        for field in fields['config_fields']:
            new_config[field] = formatted_data[field]
        return new_config
    
    def loadFileList(self, dir):
        error = None
        try:
            file_list = list(importlib.resources.contents('plfluidics.server.' + dir))
            if file_list == []:
                raise ValueError(f"No config files found in: {importlib.resources.files('plfluidics.server.' + dir)}")
        except Exception as e:
            error = e
        return file_list, error

    def configLinearize(self, data):
        # Linearize valve data from dict of dicts to list of dicts
        try:
            valves = data['valves']
            fields = self.ctrl_model.optionsGet()
            valve_fields = fields['valve_fields']
            valve_fields.remove('valve_alias')
            valve_data = []
            for valve in valves:
                try:
                    temp_valve = {'valve_alias': valve}
                    temp_valve = temp_valve | {key:valves[valve][key] for key in valve_fields}
                except Exception as e:
                    raise KeyError(f'Field missing from valve configuration: {e}')
                valve_data.append(temp_valve)
            data['valves'] = valve_data
        except Exception as e:
            self.config_model.error = f'Error transforming config to model format. {e}'
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

    #########
    # VALVE #
    #########

    def valveToggle(self, valve):
        try:
            valve=request.form.get('valve')
            if self.checkValveExists(valve):
                curr_state = self.ctrl_model.data['server']['valve_states'][valve]
                if curr_state == 'open':
                    self.ctrl_model.closeValve(valve)
                elif curr_state == 'closed':
                    self.ctrl_model.openValve(valve)
        except Exception as e:
            pass
        return redirect(url_for('index'))
    
    def valveOpenList(self):
        try:
            data=request.form.get('valve')
            valves_list = data.split(',')
            for valve in valves_list:
                self.ctrl_model.openValve(valve)
        except Exception as e:
            pass
        return redirect(url_for('index'))

    def valveCloseList(self):
        try:
            data=request.form.get('valve')
            valves_list = data.split(',')
            for valve in valves_list:
                self.ctrl_model.closeValve(valve)
        except Exception as e:
            pass
        return redirect(url_for('index'))

    ###################
    # VALVE UTILITIES #
    ###################

    def openValve(self, valve):
        if self.checkValveExists(valve):
            self.ctrl_model.openValve(valve)
        return redirect(url_for('index'))

    def closeValve(self, valve):
        if self.checkValveExists(valve):
            self.ctrl_model.closeValve(valve)
        return redirect(url_for('index'))

    def checkValveExists(self, valve):
        if valve in self.ctrl_model.data['server']['valve_states']:
            return True
        else:
            raise ValueError(f'Valve not present in model: {valve}')
        

    ##########
    # SCRIPT #
    ##########
    """
    script.preview_text
    ctrl_model.error
    """
        '''
        self.script_operations = ['open','close', 'wait', 'pump']
        self.script_wait_units = ['s', 'm', 'h']
        self.script_pump_units = ['hz']
        self.script_time_step_next = 0
        self.script_time_accumulated = 0
        self.script_time_step_duration = 0
        self.script_time_expected = 0
        self.script_wait = False
        self.script_run = False
        self.script_pause = False
        self.script_interrupt = False
        self.script_state = 'idle'
        self.script = []'''

    def scriptLoad(self):
        self.ctrl_model.error = None
        try:
            file_name = request.form.get('item_selected')
            self.ctrl_model.preview_text = self.configRead(file_name)
            self.ctrl_model.selected = file_name
        except Exception as e:
            self.ctrl_model.error = f'Error opening {file_name} : {e}'
        return self.renderPage()

    def scriptSave(self):
        self.ctrl_model.error = None
        try:
            file_name = request.form.get('text')
            data = request.form.get('preview_content')
            self.ctrl_model.preview_text=data
            script = self.processScript(data)
            # TODO - Check to see if user put .script at end of file
            file_path = importlib.resources.files('plfluidics.server.scripts').joinpath(file_name + '.script')
            with open(file_path, 'w') as f:
                json.dump(script,f, indent=0)
        except Exception as e:
            self.ctrl_model.error = f'Error saving script. {e}'
        return self.renderPage()

    def scriptToggle(self):
        pass

    def scriptSkip(self):
        pass

    def scriptStop(self):
        pass


    ####################
    # SCRIPT UTILITIES #
    ####################

    def scriptEngine(self):

        while(1):
            next_state = self.script_state
            interrupt = self.processScriptInterrupt()

            # IDLE #
            if self.script_state == 'idle':
                if interrupt == 'start-pause':
                    if self.script:
                        next_state = 'running'
            
            # PAUSED #
            if self.script_state == 'paused':
                if interrupt == 'start-pause':
                    self.script_time_step_next = time.time() + self.script_time_step_remaining
                    next_state = 'running'

                if interrupt == 'skip':
                    self.scriptAdvance()
                    if self.script != []:
                        next_state = 'paused'
                    else:
                        next_state = 'idle'

                if interrupt == 'stop':
                    self.scriptResetTimers()
                    next_state = 'idle'

            # RUNNING #
            if self.script_state == 'running':
                if interrupt == 'stop':
                    self.scriptResetTimers()
                    next_state = 'idle'

                elif interrupt == 'start-pause':
                    self.script_time_step_remaining = self.script_time_step_next - time.time()
                    next_state = 'paused'

                elif interrupt == 'skip':
                    self.scriptAdvance()
                    next_state = 'running'

                else:
                    if not self.script_time_step_next:
                        self.scriptExecute()

                    if self.script_time_step_next < time.time():
                        self.scriptAdvance()

                    if self.script != []:
                        next_state = 'running'
                    else:
                        next_state = 'idle'

            self.script_state = next_state


        """     if self.script_interrupt:
                    self.processScriptInterrupt()
                if self.script_wait:
                    t_now = time.time()
                    if t_now < self.script_next_time:
                        # int(t_now - self.script_next_time)
                        # time.strftime('%H:%M:%S', time.localtime(self.script_next_time))
                        pass
                    else:
                        self.script_wait = False
                        self.script.pop(0)
                        self.scriptExecute(self.script[0])
                else:
                    self.scriptExecute(self.script[0])
                    if not self.script_wait:
                        self.script.pop(0)
                    
        """

    def scriptResetStepTimers(self):
        self.script_time_step_duration = 0
        self.script_time_step_next = 0
        self.script_time_step_remaining = 0

    def scriptResetTimers(self):
        self.script_time_expected = 0
        self.script_time_accumulated = 0
        self.scriptResetStepTimers()

    def scriptAdvance(self):
        step = self.script.pop(0)
        if step[0] == 'wait':
            self.scriptResetStepTimers()
            self.script_time_accumulated += step[1]


    def scriptExecute(self, cmd):
        if cmd[0] == 'open':
            self.openValve(cmd[1])
            self.script_wait = False
        elif cmd[0] == 'closed':
            self.closeValve(cmd[1])
            self.script_wait = False
        elif cmd[0] =='wait':
            self.script_step_duration = cmd[1]
            self.script_time_step_next = time.time() + self.script_step_duration

    def startScriptEngine(self):
        pass

    def stopScriptEngine(self):
        pass

    def pauseScriptEngine(self):
        pass

    def processScriptInterrupt(self):
        pass

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
                        if op[0] not in self.script_operations:  # Identify operation
                            raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `{op[0]}` not in recognized list: {self.script_operations}.')

                        if (op[0] == 'open') or (op[0] == 'close'):
                            if len(op) < 2:  # Identify missing argument
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `{op[0]} requires a valve.')
                            valve = op[1]
                            if valve not in self.ctrl_model['config']['valves']:  # Identify typos
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Valve `{valve}` in operation `{op}` not recognized.')
                            new_line = [op,valve]

                        if op[0] =='wait':
                            if len(op) < 3:  # Identify missing argument
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `wait` requires a duration and unit of time.')
                            if not op[1].isdigit():  # Check if wait duration is an integer
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `wait` duration length is not an integer - {op[1]}')
                            if op[2] not in self.script_time_units:  # Check if wait unit is recognized
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `wait` duration unit must be one of the following - {self.script_time_units}')                    
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
                            if op[2] not in self.script_time_units:  # check if frequency unit is recognized
                                raise SyntaxError(f'Script formatting error. Line {line_number} : Operation `pump` unit must be one of the following - {self.script_time_units}')
                            new_line = [op[0], op[1]]

                if new_line:
                    new_script.append(new_line)

        except Exception as e:
            raise e

        return new_script, approx_time

    