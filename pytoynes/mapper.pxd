# cython: language_level=3

cdef class Mapper:
    cdef public int num_prg_banks
    cdef public int num_chr_banks
    cdef public int mirror_mode
    cdef public bint irq_active

    cpdef int map_cpu_read_addr(self, int addr)
    cpdef int map_cpu_write_addr(self, int addr, int data)
    cpdef int map_ppu_read_addr(self, int addr)
    cpdef int map_ppu_write_addr(self, int addr, int data)
    cpdef void count_scanline(self)

cdef class Mapper000(Mapper):
    cdef inline int _map_cpu_addr(self, int addr)

cdef class Mapper001(Mapper):
    cdef int shift_reg
    cdef int shift_count
    cdef int control_reg
    cdef int chr_bank0_reg
    cdef int chr_bank1_reg
    cdef int prg_bank_reg

cdef class Mapper002(Mapper):
    cdef int prg_bank_lo
    cdef int prg_bank_hi

cdef class Mapper003(Mapper):
    cdef int chr_bank

cdef class Mapper004(Mapper):
    cdef int target_reg
    cdef int prg_bank_mode
    cdef int chr_invert
    cdef int[8] regs
    cdef int irq_counter
    cdef int irq_latch
    cdef bint irq_enabled
