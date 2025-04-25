'''Model in model-view-controller framework for microfluidic hardware control application.

Model:
- Represents server state, hardware state
- Stores methods that are called by controller
- Updates state as dictated
- Returns to controller
'''
from plfluidics.valves.valve_controller import ValveControllerRGS


class ModelMicrofluidicController():

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
        self.data['server']['status'] = 'driver_not_set'
        
    def driverSet(self):
        config = self.configGet()
        if config['driver'] is 'rgs':
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

        elif config['driver'] is 'none':
            self.data['controller'] = []
            self.data['server']['valve_states']={}
    
    def openValve(self, valve):
        self.data['controller'].setValveOpen(valve)
        self.data['server']['valve_states'][valve] = 'open'

    def closeValve(self, valve):
        self.data['controller'].setValveClose(valve)
        self.data['server']['valve_states'][valve] = 'close'