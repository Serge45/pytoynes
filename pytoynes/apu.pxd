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
    
    cdef public int pulse2_duty_mode
    cdef public int pulse2_duty_step
    cdef public int pulse2_timer_reload
    cdef public int pulse2_timer_value
    cdef public int pulse2_lc_value
    cdef public bint pulse2_lc_halt

    # Triangle State
    cdef public int tri_timer_reload
    cdef public int tri_timer_value
    cdef public int tri_lc_value
    cdef public bint tri_lc_halt
    cdef public int tri_linear_reload
    cdef public int tri_linear_value
    cdef public bint tri_linear_reload_flag
    cdef public int tri_step

    # Pulse 1 Sweep
    cdef public bint p1_sweep_enabled
    cdef public int p1_sweep_period
    cdef public bint p1_sweep_negate
    cdef public int p1_sweep_shift
    cdef public bint p1_sweep_reload
    cdef public int p1_sweep_divider

    # Pulse 2 Sweep
    cdef public bint p2_sweep_enabled
    cdef public int p2_sweep_period
    cdef public bint p2_sweep_negate
    cdef public int p2_sweep_shift
    cdef public bint p2_sweep_reload
    cdef public int p2_sweep_divider

    # Noise State
    cdef public int noise_timer_reload
    cdef public int noise_timer_value
    cdef public int noise_shift_reg
    cdef public bint noise_mode
    cdef public int noise_lc_value
    cdef public bint noise_lc_halt
    cdef public bint noise_env_loop
    cdef public bint noise_env_const
    cdef public int noise_env_vol_period
    cdef public bint noise_env_start
    cdef public int noise_env_divider
    cdef public int noise_env_decay

    # Pulse 1 Envelope
    cdef public bint pulse1_env_loop
    cdef public bint pulse1_env_const
    cdef public int pulse1_env_vol_period
    cdef public bint pulse1_env_start
    cdef public int pulse1_env_divider
    cdef public int pulse1_env_decay

    # Pulse 2 Envelope
    cdef public bint pulse2_env_loop
    cdef public bint pulse2_env_const
    cdef public int pulse2_env_vol_period
    cdef public bint pulse2_env_start
    cdef public int pulse2_env_divider
    cdef public int pulse2_env_decay

    cdef public int frame_counter_mode
    cdef public int frame_counter_step
    cdef public int frame_counter_cycles
    cdef public bint frame_irq_active
    cdef public bint frame_irq_inhibit
    
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
    cdef int _calculate_p1_target_period(self)
    cdef int _calculate_p2_target_period(self)
    cdef void _clock_p1_sweep(self)
    cdef void _clock_p2_sweep(self)
    cpdef int flush_audio(self, float[:] out)
