from typing import Optional
from rom import Rom
from mapper import Mapper, Mapper000

class Cartridge:
    def __init__(self, rom_path: str):
        self.rom = Rom(rom_path)
        self.mapper: Optional[Mapper] = None

        if self.rom.mapper == 0:
            self.mapper = Mapper000(self.rom.num_prg_banks, self.rom.num_chr_banks)

    def cpu_read(self, addr: int):
        assert self.mapper, 'No valid mapper'

        if mapped_addr := self.mapper.map_cpu_read_addr(addr):
            return self.rom.prg_rom_data[mapped_addr]

    def cpu_write(self, addr: int, data):
        assert self.mapper, 'No valid mapper'
        if mapped_addr := self.mapper.map_cpu_read_addr(addr):
            self.rom.prg_rom_data[mapped_addr] = data
            return data
