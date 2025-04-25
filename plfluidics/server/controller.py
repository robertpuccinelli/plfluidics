'''Controller in model-view-controller framework for microfluidic hardware control application.
'''
import os
import json
import importlib.resources
from logging import Logger
from flask import request, render_template, redirect, url_for
from plfluidics.server.model import ModelMicrofluidicController


class MicrofluidicController():

    def __init__(self):
        self.model = ModelMicrofluidicController()
        self.error = None

    def renderPage(self):
        if self.model.data['server']['status'] == 'no_config':
            return self.configPage()
        else:
            return self.controlPage()

    def configPage(self):
        print('Config page rendering')
        file_list = self.loadConfigList()
        msg = self.error
        return render_template('config.html', file_list=file_list, error_msg = msg)

    def controlPage(self):
        return render_template(url_for('index'))
    
    def index(self):
        server_status = self.model.data['server']['status']
        config_name = self.model.data['config']['config_name']
        driver = self.model.data['config']['driver']
        device_name = self.model.data['config']['device']
        valve_states = self.model.data['server']['valve_states']
        return render_template('index.html', 
                               status = server_status,
                               config_name = config_name,
                               driver = driver,
                               device_name = device_name,
                               valve_states=valve_states)
    
    def reset(self):
        self.model.reset()
        return redirect(url_for('index'))
    
    def toggleValve(self, valve):
        if self.checkValveExists(valve):
            curr_state = self.model.data['server']['valve_states'][valve]
            if curr_state == 'open':
                self.model.closeValve(valve)
            elif curr_state == 'closed':
                self.model.openValve(valve)
        return redirect(url_for('index'))
    
    def openValve(self, valve):
        if self.checkValveExists(valve):
            self.model.openValve(valve)
        return redirect(url_for('index'))
    
    def openAll(self):
        for valve in self.model['server']['valve_states']:
            self.model.openValve(valve)
        return redirect(url_for('index'))

    def closeValve(self, valve):
        if self.checkValveExists(valve):
            self.model.closeValve(valve)
        return redirect(url_for('index'))
    
    def closeAll(self):
        for valve in self.model['server']['valve_states']:
            self.model.closeValve(valve)
        return redirect(url_for('index'))


#############
# UTILITIES #
#############

    def readConfig(self):
        file_name = request.args.get('file_name')
        file_path = importlib.resources.files('plfluidics.server.configs').joinpath(file_name)
        with open(file_path, 'r') as f:
            file_content = f.read()
            return file_content

    def loadConfigList(self):
        return list(importlib.resources.contents('plfluidics.server.configs'))
    
    def setConfig(self):
        if request.is_json:
            data=request.get_json().get('text')
            config = self.processConfig(data)
            self.model.configSet = config
            self.model.setDriver()
        return self.renderPage()    

    def setFileConfig(self):
        if request.is_json:
            data=request.get_json().get('text')
            file_name = config['config_name']
            file_path = importlib.resources.files('plfluidics.server.configs').joinpath(file_name + '.config')
            with open(file_path, 'r') as f:
                data = f.read()
            config = self.processConfig(data)
            self.model.configSet = config
            self.model.setDriver()
        return self.renderPage()    

    def saveConfig(self):
        self.error = []
        if request.is_json:
            try:
                data=request.get_json().get('text')
                config = self.processConfig(data)
                file_name = config['config_name']
                file_path = importlib.resources.files('plfluidics.server.configs').joinpath(file_name + '.config')
                with open(file_path, 'w') as f:
                    f.write(json.dumps(config))
            except Exception as e:
                print(f'Error : {e}')
                self.error = 'Error caught'
            return self.renderPage()


    def templatesDir(self):
        return f'{importlib.resources.files('plfluidics.server.templates').joinpath('config.html').parent}'

    def configInitialize(self, data):
        try:
            data = request.get_json()
            config = self.processConfig(data)
            self.model.configSet(config)
        except Exception as e:
            Logger.warning(f'Failed to set config: {e}')

        return redirect(url_for('index'))

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
                raise ValueError(f'Entry not formatted properly. Key: {key}, Value: {value}')
        return new_dict
    
    def checkValveExists(self, valve):
        if valve in self.model.data['server']['valve_states']:
            return True
        
    def processConfig(self, data):
        '''Validate configuration format and extract data'''
        new_data = self.lowercaseDict(data)
        fields = self.model.optionsGet()
        config_fields = set(fields['config_fields'])
        config_set = set(new_data)
        if config_fields.difference(config_set):
            raise KeyError(f'Key missing in config: {config_fields.difference(config_set)}')
        
        if config_set.difference(config_fields):
            raise KeyError(f'Extra keys found in config: {config_set.difference(config_fields)}')

        if new_data['driver'] not in fields['driver_options']:
            raise ValueError(f'Driver not in recognized list: {fields['driver_options']}')
        
        # Linearize valve data from dict of dicts to list of dicts
        new_valves = new_data['valves']
        valve_fields = fields['valve_fields']
        valve_fields.remove('valve_alias')
        valve_data = []
        for valve in new_valves:
            try:
                temp_valve = {'valve_alias': valve}
                temp_valve = temp_valve | {key:new_valves[valve][key] for key in valve_fields}
            except Exception as e:
                raise KeyError(f'Field missing from valve configuration. {e}')
            valve_data.append(temp_valve)
        print('Valve list generated')
        new_data['valves'] = valve_data
        return new_data