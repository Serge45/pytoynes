cdef class APU:
    cdef public bint pulse1_enabled
    cdef public bint pulse2_enabled
    cdef public bint triangle_enabled
    cdef public bint noise_enabled
    cdef public bint dmc_enabled
    
    cdef public int pulse1_duty_mode
    cdef public int pulse1_duty_step
    cdef public int pulse1_timer_reload
    cdef public int pulse1_timer_value
    
    cdef public int clock_divider
    cdef public long long total_cycles
    
    cdef public unsigned char[:] pulse1_samples
    cdef public int sample_ptr

    cpdef void clock(self)
    cpdef void clock_n(self, int n)
    cpdef int cpu_read(self, int addr)
    cpdef void cpu_write(self, int addr, int data)
    cpdef int get_pulse1_sample(self)
