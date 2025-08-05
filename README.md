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

### Running application server as a systemd service
If running the server on a dedicated Debian system, it can help to run the application as a service so that it will automatically restart after booting. First, bash script to launch the application. The example script provided below assumes that the virtual environment named `venv-plfluidics` is installed in the home directory of a user named `plfluidics`. The script unloads FTDI VCP drivers (see the troubleshooting section below), starts the virtual environment, and then launches the server.

```bash
#!/bin/bash
/sbin/rmmod ftdi_sio
/sbin/rmmod usbserial
source /home/plfluidics/venv-plfluidics/bin/activate
python3 -m plfluidics.app
```

Once the script has been created, change the permissions of the script so that it can be executed and modified by root and users.

`chmod 0770 /path/to/script.sh`

Then create a systemd service by creating a file named `/etc/systemd/system/plfluidics.service`
```
[Unit]
Description= plfluidics server
After=network.target

[Service]
User=root
ExecStart=/usr/bin/bash /path/to/script.sh
Restart=always
StandardOutput=journal

[Install]
WantedBy=multi-user.target
```

Afterwards, run the service so that it can automatically launch and always be running.

`systemctl enable plfluidics.service`

Confirm that the service is running by checking its status

`systemctl status plfluidics.service`


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

## Troubleshooting

### Errors with the FTDI D2XX driver on Linux
Many Linux distributions have both the VCP and D2XX FTDI drivers installed. However, when trying to connect to a USB device with the D2XX driver, you may run into an error stating something along the lines that only one driver can be used at a time. FTDI provides some suggestions for how to resolve this issue in the "Notes on Kernel Built-in Support of FTDI devices" section of the [D2XX README document](https://ftdichip.com/Driver/D2XX/Linux/ReadMe.txt). If the platform you're using will not be using other FTDI devices, I recommend following the instructions for the first option that removes the kernel module ftdi_sio.