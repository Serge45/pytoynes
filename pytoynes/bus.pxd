# cython: language_level=3
from .ppu cimport PPU
from .cartridge cimport Cartridge
from .apu cimport APU

cdef class Bus:
    cdef public unsigned char[:] ram
    cdef public PPU ppu
    cdef public APU apu
    cdef public list controllers
    cdef public Cartridge _cartridge

    cpdef int read(self, int addr)
    cpdef void write(self, int addr, int data)
