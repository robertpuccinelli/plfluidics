import ftd2xx as ftd
from time import sleep

device = ftd.open(0) # Open first FTDI device

def numToByte(num):
    return num.to_bytes(1, 'big')

def strToByte(string):
    return string.encode('ascii')

def joinBytes(A,B):
    return b''.join([A,B])

def command(A,B):
    cmd=joinBytes(strToByte(A), numToByte(B))
    print(cmd)
    return cmd

device.write(command('!A',0)) # Setup
device.write(command('!B',0)) # Setup
device.write(command('!C',0)) # Setup
device.write(command('A',0)) # Setup
device.write(command('B',0)) # Setup
device.write(command('C',0)) # Setup

for i in range(0,256):
    device.write(command('A',i))
    sleep(0.01)

device.write(command('A',0)) # Setup


for i in range(0,24):
    device.write(command('H',i))
#    sleep(0.01)
    input('Press enter close valve {} '.format(i))

for i in range(0,24):
    device.write(command('L',i))
#    sleep(0.02)
    input('Press enter close valve {} '.format(i))
