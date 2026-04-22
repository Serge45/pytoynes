# cython: language_level=3
from .ppu cimport PPU

cdef class Bus:
    cdef public unsigned char[:] ram
    cdef public PPU ppu
    cdef public list controllers
    cdef public object _cartridge
    cdef unsigned char[:] _prg_memory
    cdef unsigned int _prg_mask

    cpdef int read(self, int addr)
    cpdef void write(self, int addr, int data)
