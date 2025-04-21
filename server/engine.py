"""
Purpose:

Create an application that listens for commands on a specified port. Commands are used to operate a microfluidic controller or provide status information.
"""

from flask import Flask
from controller import configGet, configSet, control, optionsGet, statusGet


app_server = Flask(__name__)
app_server.add_url_rule('/state', view_func=statusGet, methods=['GET'])
app_server.add_url_rule('/config', view_func=configGet, methods=['GET'])
app_server.add_url_rule('/options', view_func=optionsGet, methods=['GET'])
app_server.add_url_rule('/config', view_func=configSet, methods=['PUT'])
app_server.add_url_rule('/control', view_func=control, methods=['POST'])

if __name__ == '__main__':
    app_server.run(host='0.0.0.0', port=5454)