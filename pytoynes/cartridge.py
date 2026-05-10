import os
from typing import Optional
from .rom import Rom
from .mapper import Mapper, Mapper000, Mapper001, Mapper002, Mapper003, Mapper004

class Cartridge:
    def __init__(self, rom_path: str = None):
        self.rom_path = rom_path
        if rom_path is not None:
            self.rom = Rom(rom_path)
            # make deep copy for reset
            self.prg_memory = bytearray(self.rom.prg_rom_data)

            if self.rom.num_chr_banks > 0:
                self.chr_memory = bytearray(self.rom.chr_rom_data)
            else:
                self.chr_memory = bytearray(8192)
            
            self.prg_ram = bytearray([0xFF] * 8192)

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
            
            self.load_sram()
        else:
            self.rom = None
            self.prg_memory = bytearray(65536)
            self.chr_memory = bytearray(8192)
            self.prg_ram = bytearray(8192)
            self.mapper = Mapper000(1, 1)

    def cpu_read(self, addr: int):
        mapped_addr = self.mapper.map_cpu_read_addr(addr)
        if mapped_addr != -1:
            if mapped_addr & 0x10000000:
                return self.prg_ram[mapped_addr & 0x0FFFFFFF]
            return self.prg_memory[mapped_addr]
        return 0

    def cpu_write(self, addr: int, data):
        mapped_addr = self.mapper.map_cpu_write_addr(addr, data)
        if mapped_addr != -1:
            if mapped_addr & 0x10000000:
                self.prg_ram[mapped_addr & 0x0FFFFFFF] = data
                return data
            self.prg_memory[mapped_addr] = data
            return data
        return 0

    def ppu_read(self, addr: int):
        mapped_addr = self.mapper.map_ppu_read_addr(addr)
        if mapped_addr != -1:
            return self.chr_memory[mapped_addr]
        return -1

    def ppu_write(self, addr: int, data: int):
        mapped_addr = self.mapper.map_ppu_write_addr(addr, data)
        if mapped_addr != -1:
            self.chr_memory[mapped_addr] = data
            return data
        return -1

    def get_sram_path(self) -> Optional[str]:
        if self.rom_path is None:
            return None
        return os.path.splitext(self.rom_path)[0] + ".sav"

    def load_sram(self):
        if self.rom is None or not self.rom.has_other_persistent_memory:
            return
        
        path = self.get_sram_path()
        if path and os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    data = f.read(8192)
                    self.prg_ram[:len(data)] = data
                print(f"Loaded SRAM from {path}")
            except Exception as e:
                print(f"Error loading SRAM: {e}")

    def save_sram(self):
        if self.rom is None or not self.rom.has_other_persistent_memory:
            return
        
        path = self.get_sram_path()
        if path:
            try:
                with open(path, 'wb') as f:
                    f.write(self.prg_ram)
                print(f"Saved SRAM to {path}")
            except Exception as e:
                print(f"Error saving SRAM: {e}")
