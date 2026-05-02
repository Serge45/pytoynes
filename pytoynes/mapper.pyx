# cython: language_level=3, boundscheck=False, wraparound=False

cdef class Mapper:
    def __init__(self, int num_prg_banks, int num_chr_banks):
        self.num_prg_banks = num_prg_banks
        self.num_chr_banks = num_chr_banks

    cpdef int map_cpu_read_addr(self, int addr):
        return -1

    cpdef int map_cpu_write_addr(self, int addr):
        return -1

    cpdef int map_ppu_read_addr(self, int addr):
        return -1

    cpdef int map_ppu_write_addr(self, int addr):
        return -1

cdef class Mapper000(Mapper):
    cdef inline int _map_cpu_addr(self, int addr):
        cdef int mask
        if addr >= 0x8000 and addr <= 0xFFFF:
            mask = 0x7FFF if self.num_prg_banks > 1 else 0x3FFF
            return addr & mask
        return -1

    cpdef int map_cpu_read_addr(self, int addr):
        return self._map_cpu_addr(addr)

    cpdef int map_cpu_write_addr(self, int addr):
        return self._map_cpu_addr(addr)

    cpdef int map_ppu_read_addr(self, int addr):
        if addr >= 0x0000 and addr <= 0x1FFF:
            return addr
        return -1

    cpdef int map_ppu_write_addr(self, int addr):
        if addr >= 0x0000 and addr <= 0x1FFF:
            if self.num_chr_banks == 0:
                # Treat as CHR-RAM
                return addr
        return -1
