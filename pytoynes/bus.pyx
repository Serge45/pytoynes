# cython: language_level=3, boundscheck=False, wraparound=False
import array
from .cartridge cimport Cartridge
from .ppu cimport PPU
from .apu cimport APU
from .mos6502 cimport MOS6502
from .controller import Controller

cdef class Bus:
    def __init__(self):
        self.ram = array.array('B', bytearray(2*1024))
        self._cartridge = None
        self.ppu = PPU()
        self.apu = APU()
        self.apu.connect_bus(self)
        self.controllers = [Controller(), Controller()]

    property cartridge:
        def __get__(self):
            return self._cartridge
        def __set__(self, val):
            self._cartridge = val
            self.ppu.connect_cartridge(val)

    cpdef int read(self, int addr):
        if addr >= 0x0000 and addr <= 0x1FFF:
            return self.ram[addr % 0x0800]
        elif addr >= 0x2000 and addr <= 0x3FFF:
            return self.ppu.cpu_read(0x2000 + (addr % 8))
        elif addr >= 0x4000 and addr <= 0x401F:
            if addr == 0x4014:
                return 0 # OAM DMA is write-only
            if addr == 0x4016:
                return self.controllers[0].read()
            elif addr == 0x4017:
                return self.controllers[1].read()
            else:
                return self.apu.cpu_read(addr)
        elif addr >= 0x4020 and addr <= 0xFFFF:
            if self._cartridge is not None:
                return self._cartridge.cpu_read(addr)
        return 0

    cpdef void write(self, int addr, int data):
        if addr >= 0x0000 and addr <= 0x1FFF:
            self.ram[addr % 0x0800] = data
        elif addr >= 0x2000 and addr <= 0x3FFF:
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
        elif addr >= 0x4020 and addr <= 0xFFFF:
            if self._cartridge is not None:
                self._cartridge.cpu_write(addr, data)

    cpdef void run_frame(self, MOS6502 cpu):
        cdef int cycles_this_frame = 0
        cdef int instr_cycles = 0
        cdef int nmi_cycles = 0
        cdef int irq_cycles = 0
        
        while cycles_this_frame < 29781:
            instr_cycles = cpu.clock()
            self.apu.clock_n(instr_cycles)
            cycles_this_frame += instr_cycles

            if self.ppu.nmi:
                self.ppu.nmi = False
                nmi_cycles = cpu.nmi()
                self.apu.clock_n(nmi_cycles)
                cycles_this_frame += nmi_cycles
            
            if (self._cartridge.mapper.irq_active or self.apu.frame_irq_active or self.apu.dmc_irq_active) and not (cpu.p & 0x04):
                if self._cartridge.mapper.irq_active:
                    self._cartridge.mapper.irq_active = False
                irq_cycles = cpu.irq()
                if irq_cycles > 0:
                    self.apu.clock_n(irq_cycles)
                    cycles_this_frame += irq_cycles

            # Synchronize PPU with the absolute CPU cycle count
            self.ppu.run_to(self.apu.total_cycles * 3)
