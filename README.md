# plfluidics

## Overview
**plfluidics** is a Python module focused on microfluidic applications. It provides both drivers for interfacing with solenoid valves and a model-view-controller (MVC) framework for operation. The interface is served on a browser-accessible port with Flask and Waitress so that the microfluidic controller can be accessed both locally and remotely. While not a feature of the module, it is recommended to run [Tailscale](tailscale.com) if the module is installed on an embedded server and remote access is desired - this will greatly improve ease of access across networks.


## Installation and Use
### Serving with Waitress
When serving Flask applications, it is recommended to use web server gateway interfaces (WSGI) such as gunicorn to robust operation that can handle many concurrent users in production environments. Since the purpose of this module is to provide an interface for instrumentation, many concurrent users are not expected. Similarly, the hardware used to serve the microfluidic controller interface is not standardized and might run on an embedded Linux server or an individual's Windows or Mac laptop. The python Waitress module is used as a WSGI here because good performance with numerous connections is not needed while support for different platforms with minimal tinkering is critical.

Once installed, the application can be served with the following command:<br>
`waitress-serve --listen=0.0.0.0:5454 --call 'plfluidics.server.app:createApp'`

Once Waitress is running, the application can be accessed on port 5454 of the localhost or the remote IP address. For embedded servers, it may be helpful to convert this task into a systemd service or something similar to facilitate automation. 

### Installation
It is recommended to install this module in a virtual environment so that version control can be better maintained and conflicts with system libraries can be avoided. The following command will create a virtual environment in the current directory:<br>
`python3 -m venv 'venv_plfluidics'`

You will now have a directory named `venv_plfluidics`, which is where the virtual environment lives. The virtual environment can be activated as described in the [Python docs](https://docs.python.org/3/library/venv.html#how-venvs-work).

Once the virtual environment is activated, the module can be installed via pip:<br>
`pip install git+https://github.com/robertpuccinelli/plfluidics.git`