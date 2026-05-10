# cython: language_level=3
from .ppu cimport PPU
from .cartridge cimport Cartridge
from .apu cimport APU
from .mos6502 cimport MOS6502

cdef class Bus:
    cdef public unsigned char[:] ram
    cdef public PPU ppu
    cdef public APU apu
    cdef public list controllers
    cdef public Cartridge _cartridge

    cpdef int read(self, int addr)
    cpdef void write(self, int addr, int data)
    cpdef void run_frame(self, MOS6502 cpu)
