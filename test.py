from plfluidics.drivers.ft4222_hub import FT4222Hub
from plfluidics.drivers.drv81008 import DRV81008_FT4222
ft_hub = None
ft_hub = FT4222Hub()
ft_hub.detectDevices()
print(ft_hub.num_devices)
print('Initializing PLRD1 valve controller.')
ft_hub = FT4222Hub()
ft_hub.detectDevices()
print(ft_hub.num_devices)
if ( ft_hub.num_devices != 4):
    raise ValueError(f'PLRD1 has 4 subunits. Only {ft_hub.num_devices} were detected.')
else:
    print('Initializing FT4222 A')
    flag = "DRV A"
    drvA = DRV81008_FT4222(ft_hub.initSPIDevice('FT4222 A'))
    drvA.readRegisters()
    print('Initializing FT4222 B')
    flag = "DRV B"
    drvB = DRV81008_FT4222(ft_hub.initSPIDevice('FT4222 B'))
    drvB.readRegisters()
    print('Initializing FT4222 C')
    flag = "DRV C"
    drvC = DRV81008_FT4222(ft_hub.initSPIDevice('FT4222 C'))
    print('Initializing FT4222 D')
    flag = "GPIO"
    gpio = ft_hub.initGPIODevice('FT4222 D', outputs=[2,3])
    device = {'A':drvA, 'B': drvB, 'C': drvC, 'LED':gpio}
print('Finished')