from typing import Optional
import array
from .cartridge import Cartridge
from .ppu import PPU

class Bus:
    def __init__(self):
        self.ram = array.array('B', bytearray(2*1024))
        self.cartridge: Optional[Cartridge] = None
        self.ppu = PPU()

    def write(self, addr, data):
        written = None
        if self.cartridge:
            written = self.cartridge.cpu_write(addr, data)

        if written is None:
            if addr >= 0 and addr <= 0x1FFF:
                self.ram[addr & 0x07FF] = data & 0xFF
            elif addr >= 0x2000 and addr <= 0x3FFF:
                self.ppu.cpu_write(addr, data)
            elif addr == 0x4014:
                # OAM DMA
                base_addr = data << 8
                for i in range(256):
                    self.ppu.oam_vram[i] = self.read(base_addr + i)
                # TODO: CPU should be stalled for ~513 cycles

    def read(self, addr):
        data = None
        if self.cartridge:
            data = self.cartridge.cpu_read(addr)

        if data is not None:
            return data
        elif addr >= 0 and addr <= 0x1FFF:
            return self.ram[addr & 0x07FF]
        elif addr >= 0x2000 and addr <= 0x3FFF:
            return self.ppu.cpu_read(addr)
        
        return 0
