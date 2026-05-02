from typing import Optional
from .rom import Rom
from .mapper import Mapper, Mapper000, Mapper001, Mapper002, Mapper003, Mapper004

class Cartridge:
    def __init__(self, rom_path: str = None):
        if rom_path is not None:
            self.rom = Rom(rom_path)
            # make deep copy for reset
            self.prg_memory = self.rom.prg_rom_data[:]

            if self.rom.num_chr_banks > 0:
                self.chr_memory = self.rom.chr_rom_data[:]
            else:
                self.chr_memory = bytearray(8192)

            if self.rom.mapper == 0:
                self.mapper = Mapper000(self.rom.num_prg_banks, self.rom.num_chr_banks, self.rom.mirroring)
            elif self.rom.mapper == 1:
                self.mapper = Mapper001(self.rom.num_prg_banks, self.rom.num_chr_banks, self.rom.mirroring)
            elif self.rom.mapper == 2:
                self.mapper = Mapper002(self.rom.num_prg_banks, self.rom.num_chr_banks, self.rom.mirroring)
            elif self.rom.mapper == 3:
                self.mapper = Mapper003(self.rom.num_prg_banks, self.rom.num_chr_banks, self.rom.mirroring)
            elif self.rom.mapper == 4:
                self.mapper = Mapper004(self.rom.num_prg_banks, self.rom.num_chr_banks, self.rom.mirroring)
            else:
                self.mapper = Mapper000(self.rom.num_prg_banks, self.rom.num_chr_banks, self.rom.mirroring)
        else:
            self.rom = None
            self.prg_memory = bytearray(65536)
            self.chr_memory = bytearray(8192)
            self.mapper = Mapper000(1, 1)

    def cpu_read(self, addr: int):
        mapped_addr = self.mapper.map_cpu_read_addr(addr)
        if mapped_addr != -1:
            return self.prg_memory[mapped_addr]
        return 0

    def cpu_write(self, addr: int, data):
        mapped_addr = self.mapper.map_cpu_write_addr(addr, data)
        if mapped_addr != -1:
            self.prg_memory[mapped_addr] = data
            return data
        return 0

    def ppu_read(self, addr: int):
        mapped_addr = self.mapper.map_ppu_read_addr(addr)
        if mapped_addr != -1:
            return self.chr_memory[mapped_addr]
        return 0

    def ppu_write(self, addr: int, data: int):
        mapped_addr = self.mapper.map_ppu_write_addr(addr, data)
        if mapped_addr != -1:
            self.chr_memory[mapped_addr] = data
            return data
        return 0
