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
        self.valve_model = ModelValves()
        self.config_model = ModelConfig(options=self.valve_model.optionsGet())
        self.script_model = ModelScript(self.userQ, self.scriptQ, valve_list=None)

    ################
    # PAGE SERVICE #
    ################

    def renderPage(self):
        if self.valve_model.data['server']['status'] == 'no_config':
            self.config_model.file_list = self.loadFileList('configs')
            return self.configPage()
        else:
            self.script_model.file_list = self.loadFileList('scripts')
            return self.controlPage()

    def configPage(self):
        return render_template('config.html', 
                               model=self.config_model, 
                               error = self.error)

    def controlPage(self):
        page_name = self.valve_model.data['config']['device'] + '.html'
        running = True if self.script_model.state == 'running' else False
        valves = self.valve_model.data['server']['valve_states']
        
        return render_template(page_name, 
                               valves = valves,
                               script_files = self.script_model.file_list,
                               script_selected = self.script_model.selected,
                               script_running = running, 
                               script = self.script_model.preview_text,
                               error = self.error)
    
    def index(self):
        server_status = self.valve_model.data['server']['status']
        config_name = self.valve_model.data['config']['config_name']
        driver = self.valve_model.data['config']['driver']
        device_name = self.valve_model.data['config']['device']
        valve_states = self.valve_model.data['server']['valve_states']
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
        self.error = None
        try:
            file_name = request.form.get('item_selected')
            self.config_model.preview_text = self.configRead(file_name)
            self.config_model.selected = file_name
        except Exception as e:
            self.error = f'Error opening {file_name} : {e}'
        return self.renderPage()
 
    def configSave(self):
        self.error = None
        try:
            data=request.form.get('preview_content').replace('\r\n', '\n')
            self.config_model.preview_text=data
            config = self.config_model.processConfig(self.config_model.preview_text)
            file_name = config['config_name']
            file_path = importlib.resources.files('plfluidics.server.configs').joinpath(file_name + '.config')
            with open(file_path, 'w') as f:
                json.dump(config,f, indent=4)
        except Exception as e:
            self.error = f'Error saving config. {e}'
        return self.renderPage()

    def configLoad(self):
        self.error = None
        try: 
            if self.config_model.selected:
                data=self.config_model.preview_text.replace('\r\n', '\n')
            else:
                if not self.config_model.file_name:
                    self.config_model.file_name = request.form.get('item_selected')  
                data = self.configRead(self.config_model.file_name)
            config = self.config_model.processConfig(data)
            linear_config = self.config_model.configLinearize(config)
            self.valve_model.configSet(linear_config)
            self.valve_model.driverSet()
            self.script_model.valve_list = list(self.valve_model.data['server']['valve_states'].keys())
        except Exception as e:
            self.valve_model.data['server']['status'] = 'no_config'
            self.error = f'Error loading config. {e}'
        return self.renderPage()

    def configChange(self):
        self.__init__()
        return self.renderPage()

    def configReload(self):
        self.valve_model.reset()
        self.configLoad()
        return self.renderPage()

    ##############
    #  UTILITIES #
    ##############

    def configRead(self, file_name):
            file_path = importlib.resources.files('plfluidics.server.configs').joinpath(file_name)
            with open(file_path, 'r') as f:
                file_content = f.read()
            return file_content
    
    def scriptRead(self, file_name):
            file_path = importlib.resources.files('plfluidics.server.scripts').joinpath(file_name)
            with open(file_path, 'r') as f:
                file_content = f.read()
            return file_content

    def loadFileList(self, dir):
        try:
            file_list = list(importlib.resources.contents('plfluidics.server.' + dir))
            if file_list == []:
                raise ValueError(f"No config files found in: {importlib.resources.files('plfluidics.server.' + dir)}")
        except Exception as e:
            self.error = e
        return file_list


    #########
    # VALVE #
    #########

    def valveToggle(self, valve):
        self.error = None
        try:
            valve=request.form.get('valve')
            if self.checkValveExists(valve):
                curr_state = self.valve_model.data['server']['valve_states'][valve]
                if curr_state == 'open':
                    self.valve_model.closeValve(valve)
                elif curr_state == 'closed':
                    self.valve_model.openValve(valve)
        except Exception as e:
            self.error = f'Failed to toggle valve. {e}'
        return redirect(url_for('index'))
    
    def valveOpenList(self):
        self.error = None
        try:
            data=request.form.get('valve')
            valves_list = data.split(',')
            for valve in valves_list:
                self.valve_model.openValve(valve)
        except Exception as e:
            self.error = f'Failed to open list of valves. {e}'
        return redirect(url_for('index'))

    def valveCloseList(self):
        self.error = None
        try:
            data=request.form.get('valve')
            valves_list = data.split(',')
            for valve in valves_list:
                self.valve_model.closeValve(valve)
        except Exception as e:
            self.error = f'Failed to close list of valves. {e}'
        return redirect(url_for('index'))

    ###################
    # VALVE UTILITIES #
    ###################

    def openValve(self, valve):
        if self.checkValveExists(valve):
            self.valve_model.openValve(valve)
        return redirect(url_for('index'))

    def closeValve(self, valve):
        if self.checkValveExists(valve):
            self.valve_model.closeValve(valve)
        return redirect(url_for('index'))

    def checkValveExists(self, valve):
        if valve in self.valve_model.data['server']['valve_states']:
            return True
        else:
            raise ValueError(f'Valve not present in model: {valve}')

    ##########
    # SCRIPT #
    ##########

    def scriptLoad(self):
        self.error = None
        try:
            file_name = request.form.get('script')
            self.script_model.preview_text = self.scriptRead(file_name).replace('\r\n', '\n')
            self.script_model.selected = file_name
        except Exception as e:
            self.error = f'Error opening {file_name} : {e}'
        return self.renderPage()

    def scriptSave(self):
        self.error = None
        try:
            file_name = request.form.get('file_name')
            data = request.form.get('panel_text').replace('\r\n', '\n')
            self.script_model.preview_text=data
            self.script_model.script = self.script_model.processScript(data)
            file_path = importlib.resources.files('plfluidics.server.scripts').joinpath(file_name)
            with open(file_path, 'w') as f:
                f.write(self.script_model.preview_text)
        except Exception as e:
            self.error = f'Error saving script. {e}'
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
