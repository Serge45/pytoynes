from typing import Optional
from .rom import Rom
from .mapper import Mapper, Mapper000

class Cartridge:
    def __init__(self, rom_path: str):
        self.rom = Rom(rom_path)
        self.mapper: Optional[Mapper] = None
        # make deep copy for reset
        self.prg_memory = self.rom.prg_rom_data[:]

        if self.rom.mapper == 0:
            self.mapper = Mapper000(self.rom.num_prg_banks, self.rom.num_chr_banks)

    def cpu_read(self, addr: int):
        assert self.mapper, 'No valid mapper'

        mapped_addr = self.mapper.map_cpu_read_addr(addr)

        if mapped_addr is not None:
            return self.prg_memory[mapped_addr]

    def cpu_write(self, addr: int, data):
        assert self.mapper, 'No valid mapper'
        mapped_addr = self.mapper.map_cpu_read_addr(addr)

        if mapped_addr is not None:
            self.prg_memory[mapped_addr] = data
            return data

    def ppu_read(self, addr: int):
        if addr >= 0 and addr <= 0x1FFF:
            return self.rom.chr_rom_data[addr]

    def ppu_write(self, addr: int, data: int):
        pass
