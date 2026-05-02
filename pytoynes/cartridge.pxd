# cython: language_level=3
from .mapper cimport Mapper

cdef class Cartridge:
    cdef public object rom
    cdef public Mapper mapper
    cdef public unsigned char[:] prg_memory
    cdef public unsigned char[:] chr_memory
    cdef public unsigned char[:] prg_ram

    cpdef int cpu_read(self, int addr)
    cpdef int cpu_write(self, int addr, int data)
    cpdef int ppu_read(self, int addr)
    cpdef int ppu_write(self, int addr, int data)
