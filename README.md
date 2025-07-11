# plfluidics

## Overview
**plfluidics** is a Python package focused on microfluidic applications. It provides both drivers for interfacing with solenoid valves and a model-view-controller (MVC) framework for operation. The interface is served on a browser-accessible port with Flask so that the microfluidic controller can be accessed both locally and remotely. While not a feature of the package, it is recommended to run [Tailscale](tailscale.com) if the software is installed on an embedded server and remote access is desired - this will greatly improve ease of access across networks.

## Software operation
The software is divided into two separate interfaces - one for configuration and another for control.

### Configuration interface
![Configuration interface](/assets/config_interface.png)
In the configuration interface, the operator selects a configuration file that will be used to initialize hardware and select a control interface. The file can be previewed within the interface or loaded directly. If the file is previewed, the file can also be edited. Edits do not need to be saved in order to be loaded, but they will not be preserved for future sessions. 

### Control interface
![Control interface](/assets/controller_interface.png)
The controller interface allows operators to interact with their device. Scripts can be selected, edited and saved as needed. While executing a script, the operator has the ability to pause/resume, skip steps, or terminate the process. If a script is not actively running, the user can manually control the device. Configurations and actions are recorded in a log that is both presented on the interface and stored in a separate file.

## Installation and use
### Installation
It is recommended to install this package in a virtual environment so that version control can be better maintained and conflicts with system libraries can be avoided. The following command will create a virtual environment in the current directory:<br>
`python3 -m venv 'venv_plfluidics'`

You will now have a directory named `venv_plfluidics`, which is where the virtual environment lives. The virtual environment can be activated as described in the [Python docs](https://docs.python.org/3/library/venv.html#how-venvs-work).

Once the virtual environment is activated, the package can be installed via pip:<br>
`pip install git+https://github.com/robertpuccinelli/plfluidics.git`

### Serving the application
When serving Flask applications, it is recommended to use web server gateway interfaces (WSGI) for robust operation in production environments. There are (3) primary considerations for selecting a WSGI in this use case. 1. The application depends on asynchronous web sockets for communication with the interface, so multithreaded and async support is required. 2. Support for a variety of operation system software is required because end users may use personal laptops or embedded servers. 3. There is no need to support a high number of concurrent users since the application controls scientific instrumentation. Eventlet appeared to best address these constraints while also having the added benefit of not requiring additional command line arguments. It is installed directly into the application to simplify deployment for end users.

Once the package is installed, the application can be served by executing a the following command in a terminal:<br>
`python -m plfluidics.app`

Once executed, the application can be accessed on a browser at port 5454 of the localhost ([127.0.0.1:5454](127.0.0.1:5454)) or the remote IP address. For embedded servers, it may be helpful to convert this task into a systemd service or something similar to facilitate automation. If a different port or configuration is desired, review how the application is launched in app.appRun() and create a custom script. It can be manually terminated by pressing `ctrl + c` or closing the terminal window.

## Customization
**plfluidics** is designed with a model-view-controller framework that uses a driver adapter pattern so that a various types of hardware can be used as long as they share a common interface. The \drivers directory is for low level interfacing with the OS. The \hardware directory is for higher level abstractions of the hardware that directly interface with the MVC framework. The \server directory holds the MVC code.

### Adding new hardware
1. Create driver software that facilitates communication with valve controller or sensors
2. Create classes for your hardware that can process program inputs and feed commands to the driver
3. Update the driverSet method in the ModelHardware class to initialize your hardware
4. Create a configuration file with initialization parameters for your hardware

### Adding a new device
1. Create a configuration file with initialization parameters and aliases that match your device
2. Create a new HTML template in the /server/templates directory