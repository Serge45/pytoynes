from typing import Optional
import array
from .cartridge import Cartridge
from .mos6502 import MOS6502
from .v2c02 import V2C02

class Bus:
    def __init__(self):
        self.ram = array.array('B', bytearray(2*1024))
        self.cartridge: Optional[Cartridge] = None
        self.system_clock = 0
        self.cpu = MOS6502()
        self.cpu.connect(self)
        self.ppu = V2C02()

    def write(self, addr, data):
        written = self.cartridge.cpu_write(addr, data)

        if written is None:
            if addr >= 0 and addr <= 0x1FFF:
                self.ram[addr & 0x07FF] = data & 0xFF
            else:
                #TODO: ppu write to cpu
                pass

    def read(self, addr):
        data = self.cartridge.cpu_read(addr)

        if data is not None:
            return data
        elif addr >= 0 and addr <= 0x1FFF:
            return self.ram[addr & 0x07FF]
        elif addr >= 0x2000 and addr <= 0x3FFF:
            #TODO: ppu read from cpu
            pass
        raise RuntimeError(f'Out of bound accessing: {hex(addr).upper()}')

    def reset(self):
        self.system_clock = 0
        self.cpu.reset()

    def clock(self):
        self.ppu.clock()

        if self.system_clock % 3 == 0:
            self.cpu.clock()

        # Hack to simply unit test
        self.system_clock += 1
