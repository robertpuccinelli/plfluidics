"""
Purpose:

Create an application that listens for commands on a specified port. Commands are used to operate a microfluidic controller or provide status information.
"""

from flask import Flask
from plfluidics.server.controller import MicrofluidicController 

ctrl = MicrofluidicController()

app_server = Flask(__name__)
app_server.static_folder = ctrl.templatesDir()
app_server.template_folder = ctrl.templatesDir()

app_server.add_url_rule('/', view_func=ctrl.renderPage, methods=['GET'])

# Config page methods
app_server.add_url_rule('/readConfig', view_func=ctrl.readConfig, methods=['GET'])
app_server.add_url_rule('/saveConfig', view_func=ctrl.saveConfig, methods=['POST'])
app_server.add_url_rule('/setConfig', view_func=ctrl.setPreviewConfig, methods=['POST'])

# Control page methods
app_server.add_url_rule('/toggle', view_func=ctrl.toggleValve, methods=['POST'])
app_server.add_url_rule('/openValve', view_func=ctrl.openValve, methods=['POST'])
app_server.add_url_rule('/openAll', view_func=ctrl.openAll, methods=['POST'])
app_server.add_url_rule('/closeValve', view_func=ctrl.closeValve, methods=['POST'])
app_server.add_url_rule('/closeAll', view_func=ctrl.closeAll, methods=['POST'])
app_server.add_url_rule('/reset', view_func=ctrl.reset,methods=['POST'])

if __name__ == '__main__':
    app_server.run(host='0.0.0.0', port=5454)