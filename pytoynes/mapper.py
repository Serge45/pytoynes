from typing import Optional
from abc import ABC, abstractmethod

class Mapper(ABC):
    def __init__(self, num_prg_banks: int, num_chr_banks: int):
        self.num_prg_banks = num_prg_banks
        self.num_chr_banks = num_chr_banks

    @abstractmethod
    def map_cpu_read_addr(self, addr) -> Optional[int]:
        pass

    @abstractmethod
    def map_cpu_write_addr(self, addr) -> Optional[int]:
        pass

    @abstractmethod
    def map_ppu_read_addr(self, addr) -> Optional[int]:
        pass

    @abstractmethod
    def map_ppu_write_addr(self, addr) -> Optional[int]:
        pass

class Mapper000(Mapper):
    def _map_cpu_addr(self, addr: int) -> Optional[int]:
        if addr >= 0x8000 and addr <= 0xFFFF:
            mask = 0x7FFF if self.num_prg_banks > 1 else 0x3FFF
            return addr & mask

    def map_cpu_read_addr(self, addr: int) -> Optional[int]:
        return self._map_cpu_addr(addr)

    def map_cpu_write_addr(self, addr: int) -> Optional[int]:
        return self._map_cpu_addr(addr)

    def map_ppu_read_addr(self, addr: int) -> Optional[int]:
        if addr >= 0x0000 and addr <= 0x1FFF:
            return addr

    def map_ppu_write_addr(self, addr: int) -> Optional[int]:
        if addr >= 0x0000 and addr <= 0x1FFF:
            if self.num_chr_banks == 0:
                # Treat as CHR-RAM
                return addr
