cdef class APU:
    cdef public bint pulse1_enabled
    cdef public bint pulse2_enabled
    cdef public bint triangle_enabled
    cdef public bint noise_enabled
    cdef public bint dmc_enabled
    cdef public long long total_cycles

    cpdef void clock(self)
    cpdef void clock_n(self, int n)
    cpdef int cpu_read(self, int addr)
    cpdef void cpu_write(self, int addr, int data)
