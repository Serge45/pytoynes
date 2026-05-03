from typing import Optional
import array
from .cartridge import Cartridge
from .ppu import PPU
from .controller import Controller
from .apu import APU

class Bus:
    def __init__(self):
        self.ram = array.array('B', bytearray(2*1024))
        self._cartridge: Optional[Cartridge] = None
        self.ppu = PPU()
        self.apu = APU()
        self.controllers = [Controller(), Controller()]

    @property
    def cartridge(self):
        return self._cartridge

    @cartridge.setter
    def cartridge(self, cartridge):
        self._cartridge = cartridge
        if cartridge is not None:
            self.ppu.connect_cartridge(cartridge)
            self.ppu.mirror_mode = cartridge.rom.mirroring

    def set_cartridge(self, cartridge: Cartridge):
        self.cartridge = cartridge

    def write(self, addr, data):
        if addr >= 0x4020:
            self.cartridge.cpu_write(addr, data)
        elif addr <= 0x1FFF:
            self.ram[addr & 0x07FF] = data & 0xFF
        elif addr <= 0x3FFF:
            self.ppu.cpu_write(addr, data)
        elif addr == 0x4014:
            base_addr = data << 8
            for i in range(256):
                self.ppu.oam_vram[i] = self.read(base_addr + i)
        elif 0x4000 <= addr <= 0x4017:
            if addr == 0x4016:
                self.controllers[0].write(data)
                self.controllers[1].write(data)
            else:
                self.apu.cpu_write(addr, data)

    def read(self, addr):
        if addr >= 0x4020:
            return self.cartridge.cpu_read(addr)
        elif addr <= 0x1FFF:
            return self.ram[addr & 0x07FF]
        elif addr <= 0x3FFF:
            return self.ppu.cpu_read(addr)
        elif 0x4000 <= addr <= 0x4017:
            if addr == 0x4016:
                return self.controllers[0].read()
            elif addr == 0x4017:
                return self.controllers[1].read()
            else:
                return self.apu.cpu_read(addr)
        return 0
