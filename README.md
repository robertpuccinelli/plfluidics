# plfluidics

## Overview
**plfluidics** is a Python module focused on microfluidic applications. It provides both drivers for interfacing with solenoid valves and a model-view-controller (MVC) framework for operation. The interface is served on a browser-accessible port with Flask so that the microfluidic controller can be accessed both locally and remotely. While not a feature of the module, it is recommended to run [Tailscale](tailscale.com) if the module is installed on an embedded server and remote access is desired - this will greatly improve ease of access across networks.


## Installation and Use
### Installation
It is recommended to install this module in a virtual environment so that version control can be better maintained and conflicts with system libraries can be avoided. The following command will create a virtual environment in the current directory:<br>
`python3 -m venv 'venv_plfluidics'`

You will now have a directory named `venv_plfluidics`, which is where the virtual environment lives. The virtual environment can be activated as described in the [Python docs](https://docs.python.org/3/library/venv.html#how-venvs-work).

Once the virtual environment is activated, the module can be installed via pip:<br>
`pip install git+https://github.com/robertpuccinelli/plfluidics.git`

### Serving the application
When serving Flask applications, it is recommended to use web server gateway interfaces (WSGI) for robust operation in production environments. There are (3) primary considerations for selecting a WSGI in this use case. 1. The application depends on asynchronous web sockets for communication with the interface, so multithreaded and async support is required. 2. Support for a variety of operation system software is required because end users may use personal laptops or embedded servers. 3. There is no need to support a high number of concurrent users since the application controls scientific instrumentation. Eventlet appeared to best address these constraints while also having the added benefit of not requiring additional command line arguments. It was installed directly into the application to simplify deployment for end users.

Once the module is installed, the application can be served by executing a python script like the example below:<br>
```python
from plfluidics.server.app import appRun
appRun()
```

Once executed, the application can be accessed on a browser at port 5454 of the localhost ([127.0.0.1:5454](127.0.0.1:5454)) or the remote IP address. For embedded servers, it may be helpful to convert this task into a systemd service or something similar to facilitate automation. If a different port or configuration is desired, review how the application is launched in appRun() and create a custom script.