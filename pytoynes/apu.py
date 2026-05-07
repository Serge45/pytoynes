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

    def __init__(self):
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

        # Frame Counter (~240Hz)
        self.frame_counter_mode = 0
        self.frame_counter_step = 0
        self.frame_counter_cycles = 0

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

    def clock(self):
        self.total_cycles += 1
        
        # 1. Pulse Timer Clock (Ticks every 2 CPU cycles)
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

        # 2. Frame Counter Clock (NTSC: ~240Hz)
        self.frame_counter_cycles += 1
        if self.frame_counter_mode == 0:
            if self.frame_counter_cycles == 7457: self._clock_quarter_frame()
            elif self.frame_counter_cycles == 14913: self._clock_half_frame()
            elif self.frame_counter_cycles == 22371: self._clock_quarter_frame()
            elif self.frame_counter_cycles == 29829:
                self._clock_half_frame()
                self.frame_counter_cycles = 0
        else:
            if self.frame_counter_cycles == 7457: self._clock_quarter_frame()
            elif self.frame_counter_cycles == 14913: self._clock_half_frame()
            elif self.frame_counter_cycles == 22371: self._clock_quarter_frame()
            elif self.frame_counter_cycles == 29829: pass
            elif self.frame_counter_cycles == 37281:
                self._clock_half_frame()
                self.frame_counter_cycles = 0

        # 3. Audio Resampling (Sample every ~40.58 CPU cycles)
        self.cycle_acc += 1000
        if self.cycle_acc >= 40584: # Fixed point 1000 * 40.584
            self.cycle_acc -= 40584
            
            # Pulse 1 Sample
            raw_sample1 = 0
            if self.pulse1_enabled and self.pulse1_lc_value > 0 and self.pulse1_timer_reload >= 8:
                raw_sample1 = self.DUTY_TABLE[self.pulse1_duty_mode][self.pulse1_duty_step]
            
            # Pulse 2 Sample
            raw_sample2 = 0
            if self.pulse2_enabled and self.pulse2_lc_value > 0 and self.pulse2_timer_reload >= 8:
                raw_sample2 = self.DUTY_TABLE[self.pulse2_duty_mode][self.pulse2_duty_step]

            # Update Visualization Buffer
            self.pulse1_samples[self.sample_ptr] = raw_sample1
            self.sample_ptr = (self.sample_ptr + 1) & 0xFF

            # Mixing and output to audio buffer
            if self.audio_ptr < 2048:
                vol1 = float(self.pulse1_env_decay if not self.pulse1_env_const else self.pulse1_env_vol_period)
                vol2 = float(self.pulse2_env_decay if not self.pulse2_env_const else self.pulse2_env_vol_period)
                s1 = (float(raw_sample1) - 0.5) * (vol1 / 15.0) * 0.5
                s2 = (float(raw_sample2) - 0.5) * (vol2 / 15.0) * 0.5
                self.audio_buffer[self.audio_ptr] = s1 + s2
                self.audio_ptr += 1

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

    def _clock_half_frame(self):
        self._clock_quarter_frame()
        if self.pulse1_lc_value > 0 and not self.pulse1_lc_halt: self.pulse1_lc_value -= 1
        if self.pulse2_lc_value > 0 and not self.pulse2_lc_halt: self.pulse2_lc_value -= 1

    def cpu_read(self, addr):
        data = 0
        if addr == 0x4015:
            if self.pulse1_lc_value > 0: data |= 0x01
            if self.pulse2_lc_value > 0: data |= 0x02
            return data
        return 0

    def cpu_write(self, addr, data):
        # Pulse 1
        if addr == 0x4000:
            self.pulse1_duty_mode = (data >> 6) & 0x03
            self.pulse1_lc_halt = self.pulse1_env_loop = (data & 0x20) != 0
            self.pulse1_env_const = (data & 0x10) != 0
            self.pulse1_env_vol_period = data & 0x0F
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
        elif addr == 0x4006: self.pulse2_timer_reload = (self.pulse2_timer_reload & 0x0700) | data
        elif addr == 0x4007:
            self.pulse2_timer_reload = (self.pulse2_timer_reload & 0x00FF) | ((data & 0x07) << 8)
            self.pulse2_timer_value = self.pulse2_timer_reload
            self.pulse2_duty_step = 0
            if self.pulse2_enabled: self.pulse2_lc_value = self.LENGTH_TABLE[(data >> 3) & 0x1F]
            self.pulse2_env_start = True

        elif addr == 0x4015:
            self.pulse1_enabled = (data & 0x01) != 0
            if not self.pulse1_enabled: self.pulse1_lc_value = 0
            self.pulse2_enabled = (data & 0x02) != 0
            if not self.pulse2_enabled: self.pulse2_lc_value = 0
            self.triangle_enabled = (data & 0x04) != 0
            self.noise_enabled = (data & 0x08) != 0
            self.dmc_enabled = (data & 0x10) != 0
        elif addr == 0x4017:
            self.frame_counter_mode = (data >> 7) & 0x01
            self.frame_counter_cycles = 0
            if self.frame_counter_mode == 1: self._clock_half_frame()

    def clock_n(self, n):
        for _ in range(n):
            self.clock()

    def flush_audio(self, out):
        count = min(self.audio_ptr, len(out))
        out[:count] = self.audio_buffer[:count]
        self.audio_ptr = 0
        return count

    def get_pulse1_sample(self):
        if not self.pulse1_enabled or self.pulse1_lc_value == 0:
            return 0
        if self.pulse1_timer_reload < 8:
            return 0
        return self.DUTY_TABLE[self.pulse1_duty_mode][self.pulse1_duty_step]
