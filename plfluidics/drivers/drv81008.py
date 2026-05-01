from ctypes import BigEndianStructure, c_uint16
import threading
from .ft4222_hub import FT4222SPIDevice_Single
'''
Register | Addr   | Def | Purpose
---------|--------|-----|--------
out_ctrl | 000000 | 00h | control outputs
in_map_0 | 000100 | 04h | input0 -> output#
in_map_1 | 000101 | 05h | input1 -> output#
in_stat  | 000110 | 06h | transmission and input status
ol_curr  | 001000 | 08h | control open load current
out_stat | 001001 | 09h | detects open loads
config1  | 001100 | 0Ch | control device behavior
out_clr  | 001101 | 0Dh | clear output error latches
config2  | 101000 | 28h | control device behavior

'''


class RegStdDiagnosis(BigEndianStructure):
    _fields_ = [
        ("reserved1", c_uint16, 1),
        ("uvrvm", c_uint16, 1),
        ("reserved2", c_uint16, 1),
        ("mode", c_uint16, 2),
        ("ter", c_uint16, 1),
        ("reserved3", c_uint16, 1),
        ("oloff", c_uint16, 1),
        ("err", c_uint16, 8)
        ]


class RegInStsMonitor(BigEndianStructure):
    _fields_ = [
        ("reserved1", c_uint16, 8),
        ("ter", c_uint16, 1),
        ("reserved2", c_uint16, 5),
        ("inst1", c_uint16, 1),
        ("inst0", c_uint16, 1)
    ]


class RegConfig(BigEndianStructure):
    _fields_ = [
        ("reserved1", c_uint16, 8),
        ("act", c_uint16, 1),
        ("rst", c_uint16, 1),
        ("disol", c_uint16, 1),
        ("ocp", c_uint16, 1),
        ("par3", c_uint16, 1),
        ("par2", c_uint16, 1),
        ("par1", c_uint16, 1),
        ("par0", c_uint16, 1)
    ]


class RegConfig2(BigEndianStructure):
    _fields_ = [
        ("reserved1", c_uint16, 8),
        ("lock", c_uint16, 3),
        ("reserved2", c_uint16, 2),
        ("otw", c_uint16, 1),
        ("reserved3", c_uint16, 1),
        ("slew", c_uint16, 1)
    ]


class DRV81008():

    def __init__(self):
        self.mode_states = {0: "RESERVED", 1:"LIMP", 2:"ACTIVE", 3:"IDLE"}

        # DRV81008 Fields
        self.uvrvm  = 0
        self.mode   = 0
        self.ter    = 0
        self.oloff  = 0
        self.err    = 0
        self.en     = 0
        self.map0   = 0
        self.map1   = 0
        self.inst0  = 0
        self.inst1  = 0
        self.iol    = 0
        self.osm    = 0
        self.act    = 0
        self.rst    = 0
        self.disol  = 0
        self.ocp    = 0
        self.par0   = 0
        self.par1   = 0
        self.par2   = 0
        self.par3   = 0
        self.clr    = 0
        self.lock   = 0
        self.otw    = 0
        self.slew   = 0

        # SPI Helpers
        self._read      = 0x4002
        self._read_resp = 0x8000
        self._write     = 0x8000
        self._temp_out  = 0
        self._temp_in   = 0

        # Register Addresses
        self.addr_std_diag  = 0x7F01
        self.addr_en        = 0x0000
        self.addr_map0      = 0x0400
        self.addr_map1      = 0x0500
        self.addr_istm      = 0x0600
        self.addr_iol       = 0x0800
        self.addr_osm       = 0x0900
        self.addr_config1   = 0x0C00
        self.addr_clr       = 0x0D00
        self.addr_config2   = 0x2800
    
    def toggleAddrBit(self, addr, bit):
        toggle_data = self.en ^ (1 << bit)
        self.cmdWriteAddr(addr, toggle_data)
                          
    def toggleOutput(self, output_ch):
        self.toggleAddrBit(self.addr_en, output_ch)
    
    def cmdWriteAddr(self,addr,data):
        resp = self._send(self._write | addr | data)
        self.processResp(resp)
    
    def cmdReadAddr(self,addr):
        resp = self._send(self._read | addr)
        self.processResp(resp)

    def cmdReadStdDiag(self):
        resp = self._send(self.addr_std_diag)
        self.processResp(resp)

    def processResp(self, resp):
        if not (resp & self._read_resp):
            self._parseStd(resp)
        elif (resp & self.addr_en):
            print("Parsing enable")
            self._parseEn(resp)
        elif (resp & self.addr_map0):
            self._parseMap0(resp)
        elif (resp & self.addr_map1):
            self._parseMap1(resp)
        elif (resp & self.addr_istm):
            self._parseISTM(resp)
        elif (resp & self.addr_iol):
            self._parseIOL(resp)
        elif (resp & self.addr_osm):
            self._parseOSM(resp)
        elif (resp & self.addr_config1):
            self._parseConfig1(resp)
        elif (resp & self.addr_clr):
            self._parseClr(resp)
        elif (resp & self.addr_config2):
            self._parseConfig2(resp)

    def _send():
        pass

    def readRegisters(self):
        self.cmdReadStdDiag()
        self.cmdReadAddr(self.addr_en)
        self.cmdReadAddr(self.addr_iol)
        self.cmdReadAddr(self.addr_osm)
        self.cmdReadAddr(self.addr_config1)
        self.cmdReadAddr(self.addr_clr)
        self.cmdReadAddr(self.addr_config2)
        self.cmdReadStdDiag()

    def _parseStd(self,read_data):
        data = RegStdDiagnosis.from_buffer_copy(read_data.to_bytes(2))
        self.uvrvm = data.uvrvm
        self.mode = self.mode_states[data.mode]
        self.ter = data.ter
        self.oloff = data.oloff
        self.err = data.err

    def _parseEn(self, read_data):
        self.outputs = read_data & 0xFF

    def _parseMap0(self, read_data):
        self.map0 = read_data & 0xFF

    def _parseMap1(self, read_data):
        self.map1 = read_data & 0xFF

    def _parseISTM(self, read_data):
        data = RegInStsMonitor.from_buffer_copy(read_data.to_bytes(2))
        self.ter = data.ter
        self.inst0 = data.inst0
        self.inst1 = data.inst1

    def _parseIOL(self, read_data):
        self.iol = read_data & 0xFF

    def _parseOSM(self, read_data):
        self.osm = read_data & 0xFF

    def _parseConfig1(self, read_data):
        data = RegConfig.from_buffer_copy(read_data.to_bytes(2))
        self.act = data.act
        self.rst = data.rst
        self.disol = data.disol
        self.ocp = data.ocp
        self.par0 = data.par0
        self.par1 = data.par1
        self.par2 = data.par2
        self.par3 = data.par3

    def _parseClr(self, read_data):
        self.output_clr = read_data & 0xFF

    def _parseConfig2(self, read_data):
        data = RegConfig2.from_buffer_copy(read_data.to_bytes(2))
        self.lock = self.mode_states[data.lock]
        self.otw = data.otw
        self.slew = data.slew


class DRV81008_FT4222(DRV81008):

    def __init__(self, ft_spi_device: FT4222SPIDevice_Single):
        super().__init__()
        self.controller = ft_spi_device
        self.lock = threading.Lock()

    def _send(self, data: int):
        with self.lock:
            self._temp_out = data
            self._temp_in = int.from_bytes(self.controller.readWrite(data.to_bytes(2, byteorder='big'), term=True))
            return self._temp_in
