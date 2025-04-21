
'''
Register | Addr   | Def | Purpose
---------|--------|-----|--------
out_ctrl | 000000 | 00h | control outputs
in_map_0 | 000100 | 04h | input0 -> output#
in_map_1 | 000101 | 08h | input1 -> output#
in_stat  | 000110 | 00h | transmission and input status
ol_curr  | 001000 | 00h | control open load current
out_stat | 001001 | 00h | detects open loads
config1  | 001100 | 00h | control device behavior
out_clr  | 001101 | 00h | clear output error latches
config2  | 101000 | 00h | control device behavior

'''

class drv81001():
    def __init__(self):
        self.undervolt_err = 0
        self.mode = 0
        self.trans_err = 0
        self.open_load_err = 0
        self.overload_err = 0
        self.outputs = 0
        self.open_load_ctl = 0
        self.open_load_status = 0

        self.active = 0
        self.reset = 0
        self.open_load_dis = 0
        self.ocurr_prof = 0
        self.error = 0
        self.overtemp = 0
        self.slew_fast = 0
        self.lock_sts = 0

        self._read  = 0b0100000000000000
        self._write = 0b1000000000000000
        self.data = 0

        # Addresses
        self.addr_offset = 8
        self.out_ctrl = 0b000000
        self.in_map_0 = 0b000100
        self.in_map_1 = 0b000101
        self.in_stat  = 0b000110
        self.ol_curr  = 0b001000
        self.out_stat = 0b001001
        self.config1  = 0b001100
        self.out_clr  = 0b001101
        self.config2  = 0b101000

        # Bitmask
        self._8 = 0b1 << 7
        self._7 = 0b1 << 6
        self._6 = 0b1 << 5
        self._5 = 0b1 << 4
        self._4 = 0b1 << 3
        self._3 = 0b1 << 2
        self._2 = 0b1 << 1
        self._1 = 0b1

        ## Standard diagnosis
        self._undervolt = 0b1 << 14
        self._mode = 0b11 << 11
        self._trans_err = 0b1 << 10
        self._oload = 0b1 << 8

        self._chan = 0b11111111

        ## Input mask
        self._terr = 0b1 << 7

        ## Config 1
        self._active = 0b1 << 7
        self._reset = 0b1 << 6
        self._dis_ol = 0b1 << 5
        self._ocp = 0b1 << 4

        ## Config 2
        self._lkunlk = 0b111 << 5
        self._lock = 0b110 << 5
        self._unlock = 0b011 << 5
        self._otw = 0b1 << 2
        self._slew = 0b1

    def _addr_shift(self, addr):
        return addr << self.addr_offset
    
    def toggleAddrBit(self, addr, bit):
        self.cmd_read_addr(addr)
        self.data = self.data ^ (1 << bit)
        self.cmd_write_addr(self, addr, self.data)
    
    def cmdWriteAddr(self,addr,data):
        return self._send(self._write + self._addr_shift(addr) + data)
    
    def cmdReadAddr(self,addr):
        self.data = self._send(self._read + self._addr_shift(addr) + 0b10)
        return self.data
    
    def _send():
        pass

    def toggleActive(self):
        self.toggleAddrBit(self.config1,7)
    
    def toggleOpenLoadDetection(self):
        self.toggleAddrBit(self.config1, 5)

    def toggleOpenLoadCurrBit(self, bit):
        self.toggleAddrBit()

    def readRegisters(self):
        self.read_standard_diagnosis()
        self.read_output_control()
        self.read_open_load_curr()
        self.read_output_status()
        self.read_config1()
        self.read_output_clear_latch()
        self.read_config2()

    def readStandardDiagnosis(self):
        self.cmd_read_addr(self._read + 0b01)  # Read standard diagnosis
        self.undervolt_err = bool(self.data & self._undervolt) 
        self.mode = self.data & self._mode
        self.trans_err = bool(self.data & self._trans_err)
        self.open_load_err = bool(self.data & self._oload)
        self.overload_err = bool(self.data & self._err)

    def readOutputControl(self):
        self.cmd_read_addr(self._read + self.out_ctrl)  # Read state of outputs
        self.outputs = self.data & self._chan

    def readOpenLoadCurr(self):
        self.cmd_read_addr(self._read + self.ol_curr)  # Read open load monitoring
        self.open_load_ctl = self.data & self._chan

    def readOutputStatus(self):
        self.cmd_read_addr(self._read + self.out_stat)  # Read open load status
        self.open_load_status = self.data & self._chan

    def readConfig1(self):
        self.cmd_read_addr(self._read + self.config1)  # Read config1
        self.active = self.data & self._active
        self.reset = self.data & self._reset
        self.open_load_dis = self.data & self._dis_ol
        self.ocurr_prof = self.data & self._ocp

    def readOutputClearLatch(self):
        self.cmd_read_addr(self._read + self.out_clr)  # Read output latch
        self.error = self.data & self._chan

    def readConfig2(self):
        self.cmd_read_addr(self._read + self.config2)
        self.lock_sts = self.data & self._lkunlk
        self.overtemp = self.data & self._otw
        self.slew_fast = self.data & self._slew