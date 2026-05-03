# cython: language_level=3, boundscheck=False, wraparound=False

cdef class APU:
    def __init__(self):
        self.pulse1_enabled = False
        self.pulse2_enabled = False
        self.triangle_enabled = False
        self.noise_enabled = False
        self.dmc_enabled = False
        self.total_cycles = 0

    cpdef void clock(self):
        self.total_cycles += 1

    cpdef void clock_n(self, int n):
        self.total_cycles += n

    cpdef int cpu_read(self, int addr):
        if addr == 0x4015:
            # Return 0 until length counters are implemented to avoid game hangs
            return 0
        return 0

    cpdef void cpu_write(self, int addr, int data):
        if addr == 0x4015:
            self.pulse1_enabled = (data & 0x01) != 0
            self.pulse2_enabled = (data & 0x02) != 0
            self.triangle_enabled = (data & 0x04) != 0
            self.noise_enabled = (data & 0x08) != 0
            self.dmc_enabled = (data & 0x10) != 0
