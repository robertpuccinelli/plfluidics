'''Controller in model-view-controller framework for microfluidic hardware control application.

Controller
- Accepts inputs
- Processes inputs
- Calls methods to update model
- Returns link for new (or updated) page
'''
from logging import Logger
from flask import request, jsonify
from model import ModelMicrofluidicController


class Controller():

    def __init__(self):
        self.model = ModelMicrofluidicController()

    def configInitialize(self, data):
        try:
            config = processConfig(data)
            self.model.configSet(config)
        except Exception as e:
            Logger.warning(f'Failed to set config: {e}')

status = {'state':'idle'}
valves = {'device':'none'}
config = {'config_name':'none','driver':'none','device':'none','valves':'none'}
config_fields = ['config_name', 'device','driver','valves']
drivers = ['rgs', 'none']
control_fields = ['valve','state']
valve_fields = ['valve_alias','solenoid_number', 'default_state_closed','inv_polarity']
controller = None

def statusGet():
    return jsonify({'status': 'success', 'message':'Server state retrieved', 'data':status}), 200

def configGet():
    return jsonify({'status': 'success', 'message':'Configuration retrieved', 'data':config}), 200

def optionsGet():
    return jsonify({'config_field': config_fields, 'drivers': drivers, 'valve_controls':control_fields, 'valve_fields':valve_fields}), 200

def configSet():
    try:
        command = processRequest()
        config, controller = processConfig(command)
        return ret200msg('Configuration set and driver loaded.')

    except Exception as e:
        return e.args
    
def control():
    try:
        if config['Name'] != 'none':
            command = processRequest()
            action, method, valve = processControl(command)
            method(valve)
            return ret200msg(f'Action successful : {action} - {valve}')
        else:
            return ret400msg('Server configuration not set.')

    except Exception as e:
        return e.args
    

    
#############
# UTILITIES #
#############

def ret200msg(msg):
    '''Return code 200 with message'''
    return jsonify({'status': 'success', 'message':msg}), 200

def ret400msg(msg):
    '''Return code 400 with message'''
    return jsonify({'status': 'error', 'message': msg}), 400

def processRequest():
    '''Validate request as JSON'''
    if request.is_json():
        try:
            command = request.get_json()
            return command

        except ValueError:
            raise ValueError(ret400msg('Invalid JSON format'))
    else:
        raise ValueError(ret400msg('Request must be JSON'))

def processConfig(command):
    '''Validate configuration format and extract data'''
    key_set = set(config)
    config_set = set(command)
    if not key_set.difference(config_set):
        raise KeyError(ret400msg(f'Key missing in config: {key_set.difference(config_set)}'))
    
    if not config_set.difference(key_set):
        raise KeyError(ret400msg(f'Extra keys found in config: {config_set.difference(key_set)}'))
    
    new_config = {}
    new_config['name'] = command['config_name'].lower()
    new_config['device'] = command['device'].lower()
    new_config['driver'] = command['driver'].lower()
    valves = command['valves']

    if new_config['driver'] is 'rgs':
        valve_list = []
        try:
            for valve in valves:
                v_name = valve['valve_alias'].lower()
                v_num = valve['solenoid_number']
                pol = valve.setdefault('inv_polarity', False)
                ds = valve.setdefault('default_state_closed', False) 
                valve_list.append([v_num,pol,ds,v_name])

            new_controller = ValveControllerRGS(valve_list)
            return new_config, new_controller

        except Exception as e:
            raise ValueError(ret400msg('Failed to load RGS valve controller. Check formatting of valve configuration data.'))
        
    elif new_config['driver'] is 'none':
        new_config = {'config_name':'none','driver':'none','device':'none','valves':'none'}
        new_controller = None
        return new_config, new_controller

    else:
        raise ValueError(ret400msg(f'Driver not recognized: {new_config['driver']}'))

def processControl(command):
    '''Validate control format and extract data'''
    key_set = set(control_fields)
    control_set = set(command)
    if not key_set.difference(control_set):
        raise KeyError(ret400msg(f'Key missing in control command: {key_set.difference(control_set)}'))
    
    valve = command['valve'].lower()
    state = command['state'].lower()

    if valve not in controller.valve_dict:
        raise ValueError(ret400msg(f'Valve not recognized: {valve}'))

    if state is 'open':
        action = 'open'
        method = controller.setValveOpen
    elif state is 'close':
        action = 'close'
        method = controller.setValveClose
    else:
        raise ValueError(ret400msg(f'Action not recognized: {state}'))
    
    return action, method, valve