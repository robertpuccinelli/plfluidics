'''Controller in model-view-controller framework for microfluidic hardware control application.
'''
import json
import importlib.resources
import queue
import threading
from logging import Logger
from flask import request, render_template, redirect, url_for
from plfluidics.server.models import ModelValves, ModelConfig, ModelScript


class MicrofluidicController():

    def __init__(self):
        self.userQ = queue.Queue()
        self.scriptQ = queue.Queue()
        self.error = None
        self.config_model = ModelConfig()
        self.ctrl_model = ModelValves()
        self.script_model = ModelScript(self.userQ, self.scriptQ)

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
    
    def loadFileList(self, dir):
        error = None
        try:
            file_list = list(importlib.resources.contents('plfluidics.server.' + dir))
            if file_list == []:
                raise ValueError(f"No config files found in: {importlib.resources.files('plfluidics.server.' + dir)}")
        except Exception as e:
            error = e
        return file_list, error


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

    def startScriptEngine(self):
        if self.script_model.state == 'idle':
            self.script_processor = threading.Thread(self.scriptProcessor)
            self.script_state_machine = threading.Thread(self.script_model.engine)
            self.script_processor.start()
            self.script_state_machine.start()

        elif self.script_model.state == 'running':
            self.userQ.put('start-pause')

        elif self.script_model.state == 'paused':
            self.userQ.put('start-pause')

    def skipScriptEngine(self):
        if self.script_model.state != 'idle':
            self.userQ.put('skip')

    def stopScriptEngine(self):
        if self.script_model.state != 'idle':
            self.userQ.put('stop')
            self.userQ.put(None)
            self.script_state_machine.join()
            self.script_processor.join()

    #########################
    # CTRL SCRIPT PROCESSOR #
    #########################

    def scriptProcessor(self):

        while(self.script_model.state != "idle"):
            # Process user input
            

            # Process script output
            try:
                msg = self.scriptQ.get_nowait()
                if msg[0] == 'open':
                    self.openValve(msg[1])
                elif msg[0] == 'close':
                    self.closeValve(msg[1])
                elif msg[0] == 'pause':
                    pass
                elif msg[0] is None:
                    # Terminate loop
                    break

            except queue.empty as e:
                pass
