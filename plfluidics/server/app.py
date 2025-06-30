"""
Purpose:

Create an application that listens for commands on a specified port. Commands are used to operate a microfluidic controller or provide status information.
"""

from flask import Flask
from flask_socketio import SocketIO
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from plfluidics.server.controller import MicrofluidicController

cdir = os.getcwd()
ndir = os.path.join(cdir, "logs")
os.makedirs(ndir, exist_ok=True)
filename = "MicrofluidicApp"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s [%(name)s]', '%H:%M:%S')
log_loc = cdir + '/logs/'
handler_file = TimedRotatingFileHandler(filename=log_loc + filename + '.log', when='midnight', interval=1, backupCount=14)
handler_file.setLevel(logging.INFO)
handler_file.setFormatter(log_format)
logger.addHandler(handler_file)

app_server = Flask(__name__)
socketio = SocketIO(app_server, cors_allowed_origins="*")
ctrl = MicrofluidicController(app_server, socketio)
ctrl.logger.info(f'Log file location: {log_loc}')

app_server.static_folder = ctrl.templatesDir()
app_server.template_folder = ctrl.templatesDir()

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
socketio.on_event('play-pause',ctrl.scriptToggle)
socketio.on_event('skip', ctrl.scriptSkip)
app_server.add_url_rule('/stopScript', view_func=ctrl.scriptStop, methods=['POST'])
# Valves
socketio.on_event('toggleValve', ctrl.valveToggle)
socketio.on_event('openValves',ctrl.valveOpenList)
socketio.on_event('closeValves', ctrl.valveCloseList)


if __name__ == '__main__':
    socketio.run(host='0.0.0.0', port=5454, debug=False)