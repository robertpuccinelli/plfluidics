"""
Purpose:

Create an application that listens for commands on a specified port. Commands are used to operate a microfluidic controller or provide status information.
"""
#import eventlet
#eventlet.monkey_patch()
from flask import Flask
from flask_socketio import SocketIO
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import importlib.resources
from plfluidic.server.controller import MicrofluidicController


socketio = SocketIO()

def createApp():
    cdir = os.getcwd()
    configs_dir = os.path.join(cdir, "plfluidic_user", "configs")
    scripts_dir = os.path.join(cdir, "plfluidic_user", "scripts")
    templates_dir = os.path.join(cdir, "plfluidic_user", "templates")
    logs_dir = os.path.join(cdir, "plfluidic_user", "logs")

    # Copy package configuration files to system working directory if not present
    if not os.path.exists(configs_dir):
        os.makedirs(configs_dir)
        package_configs = importlib.resources.files("plfluidic.server.configs")
        for item in package_configs.iterdir():
            if item.is_file():
                file_name = item.name
                destination_path = os.path.join(configs_dir, file_name)
                file_content = item.read_bytes()
                with open(destination_path, "wb") as f:
                    f.write(file_content)

    # Copy package script files to system working directory if not present
    if not os.path.exists(scripts_dir):
        os.makedirs(scripts_dir)
        package_configs = importlib.resources.files("plfluidic.server.scripts")
        for item in package_configs.iterdir():
            if item.is_file():
                file_name = item.name
                destination_path = os.path.join(scripts_dir, file_name)
                file_content = item.read_bytes()
                with open(destination_path, "wb") as f:
                    f.write(file_content)

    # Copy package template files to system working directory if not present
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        package_configs = importlib.resources.files("plfluidic.server.templates")
        for item in package_configs.iterdir():
            if item.is_file():
                file_name = item.name
                destination_path = os.path.join(templates_dir, file_name)
                file_content = item.read_bytes()
                with open(destination_path, "wb") as f:
                    f.write(file_content)

    os.makedirs(logs_dir, exist_ok=True)
    filename = "plfluidic"

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s [%(name)s]', '%H:%M:%S')
    log_loc = cdir + os.sep + 'logs' + os.sep
    handler_file = TimedRotatingFileHandler(filename=log_loc + filename + '.log', when='midnight', interval=1, backupCount=28)
    handler_file.setLevel(logging.DEBUG)
    handler_file.setFormatter(log_format)
    logger.addHandler(handler_file)

    app_server = Flask(__name__,template_folder=templates_dir, static_folder=templates_dir)
    #socketio.init_app(app_server, cors_allowed_origins="*", async_mode='eventlet')
    socketio.init_app(app_server, cors_allowed_origins="*", async_mode='threading')
    ctrl = MicrofluidicController(app_server, socketio, log_file_handler=handler_file)
    ctrl.logger.info(f'Log file location: {log_loc}')

    app_server.add_url_rule('/', view_func=ctrl.renderPage, methods=['GET'])

    # CONFIG PAGE
    app_server.add_url_rule('/configPreview', view_func=ctrl.configPreview, methods=['POST'])
    app_server.add_url_rule('/configSave', view_func=ctrl.configSave, methods=['POST'])
    app_server.add_url_rule('/configLoad', view_func=ctrl.configLoad, methods=['POST'])


    # CONTROL PAGE
    # Config
    app_server.add_url_rule('/changeConfig', view_func=ctrl.configChange, methods=['POST'])
    app_server.add_url_rule('/reloadConfig', view_func=ctrl.configReload, methods=['POST'])
    # Script
    app_server.add_url_rule('/loadScript', view_func=ctrl.scriptLoad, methods=['POST'])
    app_server.add_url_rule('/saveScript', view_func=ctrl.scriptSave, methods=['POST'])
    # Media
    socketio.on_event('poll', ctrl.poll)
    socketio.on_event('play-pause',ctrl.scriptToggle)
    socketio.on_event('skip', ctrl.scriptSkip)
    app_server.add_url_rule('/stopScript', view_func=ctrl.scriptStop, methods=['POST'])
    # Valves
    socketio.on_event('toggleValve', ctrl.valveToggle)
    socketio.on_event('openValves',ctrl.valveOpenList)
    socketio.on_event('closeValves', ctrl.valveCloseList)
    # Pump

    return app_server

def appRun():
    app = createApp()
    socketio.run(app, host='0.0.0.0', port='5455', debug=False, use_reloader=False)

if __name__ == '__main__':
    appRun()
