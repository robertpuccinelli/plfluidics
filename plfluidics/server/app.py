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
app_server.add_url_rule('/configPreview', view_func=ctrl.configPreview, methods=['POST'])
app_server.add_url_rule('/configSave', view_func=ctrl.configSave, methods=['POST'])
app_server.add_url_rule('/configLoad', view_func=ctrl.configLoad, methods=['POST'])

if __name__ == '__main__':
    app_server.run(host='0.0.0.0', port=5454, debug=True)