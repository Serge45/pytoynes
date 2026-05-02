# cython: language_level=3
from .ppu cimport PPU
from .cartridge cimport Cartridge

cdef class Bus:
    cdef public unsigned char[:] ram
    cdef public PPU ppu
    cdef public list controllers
    cdef public Cartridge _cartridge

    cpdef int read(self, int addr)
    cpdef void write(self, int addr, int data)
