class APU:
    # Standard NES Duty Cycle sequences (8 steps each)
    DUTY_TABLE = [
        [0, 1, 0, 0, 0, 0, 0, 0], # 12.5%
        [0, 1, 1, 0, 0, 0, 0, 0], # 25%
        [0, 1, 1, 1, 1, 0, 0, 0], # 50%
        [1, 0, 0, 1, 1, 1, 1, 1]  # 25% negated
    ]

    # NES Length Counter lookup table
    LENGTH_TABLE = [
        10, 254, 20, 2, 40, 4, 80, 6, 160, 8, 60, 10, 14, 12, 26, 14,
        12, 16, 24, 18, 48, 20, 96, 22, 192, 24, 72, 26, 16, 28, 32, 30
    ]

    TRI_TABLE = [
        15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0,
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
    ]

    NOISE_TABLE = [
        4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068
    ]

    DMC_TABLE = [
        428, 380, 340, 320, 286, 254, 226, 214, 190, 160, 142, 128, 106, 84, 72, 54
    ]

    def __init__(self):
        self.bus = None
        # Channel Enable Status (Register 0x4015)
        self.pulse1_enabled = False
        self.pulse2_enabled = False
        self.triangle_enabled = False
        self.noise_enabled = False
        self.dmc_enabled = False

        # Pulse 1 State
        self.pulse1_duty_mode = 0
        self.pulse1_duty_step = 0
        self.pulse1_timer_reload = 0
        self.pulse1_timer_value = 0
        self.pulse1_lc_value = 0
        self.pulse1_lc_halt = False
        self.pulse1_env_loop = False
        self.pulse1_env_const = False
        self.pulse1_env_vol_period = 0
        self.pulse1_env_start = False
        self.pulse1_env_divider = 0
        self.pulse1_env_decay = 0

        # Pulse 2 State
        self.pulse2_duty_mode = 0
        self.pulse2_duty_step = 0
        self.pulse2_timer_reload = 0
        self.pulse2_timer_value = 0
        self.pulse2_lc_value = 0
        self.pulse2_lc_halt = False
        self.pulse2_env_loop = False
        self.pulse2_env_const = False
        self.pulse2_env_vol_period = 0
        self.pulse2_env_start = False
        self.pulse2_env_divider = 0
        self.pulse2_env_decay = 0

        # Pulse 1 Sweep
        self.p1_sweep_enabled = False
        self.p1_sweep_period = 0
        self.p1_sweep_negate = False
        self.p1_sweep_shift = 0
        self.p1_sweep_reload = False
        self.p1_sweep_divider = 0

        # Pulse 2 Sweep
        self.p2_sweep_enabled = False
        self.p2_sweep_period = 0
        self.p2_sweep_negate = False
        self.p2_sweep_shift = 0
        self.p2_sweep_reload = False
        self.p2_sweep_divider = 0

        # Triangle State
        self.tri_timer_reload = 0
        self.tri_timer_value = 0
        self.tri_lc_value = 0
        self.tri_lc_halt = False
        self.tri_linear_reload = 0
        self.tri_linear_value = 0
        self.tri_linear_reload_flag = False
        self.tri_step = 0

        # Noise State
        self.noise_timer_reload = 0
        self.noise_timer_value = 0
        self.noise_shift_reg = 1
        self.noise_mode = False
        self.noise_lc_value = 0
        self.noise_lc_halt = False
        self.noise_env_loop = False
        self.noise_env_const = False
        self.noise_env_vol_period = 0
        self.noise_env_start = False
        self.noise_env_divider = 0
        self.noise_env_decay = 0

        # DMC State
        self.dmc_irq_enabled = False
        self.dmc_loop = False
        self.dmc_rate_index = 0
        self.dmc_direct_load = 0
        self.dmc_sample_addr = 0
        self.dmc_sample_len = 0
        self.dmc_current_addr = 0
        self.dmc_bytes_remaining = 0
        self.dmc_sample_buffer = 0
        self.dmc_buffer_full = False
        self.dmc_shift_reg = 0
        self.dmc_bits_remaining = 0
        self.dmc_timer_value = 0
        self.dmc_timer_reload = 0
        self.dmc_irq_active = False
        self.dmc_silence_flag = True

        # Frame Counter (~240Hz)
        self.frame_counter_mode = 0
        self.frame_counter_step = 0
        self.frame_counter_cycles = 0
        self.frame_irq_active = False
        self.frame_irq_inhibit = False

        # Internal Timing
        self.total_cycles = 0
        self.clock_divider = 0

        # Ring buffer for visualization
        self.pulse1_samples = bytearray(256)
        self.sample_ptr = 0

        # Audio Buffer
        self.audio_buffer = [0.0] * 2048
        self.audio_ptr = 0
        self.cycle_acc = 0
        self.cycles_per_sample = 40.584

    def connect_bus(self, bus):
        self.bus = bus

    def clock(self):
        self.total_cycles += 1
        
        # 1. Timer Clock (Pulse and Noise clock every 2 CPU cycles)
        self.clock_divider ^= 1
        if self.clock_divider == 0:
            # Pulse 1
            if self.pulse1_timer_value == 0:
                self.pulse1_timer_value = self.pulse1_timer_reload
                self.pulse1_duty_step = (self.pulse1_duty_step + 1) & 0x07
            else:
                self.pulse1_timer_value -= 1
            # Pulse 2
            if self.pulse2_timer_value == 0:
                self.pulse2_timer_value = self.pulse2_timer_reload
                self.pulse2_duty_step = (self.pulse2_duty_step + 1) & 0x07
            else:
                self.pulse2_timer_value -= 1
            # Noise
            if self.noise_timer_value == 0:
                self.noise_timer_value = self.noise_timer_reload
                feedback = (self.noise_shift_reg & 0x01) ^ ((self.noise_shift_reg >> (6 if self.noise_mode else 1)) & 0x01)
                self.noise_shift_reg = (self.noise_shift_reg >> 1) | (feedback << 14)
            else:
                self.noise_timer_value -= 1

        # 2. Triangle Timer Clock (Ticks every CPU cycle)
        if self.tri_timer_value == 0:
            self.tri_timer_value = self.tri_timer_reload
            if self.tri_lc_value > 0 and self.tri_linear_value > 0:
                self.tri_step = (self.tri_step + 1) & 0x1F
        else:
            self.tri_timer_value -= 1

        # 3. DMC Clock
        if self.dmc_timer_value == 0:
            self.dmc_timer_value = self.dmc_timer_reload
            if not self.dmc_silence_flag:
                if self.dmc_shift_reg & 0x01:
                    if self.dmc_direct_load <= 125: self.dmc_direct_load += 2
                else:
                    if self.dmc_direct_load >= 2: self.dmc_direct_load -= 2
            self.dmc_shift_reg >>= 1
            self.dmc_bits_remaining -= 1
            if self.dmc_bits_remaining <= 0:
                self.dmc_bits_remaining = 8
                if not self.dmc_buffer_full:
                    self.dmc_silence_flag = True
                else:
                    self.dmc_silence_flag = False
                    self.dmc_shift_reg = self.dmc_sample_buffer
                    self.dmc_buffer_full = False
                    self._dmc_fetch_sample()
        else:
            self.dmc_timer_value -= 1

        # 4. Frame Counter Clock (NTSC: ~240Hz)
        self.frame_counter_cycles += 1
        if self.frame_counter_mode == 0:
            if self.frame_counter_cycles == 7457: self._clock_quarter_frame()
            elif self.frame_counter_cycles == 14913: self._clock_half_frame()
            elif self.frame_counter_cycles == 22371: self._clock_quarter_frame()
            elif self.frame_counter_cycles == 29828:
                if not self.frame_irq_inhibit: self.frame_irq_active = True
            elif self.frame_counter_cycles == 29829:
                self._clock_half_frame()
                if not self.frame_irq_inhibit: self.frame_irq_active = True
                self.frame_counter_cycles = 0
        else:
            if self.frame_counter_cycles == 7457: self._clock_quarter_frame()
            elif self.frame_counter_cycles == 14913: self._clock_half_frame()
            elif self.frame_counter_cycles == 22371: self._clock_quarter_frame()
            elif self.frame_counter_cycles == 29829: pass
            elif self.frame_counter_cycles == 37281:
                self._clock_half_frame()
                self.frame_counter_cycles = 0

        # 5. Audio Resampling (Sample every ~40.58 CPU cycles)
        self.cycle_acc += 1000
        if self.cycle_acc >= 40584: # Fixed point 1000 * 40.584
            self.cycle_acc -= 40584
            
            # Pulse 1 Sample
            raw_sample1 = 0
            tp1 = self._calculate_p1_target_period()
            if self.pulse1_enabled and self.pulse1_lc_value > 0 and self.pulse1_timer_reload >= 8 and tp1 <= 0x7FF:
                raw_sample1 = self.DUTY_TABLE[self.pulse1_duty_mode][self.pulse1_duty_step]
            
            # Pulse 2 Sample
            raw_sample2 = 0
            tp2 = self._calculate_p2_target_period()
            if self.pulse2_enabled and self.pulse2_lc_value > 0 and self.pulse2_timer_reload >= 8 and tp2 <= 0x7FF:
                raw_sample2 = self.DUTY_TABLE[self.pulse2_duty_mode][self.pulse2_duty_step]

            # Triangle Sample
            raw_sample_tri = 0
            if self.triangle_enabled and self.tri_lc_value > 0 and self.tri_linear_value > 0:
                raw_sample_tri = self.TRI_TABLE[self.tri_step]
            
            # Noise Sample
            raw_sample_noise = 0
            if self.noise_enabled and self.noise_lc_value > 0 and not (self.noise_shift_reg & 0x01):
                raw_sample_noise = 1

            # Update Visualization Buffer
            self.pulse1_samples[self.sample_ptr] = raw_sample1
            self.sample_ptr = (self.sample_ptr + 1) & 0xFF

            # Mixing using PRECISE formulas
            if self.audio_ptr < 2048:
                p_vol1 = self.pulse1_env_decay if not self.pulse1_env_const else self.pulse1_env_vol_period
                p_vol2 = self.pulse2_env_decay if not self.pulse2_env_const else self.pulse2_env_vol_period
                n_vol = self.noise_env_decay if not self.noise_env_const else self.noise_env_vol_period
                
                # 1. Pulse Mixing
                pulse_sum = raw_sample1 * p_vol1 + raw_sample2 * p_vol2
                pulse_out = 0.0
                if pulse_sum > 0:
                    pulse_out = 95.88 / ((8128.0 / pulse_sum) + 100.0)
                
                # 2. TND Mixing
                tnd_denom = (raw_sample_tri / 8227.0) + ((raw_sample_noise * n_vol) / 12241.0) + (self.dmc_direct_load / 22638.0)
                tnd_out = 0.0
                if tnd_denom > 0:
                    tnd_out = 159.79 / ((1.0 / tnd_denom) + 100.0)
                
                self.audio_buffer[self.audio_ptr] = (pulse_out + tnd_out) - 0.1
                self.audio_ptr += 1

    def _dmc_fetch_sample(self):
        if self.dmc_bytes_remaining > 0 and not self.dmc_buffer_full:
            if self.bus is not None:
                self.dmc_sample_buffer = self.bus.read(self.dmc_current_addr)
                self.dmc_buffer_full = True
                self.dmc_current_addr = (self.dmc_current_addr + 1) | 0x8000
                self.dmc_bytes_remaining -= 1
                if self.dmc_bytes_remaining == 0:
                    if self.dmc_loop:
                        self.dmc_current_addr = self.dmc_sample_addr
                        self.dmc_bytes_remaining = self.dmc_sample_len
                    elif self.dmc_irq_enabled:
                        self.dmc_irq_active = True

    def _clock_quarter_frame(self):
        # Pulse 1
        if self.pulse1_env_start:
            self.pulse1_env_start = False
            self.pulse1_env_decay = 15
            self.pulse1_env_divider = self.pulse1_env_vol_period
        else:
            if self.pulse1_env_divider == 0:
                self.pulse1_env_divider = self.pulse1_env_vol_period
                if self.pulse1_env_decay > 0: self.pulse1_env_decay -= 1
                elif self.pulse1_env_loop: self.pulse1_env_decay = 15
            else: self.pulse1_env_divider -= 1
        # Pulse 2
        if self.pulse2_env_start:
            self.pulse2_env_start = False
            self.pulse2_env_decay = 15
            self.pulse2_env_divider = self.pulse2_env_vol_period
        else:
            if self.pulse2_env_divider == 0:
                self.pulse2_env_divider = self.pulse2_env_vol_period
                if self.pulse2_env_decay > 0: self.pulse2_env_decay -= 1
                elif self.pulse2_env_loop: self.pulse2_env_decay = 15
            else: self.pulse2_env_divider -= 1
        # Noise
        if self.noise_env_start:
            self.noise_env_start = False
            self.noise_env_decay = 15
            self.noise_env_divider = self.noise_env_vol_period
        else:
            if self.noise_env_divider == 0:
                self.noise_env_divider = self.noise_env_vol_period
                if self.noise_env_decay > 0: self.noise_env_decay -= 1
                elif self.noise_env_loop: self.noise_env_decay = 15
            else: self.noise_env_divider -= 1
            
        # Triangle Linear Counter
        if self.tri_linear_reload_flag:
            self.tri_linear_value = self.tri_linear_reload
        elif self.tri_linear_value > 0:
            self.tri_linear_value -= 1
        if not self.tri_lc_halt:
            self.tri_linear_reload_flag = False

    def _clock_half_frame(self):
        self._clock_quarter_frame()
        self._clock_p1_sweep()
        self._clock_p2_sweep()
        if self.pulse1_lc_value > 0 and not self.pulse1_lc_halt: self.pulse1_lc_value -= 1
        if self.pulse2_lc_value > 0 and not self.pulse2_lc_halt: self.pulse2_lc_value -= 1
        if self.tri_lc_value > 0 and not self.tri_lc_halt: self.tri_lc_value -= 1
        if self.noise_lc_value > 0 and not self.noise_lc_halt: self.noise_lc_value -= 1

    def _calculate_p1_target_period(self):
        period = self.pulse1_timer_reload
        delta = period >> self.p1_sweep_shift
        if self.p1_sweep_negate: return period - delta - 1
        return period + delta

    def _calculate_p2_target_period(self):
        period = self.pulse2_timer_reload
        delta = period >> self.p2_sweep_shift
        if self.p2_sweep_negate: return period - delta
        return period + delta

    def _clock_p1_sweep(self):
        if self.p1_sweep_divider == 0 and self.p1_sweep_enabled and self.p1_sweep_shift > 0:
            target = self._calculate_p1_target_period()
            if target <= 0x7FF and self.pulse1_timer_reload >= 8:
                self.pulse1_timer_reload = target
        if self.p1_sweep_divider == 0 or self.p1_sweep_reload:
            self.p1_sweep_divider = self.p1_sweep_period
            self.p1_sweep_reload = False
        else:
            self.p1_sweep_divider -= 1

    def _clock_p2_sweep(self):
        if self.p2_sweep_divider == 0 and self.p2_sweep_enabled and self.p2_sweep_shift > 0:
            target = self._calculate_p2_target_period()
            if target <= 0x7FF and self.pulse2_timer_reload >= 8:
                self.pulse2_timer_reload = target
        if self.p2_sweep_divider == 0 or self.p2_sweep_reload:
            self.p2_sweep_divider = self.p2_sweep_period
            self.p2_sweep_reload = False
        else:
            self.p2_sweep_divider -= 1

    def cpu_read(self, addr):
        data = 0
        if addr == 0x4015:
            if self.pulse1_lc_value > 0: data |= 0x01
            if self.pulse2_lc_value > 0: data |= 0x02
            if self.tri_lc_value > 0: data |= 0x04
            if self.noise_lc_value > 0: data |= 0x08
            if self.dmc_bytes_remaining > 0: data |= 0x10
            if self.frame_irq_active: data |= 0x40
            if self.dmc_irq_active: data |= 0x80
            self.frame_irq_active = False
            self.dmc_irq_active = False
            return data
        return 0

    def cpu_write(self, addr, data):
        # Pulse 1
        if addr == 0x4000:
            self.pulse1_duty_mode = (data >> 6) & 0x03
            self.pulse1_lc_halt = self.pulse1_env_loop = (data & 0x20) != 0
            self.pulse1_env_const = (data & 0x10) != 0
            self.pulse1_env_vol_period = data & 0x0F
        elif addr == 0x4001:
            self.p1_sweep_enabled = (data & 0x80) != 0
            self.p1_sweep_period = (data >> 4) & 0x07
            self.p1_sweep_negate = (data & 0x08) != 0
            self.p1_sweep_shift = data & 0x07
            self.p1_sweep_reload = True
        elif addr == 0x4002: self.pulse1_timer_reload = (self.pulse1_timer_reload & 0x0700) | data
        elif addr == 0x4003:
            self.pulse1_timer_reload = (self.pulse1_timer_reload & 0x00FF) | ((data & 0x07) << 8)
            self.pulse1_timer_value = self.pulse1_timer_reload
            self.pulse1_duty_step = 0
            if self.pulse1_enabled: self.pulse1_lc_value = self.LENGTH_TABLE[(data >> 3) & 0x1F]
            self.pulse1_env_start = True
        
        # Pulse 2
        elif addr == 0x4004:
            self.pulse2_duty_mode = (data >> 6) & 0x03
            self.pulse2_lc_halt = self.pulse2_env_loop = (data & 0x20) != 0
            self.pulse2_env_const = (data & 0x10) != 0
            self.pulse2_env_vol_period = data & 0x0F
        elif addr == 0x4005:
            self.p2_sweep_enabled = (data & 0x80) != 0
            self.p2_sweep_period = (data >> 4) & 0x07
            self.p2_sweep_negate = (data & 0x08) != 0
            self.p2_sweep_shift = data & 0x07
            self.p2_sweep_reload = True
        elif addr == 0x4006: self.pulse2_timer_reload = (self.pulse2_timer_reload & 0x0700) | data
        elif addr == 0x4007:
            self.pulse2_timer_reload = (self.pulse2_timer_reload & 0x00FF) | ((data & 0x07) << 8)
            self.pulse2_timer_value = self.pulse2_timer_reload
            self.pulse2_duty_step = 0
            if self.pulse2_enabled: self.pulse2_lc_value = self.LENGTH_TABLE[(data >> 3) & 0x1F]
            self.pulse2_env_start = True

        # Triangle
        elif addr == 0x4008:
            self.tri_lc_halt = (data & 0x80) != 0
            self.tri_linear_reload = data & 0x7F
        elif addr == 0x400A: self.tri_timer_reload = (self.tri_timer_reload & 0x0700) | data
        elif addr == 0x400B:
            self.tri_timer_reload = (self.tri_timer_reload & 0x00FF) | ((data & 0x07) << 8)
            self.tri_timer_value = self.tri_timer_reload
            if self.triangle_enabled: self.tri_lc_value = self.LENGTH_TABLE[(data >> 3) & 0x1F]
            self.tri_linear_reload_flag = True

        # Noise
        elif addr == 0x400C:
            self.noise_lc_halt = (data & 0x20) != 0
            self.noise_env_loop = (data & 0x20) != 0
            self.noise_env_const = (data & 0x10) != 0
            self.noise_env_vol_period = data & 0x0F
        elif addr == 0x400E:
            self.noise_mode = (data & 0x80) != 0
            self.noise_timer_reload = self.NOISE_TABLE[data & 0x0F]
        elif addr == 0x400F:
            if self.noise_enabled: self.noise_lc_value = self.LENGTH_TABLE[(data >> 3) & 0x1F]
            self.noise_env_start = True

        # DMC
        elif addr == 0x4010:
            self.dmc_irq_enabled = (data & 0x80) != 0
            self.dmc_loop = (data & 0x40) != 0
            self.dmc_rate_index = data & 0x0F
            self.dmc_timer_reload = self.DMC_TABLE[self.dmc_rate_index]
            if not self.dmc_irq_enabled: self.dmc_irq_active = False
        elif addr == 0x4011: self.dmc_direct_load = data & 0x7F
        elif addr == 0x4012: self.dmc_sample_addr = 0xC000 | (data << 6)
        elif addr == 0x4013: self.dmc_sample_len = (data << 4) | 1

        elif addr == 0x4015:
            self.pulse1_enabled = (data & 0x01) != 0
            if not self.pulse1_enabled: self.pulse1_lc_value = 0
            self.pulse2_enabled = (data & 0x02) != 0
            if not self.pulse2_enabled: self.pulse2_lc_value = 0
            self.triangle_enabled = (data & 0x04) != 0
            if not self.triangle_enabled: self.tri_lc_value = 0
            self.noise_enabled = (data & 0x08) != 0
            if not self.noise_enabled: self.noise_lc_value = 0
            self.dmc_enabled = (data & 0x10) != 0
            if not self.dmc_enabled: self.dmc_bytes_remaining = 0
            else:
                if self.dmc_bytes_remaining == 0:
                    self.dmc_current_addr = self.dmc_sample_addr
                    self.dmc_bytes_remaining = self.dmc_sample_len
                    if not self.dmc_buffer_full: self._dmc_fetch_sample()
            self.dmc_irq_active = False

        elif addr == 0x4017:
            self.frame_counter_mode = (data >> 7) & 0x01
            self.frame_irq_inhibit = (data & 0x40) != 0
            if self.frame_irq_inhibit: self.frame_irq_active = False
            self.frame_counter_cycles = 0
            if self.frame_counter_mode == 1: self._clock_half_frame()

    def clock_n(self, n):
        for _ in range(n): self.clock()

    def flush_audio(self, out):
        count = min(self.audio_ptr, len(out))
        out[:count] = self.audio_buffer[:count]
        self.audio_ptr = 0
        return count

    def get_pulse1_sample(self):
        tp1 = self._calculate_p1_target_period()
        if not self.pulse1_enabled or self.pulse1_lc_value == 0: return 0
        if self.pulse1_timer_reload < 8 or tp1 > 0x7FF: return 0
        return self.DUTY_TABLE[self.pulse1_duty_mode][self.pulse1_duty_step]
