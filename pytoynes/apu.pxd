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
    cdef public int pulse1_lc_value
    cdef public bint pulse1_lc_halt
    
    # Pulse 1 Envelope
    cdef public bint pulse1_env_loop
    cdef public bint pulse1_env_const
    cdef public int pulse1_env_vol_period
    cdef public bint pulse1_env_start
    cdef public int pulse1_env_divider
    cdef public int pulse1_env_decay

    cdef public int frame_counter_mode
    cdef public int frame_counter_step
    cdef public int frame_counter_cycles
    
    cdef public int clock_divider
    cdef public long long total_cycles
    
    cdef public unsigned char[:] pulse1_samples
    cdef public int sample_ptr

    # Audio Output
    cdef public float[:] audio_buffer
    cdef public int audio_ptr
    cdef public int cycles_per_sample
    cdef public int cycle_acc

    cpdef void clock(self)
    cpdef void clock_n(self, int n)
    cpdef int cpu_read(self, int addr)
    cpdef void cpu_write(self, int addr, int data)
    cpdef int get_pulse1_sample(self)
    cdef void _clock_quarter_frame(self)
    cdef void _clock_half_frame(self)
    cpdef void flush_audio(self, float[:] out)
