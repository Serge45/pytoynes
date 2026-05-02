# cython: language_level=3

cdef class Mapper:
    cdef public int num_prg_banks
    cdef public int num_chr_banks

    cpdef int map_cpu_read_addr(self, int addr)
    cpdef int map_cpu_write_addr(self, int addr)
    cpdef int map_ppu_read_addr(self, int addr)
    cpdef int map_ppu_write_addr(self, int addr)

cdef class Mapper000(Mapper):
    cdef inline int _map_cpu_addr(self, int addr)
