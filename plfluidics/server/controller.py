'''Controller in model-view-controller framework for microfluidic hardware control application.
'''
import os
import json
import importlib.resources
from logging import Logger
from flask import request, render_template, redirect, url_for
from plfluidics.server.models import ModelMicrofluidicController, ModelConfig


class MicrofluidicController():

    def __init__(self):
        self.config_model = ModelConfig()
        self.ctrl_model = ModelMicrofluidicController()
        self.error = None

    ################
    # PAGE SERVICE #
    ################

    def renderPage(self):
        if self.ctrl_model.data['server']['status'] == 'no_config':
            self.config_model.file_list = self.loadConfigFileList()
            return self.configPage()
        else:
            return self.controlPage()

    def configPage(self):
        return render_template('config.html', model=self.config_model)

    def controlPage(self):
        return render_template(url_for('index'))
    
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
    
    def loadConfigFileList(self):
        try:
            file_list = list(importlib.resources.contents('plfluidics.server.configs'))
            if file_list == []:
                raise ValueError(f"No config files found in: {importlib.resources.files('plfluidics.server.configs')}")
        except Exception as e:
            self.config_model.error = e
        return file_list

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

    def scriptLoad(self):
        pass

    def scriptSave(self):
        pass

    def scriptToggle(self):
        pass

    def scriptSkip(self):
        pass

    def scriptStop(self):
        pass


    #############
    # UTILITIES #
    #############      

    def configInitialize(self, data):
        try:
            data = request.get_json()
            config = self.processConfig(data)
            self.ctrl_model.configSet(config)
        except Exception as e:
            Logger.warning(f'Failed to set config: {e}')

        return redirect(url_for('index'))
    