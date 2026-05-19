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
        self.apu.connect_bus(self)
        self.controllers = [Controller(), Controller()]

    @property
    def cartridge(self):
        return self._cartridge

    @cartridge.setter
    def cartridge(self, cartridge):
        self._cartridge = cartridge
        if cartridge is not None:
            self.ppu.connect_cartridge(cartridge)
            if hasattr(cartridge, 'rom') and cartridge.rom is not None:
                self.ppu.mirror_mode = cartridge.rom.mirroring

    def set_cartridge(self, cartridge: Cartridge):
        self.cartridge = cartridge

    def write(self, addr, data):
        if addr <= 0x1FFF:
            self.ram[addr & 0x07FF] = data & 0xFF
        elif addr <= 0x3FFF:
            self.ppu.cpu_write(0x2000 + (addr % 8), data)
        elif addr >= 0x4000 and addr <= 0x401F:
            if addr == 0x4014:
                # OAM DMA
                for i in range(256):
                    self.ppu.oam_vram[self.ppu.oam_addr] = self.read((data << 8) | i)
                    self.ppu.oam_addr = (self.ppu.oam_addr + 1) & 0xFF
            elif addr == 0x4016:
                self.controllers[0].write(data)
                self.controllers[1].write(data)
            else:
                self.apu.cpu_write(addr, data)
        elif addr >= 0x4020:
            if self._cartridge is not None:
                self._cartridge.cpu_write(addr, data)

    def read(self, addr):
        if addr <= 0x1FFF:
            return self.ram[addr & 0x07FF]
        elif addr <= 0x3FFF:
            return self.ppu.cpu_read(0x2000 + (addr % 8))
        elif addr >= 0x4000 and addr <= 0x401F:
            if addr == 0x4014:
                return 0
            if addr == 0x4016:
                return self.controllers[0].read()
            elif addr == 0x4017:
                return self.controllers[1].read()
            else:
                return self.apu.cpu_read(addr)
        elif addr >= 0x4020:
            if self._cartridge is not None:
                return self._cartridge.cpu_read(addr)
        return 0

    def run_frame(self, cpu):
        cycles_this_frame = 0
        while cycles_this_frame < 29781:
            instr_cycles = cpu.clock()
            self.apu.clock_n(instr_cycles)
            cycles_this_frame += instr_cycles

            if self.ppu.nmi:
                self.ppu.nmi = False
                nmi_cycles = cpu.nmi()
                self.apu.clock_n(nmi_cycles)
                cycles_this_frame += nmi_cycles
            
            if self._cartridge is not None and self._cartridge.mapper is not None:
                if (self._cartridge.mapper.irq_active or self.apu.frame_irq_active or self.apu.dmc_irq_active) and not (cpu.p & 0x04):
                    if self._cartridge.mapper.irq_active:
                        self._cartridge.mapper.irq_active = False
                    irq_cycles = cpu.irq()
                    if irq_cycles > 0:
                        self.apu.clock_n(irq_cycles)
                        cycles_this_frame += irq_cycles

            # Synchronize PPU with the absolute CPU cycle count
            self.ppu.run_to(self.apu.total_cycles * 3)
