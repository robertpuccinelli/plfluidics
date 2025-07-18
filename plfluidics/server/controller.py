'''Controller in model-view-controller framework for microfluidic hardware control application.
'''
import json
import importlib.resources
import queue
import threading
import logging
import io
from time import sleep
from flask import request, render_template

from plfluidics.server.models import ModelHardware, ModelConfig, ModelScript


class MicrofluidicController():

    def __init__(self, flask_app, socketio_instance, log_level=logging.INFO):
        self.app = flask_app
        self.socketio = socketio_instance
        self.log_level = log_level

        self.userQ = queue.Queue()
        self.scriptQ = queue.Queue()
        self.logQ = queue.Queue()

        log_format = logging.Formatter('%(asctime)s - %(message)s', '%H:%M:%S')
        self.logger = logging.getLogger('controller')
        self.logger.setLevel(self.log_level)

        self.log_queue = QueueLogHandler(self.logQ)
        self.log_queue.setLevel(self.log_level)
        self.log_queue.setFormatter(log_format)

        self.log_var = io.StringIO()
        log_var_handler = logging.StreamHandler(self.log_var)
        log_var_handler.setFormatter(log_format)
        log_var_handler.setLevel(self.log_level)

        self.logger.addHandler(self.log_queue)
        self.logger.addHandler(log_var_handler)

        self.reset()

    def reset(self):
        self.userQ.queue.clear()
        self.scriptQ.queue.clear()
        self.logQ.queue.clear()

        self.thread_logger = None
        self.thread_script_processor = None
        self.thread_script_state_machine = None
        self.flag_thread_logger = False
        self.flag_thread_processor = False

        self.error = None
        self.valve_model = None
        self.config_model = None
        self.script_model = None

        self.valve_model = ModelHardware(logger_name='controller.valves')
        self.config_model = ModelConfig(options=self.valve_model.optionsGet(), logger_name='controller.config')
        self.script_model = ModelScript(self.userQ, self.scriptQ, valve_list=None, logger_name='controller.script')

        self.logger.debug('MicrofluidicController initialized.')

    def templatesDir(self):
        return f'{importlib.resources.files('plfluidics.server.templates').joinpath('config.html').parent}'

    ############
    # LOGGGING #
    ############

    def logEmitter(self):
        with self.app.app_context():
            while True:
                try:
                    msg = self.logQ.get(timeout=0.01)
                    self.socketio.emit('log_msg', {'msg': msg})
                except queue.Empty:
                    sleep(0.04)

    ################
    # PAGE SERVICE #
    ################

    def renderPage(self):
        if self.valve_model.data['server']['status'] == 'no_config':
            self.logger.debug('Rendering configuration page.')
            self.config_model.file_list = self.loadFileList('configs')
            return self.configPage()
        else:
            self.logger.debug('Rendering control page.')
            self.script_model.file_list = self.loadFileList('scripts')
            return self.controlPage()

    def configPage(self):
        if self.error:
            self.logger.warning(f'{self.error}')
        return render_template('config.html', 
                               model=self.config_model, 
                               error = self.error)

    def controlPage(self):
        if self.error:
            self.logger.warning(f'{self.error}')
        if not self.flag_thread_logger:
            self.thread_logger = threading.Thread(target=self.logEmitter)
            self.thread_logger.daemon = True
            self.thread_logger.start()      
            self.flag_thread_logger = True
        page_name = self.valve_model.data['config']['device'] + '.html'
        valves = self.valve_model.data['server']['valve_states']
        self.logger.debug(f'Control page: {page_name}')
        return render_template(page_name, 
                               valves = valves,
                               script_files = self.script_model.file_list,
                               script_selected = self.script_model.selected,
                               script_state = self.script_model.state,
                               script_processed = True if self.script_model.script else False,
                               script = self.script_model.preview_text,
                               log = self.log_var.getvalue())

    ##########
    # CONFIG #
    ##########

    def configPreview(self):
        self.logger.debug('Previewing configuration.')
        self.error = None
        try:
            file_name = request.form.get('item_selected')
            self.config_model.preview_text = self.configRead(file_name)
            self.config_model.selected = file_name
            self.logger.info(f'Configuration previewed: {file_name}')
        except Exception as e:
            self.error = f'Error opening {file_name} : {e}'
        return self.renderPage()
 
    def configSave(self):
        self.logger.debug('Saving configuration.')
        self.error = None
        try:
            data=request.form.get('preview_content').replace('\r\n', '\n')
            self.config_model.preview_text=data
            config = self.config_model.processConfig(self.config_model.preview_text)
            file_name = config['config_name']
            file_path = importlib.resources.files('plfluidics.server.configs').joinpath(file_name + '.config')
            with open(file_path, 'w') as f:
                json.dump(config,f, indent=4)
            self.logger.info(f'Configuration saved: {file_path}')
        except Exception as e:
            self.error = f'Error saving config. {e}'
        return self.renderPage()

    def configLoad(self):
        self.logger.debug('Loading configuration.')
        self.error = None
        try: 
            if self.config_model.selected:
                data=self.config_model.preview_text.replace('\r\n', '\n')
                self.logger.info('Loading configuration from preview panel.')
            else:
                if not self.config_model.file_name:
                    self.config_model.file_name = request.form.get('item_selected')  
                data = self.configRead(self.config_model.file_name)
                self.logger.info(f'Loading configuration from file: {self.config_model.file_name}')
            config = self.config_model.processConfig(data)
            linear_config = self.config_model.configLinearize(config)
            self.valve_model.configSet(linear_config)
            self.valve_model.driverSet()
            self.script_model.valve_list = list(self.valve_model.data['server']['valve_states'].keys())
            self.logger.info('Configuration loaded successfully.')
        except Exception as e:
            self.valve_model.data['server']['status'] = 'no_config'
            self.error = f'Error loading config. {e}'
        return self.renderPage()

    def configChange(self):
        self.logger.info('Returning to configuration selection.')
        self.reset()
        return self.renderPage()

    def configReload(self):
        self.logger.info('Reloading configuration.')
        self.valve_model.reset()
        self.configLoad()
        return self.renderPage()

    ##############
    #  UTILITIES #
    ##############

    def configRead(self, file_name):
            file_path = importlib.resources.files('plfluidics.server.configs').joinpath(file_name)
            self.logger.debug(f'Reading configuration: {file_path}')
            with open(file_path, 'r') as f:
                file_content = f.read()
            return file_content

    def scriptRead(self, file_name):
            file_path = importlib.resources.files('plfluidics.server.scripts').joinpath(file_name)
            self.logger.debug(f'Reading script: {file_path}')
            with open(file_path, 'r') as f:
                file_content = f.read()
            return file_content

    def loadFileList(self, dir):
        self.logger.debug(f'Loading file list: {dir}')
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
    
    def valveToggle(self, data):
        self.logger.debug('Toggling valve.')
        self.error = None
        try:
            valve = data.get('valve')
            if self.checkValveExists(valve):
                curr_state = self.valve_model.data['server']['valve_states'][valve]
            if curr_state == 'open':
                self.closeValve(valve)
            elif curr_state == 'closed':
                self.openValve(valve)
        except Exception as e:
            self.logger.warning(f'Failed to toggle valve. {e}')
    
    def valveOpenList(self, data):
        self.logger.debug('Opening list of valves.')
        self.error = None
        try:
            valves = data.get('valves')
            for valve in valves:
                if self.checkValveExists(valve):
                    self.openValve(valve)
        except Exception as e:
            self.error = f'Failed to open list of valves. {e}'

    def valveCloseList(self,data):
        self.logger.debug('Closing list of valves.')
        self.error = None
        try:
            valves = data.get('valves')
            for valve in valves:
                if self.checkValveExists(valve):
                    self.closeValve(valve)
        except Exception as e:
            self.error = f'Failed to close list of valves. {e}'

    ###################
    # VALVE UTILITIES #
    ###################

    def openValve(self, valve):
        if self.valve_model.data['server']['valve_states'][valve] == 'closed':
            self.valve_model.openValve(valve)
            if self.valve_model.data['server']['valve_states'][valve] == 'open':
                self.socketio.emit('valve',{'action':'open','valve':valve})

    def closeValve(self, valve):
        if self.valve_model.data['server']['valve_states'][valve] == 'open':
            self.valve_model.closeValve(valve)
            if self.valve_model.data['server']['valve_states'][valve] == 'closed':
                self.socketio.emit('valve',{'action':'close','valve':valve})

    def checkValveExists(self, valve):
        self.logger.debug(f'Checking existence of valve: {valve}')
        if valve in self.valve_model.data['server']['valve_states']:
            return True
        else:
            raise ValueError(f'Valve not present in model: {valve}')

    ##########
    # SCRIPT #
    ##########

    def scriptLoad(self):
        self.logger.debug('Loading script.')
        self.error = None
        try:
            file_name = request.form.get('script')
            self.script_model.preview_text = self.scriptRead(file_name).replace('\r\n', '\n')
            self.script_model.selected = file_name
            self.logger.info(f'Loaded script: {file_name}')
        except Exception as e:
            self.error = f'Error opening {file_name} : {e}'
        return self.renderPage()

    def scriptSave(self):
        self.logger.debug('Saving script.')
        self.error = None
        try:
            file_name = request.form.get('file_name')
            if not file_name:
                raise ValueError('No file name.')
            data = request.form.get('panel_text').replace('\r\n', '\n')
            self.script_model.preview_text=data  # Preserve user text
            self.script_model.processScript(data)  # Generate error if data not formatted correctly
            file_path = importlib.resources.files('plfluidics.server.scripts').joinpath(file_name)
            with open(file_path, 'w') as f:
                f.write(self.script_model.preview_text)
            self.script_model.selected = file_name
            self.logger.info(f'Script saved: {file_path}')
        except Exception as e:
            self.error = f'Error saving script. {e}'
        return self.renderPage()

    def scriptToggle(self, data):
        if self.script_model.state == 'running':
            self.logger.info('User request: pause')
        else:
            self.logger.info('User request: play')
        try:
            if not self.script_model.script:  # On 1st press: extract, process, store user text
                text = data.get('panel_text').replace('\r\n', '\n')
                self.script_model.preview_text=text
                self.script_model.script = self.script_model.processScript(text)
            self.startPauseScriptEngine()
        except Exception as e:
            self.logger.warning = f'Error starting/pausing script. {e}'

    def scriptSkip(self):
        self.logger.info('User request: skip')
        self.skipScriptEngine()
        return self.renderPage()

    def scriptStop(self):
        self.logger.info('User request: stop')
        self.stopScriptEngine()
        return self.renderPage()

    ####################
    # SCRIPT UTILITIES #
    ####################

    def startPauseScriptEngine(self):
        """Enable or disable the autoplay function of scripts.
        
        If script state machine is idle, launch threads for the state machine
        and controller processor. Processor converts messages to valve operations.

        If script state machine is running, disable autoplay to allow user interaction.

        If script state machine is paused, enable script autoplay.
        """
        if self.script_model.state == 'idle':
            # Check to see if threads for script management are running
            if not self.flag_thread_processor:
                self.logger.debug('Starting thread for interfacing with script engine.')
                self.userQ.queue.clear()
                self.thread_script_processor = threading.Thread(target=self.scriptProcessor)
                self.thread_script_processor.daemon = True
                self.thread_script_processor.start()

            if not self.script_model.flag_thread_engine:
                self.logger.debug('Starting thread for script engine.')
                self.scriptQ.queue.clear()
                self.thread_script_state_machine = threading.Thread(target=self.script_model.engine)
                self.thread_script_state_machine.daemon = True
                self.thread_script_state_machine.start()

        if self.script_model.state == 'running':
            self.socketio.emit('pause')
        else:
            self.socketio.emit('play')

        self.logger.debug('Submitting start-pause command.')
        self.userQ.put('start-pause')

    def skipScriptEngine(self):
        """While script is loaded, skip the next uncompleted step."""
        if self.script_model:
            self.logger.debug('Submitting skip command.')
            self.userQ.put('skip')

    def stopScriptEngine(self):
        """Manually terminate script state machine and processor threads"""
        if self.script_model.script:
            self.logger.debug('Submitting stop command.')
            self.userQ.put('stop')
            self.thread_script_state_machine.join()
            self.logger.debug('Script engine thread terminated.')
            self.thread_script_processor.join()
            self.logger.debug('Controller script interface terminated.')


    def poll(self):
        self.userQ.put('poll')

    #########################
    # CTRL SCRIPT PROCESSOR #
    #########################

    def scriptProcessor(self):
        """Processes signals generated from script state machine.

        Signals consist of valve operations or termination. The processor 
        thread is not active if the script state machine is in an idle state.
        """
        self.logger.debug('Script processor initializing.')
        self.flag_thread_processor = True
        while(True):
            try:
                msg = self.scriptQ.get_nowait()
                self.scriptQ.task_done()
                if msg is None:
                    # Terminate loop
                    break
                elif msg[0] == 'open':
                    self.openValve(msg[1])
                    self.socketio.emit('valve',{'name':msg[1], 'state':'o'})
                elif msg[0] == 'close':
                    self.closeValve(msg[1])
                    self.socketio.emit('valve',{'name':msg[1], 'state':'c'})
                elif msg[0] == 'pause':
                    self.socketio.emit('pause')
                elif msg[0] == 't_e':
                    self.socketio.emit('time',{'event':'t_e','value':msg[1]})
                elif msg[0] == 't_a':
                    self.socketio.emit('time',{'event':'t_a','remaining':msg[1], 'duration':msg[2]})
                elif msg[0] == 't_n':
                    self.socketio.emit('time',{'event':'t_n','value':msg[1]})
                elif msg[0] == 't_r':
                    self.socketio.emit('time',{'event':'t_r','remaining':msg[1], 'duration':msg[2]})
                elif msg[0] == 'line':
                    self.socketio.emit('line',{'index':msg[1]})

            except queue.Empty as e:
                sleep(.001)
        self.flag_thread_processor = False
        self.logger.debug('Script processor terminated.')
        self.socketio.emit('stop')

class QueueLogHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            self.log_queue.put(self.format(record).strip())
        except Exception:
            self.handleError(record)