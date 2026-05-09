# cython: language_level=3, boundscheck=False, wraparound=False
import array
import numpy as np
cimport numpy as np

cdef int DUTY_TABLE[4][8]
DUTY_TABLE[0] = [0, 1, 0, 0, 0, 0, 0, 0] # 12.5%
DUTY_TABLE[1] = [0, 1, 1, 0, 0, 0, 0, 0] # 25%
DUTY_TABLE[2] = [0, 1, 1, 1, 1, 0, 0, 0] # 50%
DUTY_TABLE[3] = [1, 0, 0, 1, 1, 1, 1, 1] # 25% negated

cdef int LENGTH_TABLE[32]
LENGTH_TABLE = [
    10, 254, 20, 2, 40, 4, 80, 6, 160, 8, 60, 10, 14, 12, 26, 14,
    12, 16, 24, 18, 48, 20, 96, 22, 192, 24, 72, 26, 16, 28, 32, 30
]

cdef int TRI_TABLE[32]
TRI_TABLE = [
    15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0,
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
]

cdef int NOISE_TABLE[16]
NOISE_TABLE = [
    4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068
]

cdef class APU:
    def __init__(self):
        self.pulse1_enabled = False
        self.pulse2_enabled = False
        self.triangle_enabled = False
        self.noise_enabled = False
        self.dmc_enabled = False
        
        self.pulse1_duty_mode = 0
        self.pulse1_duty_step = 0
        self.pulse1_timer_reload = 0
        self.pulse1_timer_value = 0
        self.pulse1_lc_value = 0
        self.pulse1_lc_halt = False
        
        self.pulse2_duty_mode = 0
        self.pulse2_duty_step = 0
        self.pulse2_timer_reload = 0
        self.pulse2_timer_value = 0
        self.pulse2_lc_value = 0
        self.pulse2_lc_halt = False

        self.tri_timer_reload = 0
        self.tri_timer_value = 0
        self.tri_lc_value = 0
        self.tri_lc_halt = False
        self.tri_linear_reload = 0
        self.tri_linear_value = 0
        self.tri_linear_reload_flag = False
        self.tri_step = 0

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

        # Envelopes
        self.pulse1_env_loop = False
        self.pulse1_env_const = False
        self.pulse1_env_vol_period = 0
        self.pulse1_env_start = False
        self.pulse1_env_divider = 0
        self.pulse1_env_decay = 0

        self.pulse2_env_loop = False
        self.pulse2_env_const = False
        self.pulse2_env_vol_period = 0
        self.pulse2_env_start = False
        self.pulse2_env_divider = 0
        self.pulse2_env_decay = 0

        self.frame_counter_mode = 0
        self.frame_counter_step = 0
        self.frame_counter_cycles = 0
        
        self.clock_divider = 0
        self.total_cycles = 0

        # Ring buffer for visualization
        self.pulse1_samples = array.array('B', bytearray(256))
        self.sample_ptr = 0
        
        # Audio Resampling (44100Hz from 1.789MHz)
        # Ratio is ~40.585. Using 40585/1000 as fixed point
        self.cycles_per_sample = 40585 # scaled by 1000
        self.cycle_acc = 0
        self.audio_buffer = np.zeros(2048, dtype=np.float32)
        self.audio_ptr = 0

    cpdef void clock(self):
        cdef int raw_sample1 = 0
        cdef int raw_sample2 = 0
        cdef int raw_sample_tri = 0
        cdef int raw_sample_noise = 0
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
                # Feedback: bit 0 XOR bit 1 (mode 0) or bit 6 (mode 1)
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
        
        # 3. Frame Counter Clock (NTSC: ~240Hz)
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
            elif self.frame_counter_cycles == 29829: pass # step 4 does nothing
            elif self.frame_counter_cycles == 37281:
                self._clock_half_frame()
                self.frame_counter_cycles = 0

        # 4. Audio Resampling (Sample every ~40.58 CPU cycles)
        self.cycle_acc += 1000
        if self.cycle_acc >= self.cycles_per_sample:
            self.cycle_acc -= self.cycles_per_sample
            
            # Pulse 1 Sample
            if self.pulse1_enabled and self.pulse1_lc_value > 0 and self.pulse1_timer_reload >= 8:
                raw_sample1 = DUTY_TABLE[self.pulse1_duty_mode][self.pulse1_duty_step]
            
            # Pulse 2 Sample
            if self.pulse2_enabled and self.pulse2_lc_value > 0 and self.pulse2_timer_reload >= 8:
                raw_sample2 = DUTY_TABLE[self.pulse2_duty_mode][self.pulse2_duty_step]

            # Triangle Sample
            if self.triangle_enabled and self.tri_lc_value > 0 and self.tri_linear_value > 0:
                raw_sample_tri = TRI_TABLE[self.tri_step]
            
            # Noise Sample
            if self.noise_enabled and self.noise_lc_value > 0 and not (self.noise_shift_reg & 0x01):
                raw_sample_noise = 1

            # Update Visualization Buffer (Pulse 1)
            self.pulse1_samples[self.sample_ptr] = raw_sample1
            self.sample_ptr = (self.sample_ptr + 1) & 0xFF

            # Mixing and output to audio buffer
            if self.audio_ptr < 2048:
                # 1. Pulse Mixing
                p_vol1 = self.pulse1_env_decay if not self.pulse1_env_const else self.pulse1_env_vol_period
                p_vol2 = self.pulse2_env_decay if not self.pulse2_env_const else self.pulse2_env_vol_period
                
                p1 = raw_sample1 * p_vol1
                p2 = raw_sample2 * p_vol2
                
                pulse_out = 0.0
                if (p1 + p2) > 0:
                    pulse_out = 95.88 / ((8128.0 / (p1 + p2)) + 100.0)
                
                # 2. TND Mixing (Triangle, Noise, DMC)
                n_vol = self.noise_env_decay if not self.noise_env_const else self.noise_env_vol_period
                
                s_tri = <float>raw_sample_tri
                s_noise = <float>raw_sample_noise * n_vol
                s_dmc = 0.0
                
                tnd_out = 0.0
                tnd_denom = (s_tri / 8227.0) + (s_noise / 12241.0) + (s_dmc / 22638.0)
                if tnd_denom > 0:
                    tnd_out = 159.79 / ((1.0 / tnd_denom) + 100.0)
                
                # Combine. We don't subtract a fixed offset to avoid hum during silence.
                # Sound hardware/drivers will typically handle the DC bias.
                self.audio_buffer[self.audio_ptr] = (pulse_out + tnd_out)
                self.audio_ptr += 1

    cpdef void clock_n(self, int n):
        cdef int i
        for i in range(n):
            self.clock()

    cdef void _clock_quarter_frame(self):
        # Clock Envelopes Pulse 1
        if self.pulse1_env_start:
            self.pulse1_env_start = False
            self.pulse1_env_decay = 15
            self.pulse1_env_divider = self.pulse1_env_vol_period
        else:
            if self.pulse1_env_divider == 0:
                self.pulse1_env_divider = self.pulse1_env_vol_period
                if self.pulse1_env_decay > 0:
                    self.pulse1_env_decay -= 1
                elif self.pulse1_env_loop:
                    self.pulse1_env_decay = 15
            else:
                self.pulse1_env_divider -= 1
        
        # Clock Envelopes Pulse 2
        if self.pulse2_env_start:
            self.pulse2_env_start = False
            self.pulse2_env_decay = 15
            self.pulse2_env_divider = self.pulse2_env_vol_period
        else:
            if self.pulse2_env_divider == 0:
                self.pulse2_env_divider = self.pulse2_env_vol_period
                if self.pulse2_env_decay > 0:
                    self.pulse2_env_decay -= 1
                elif self.pulse2_env_loop:
                    self.pulse2_env_decay = 15
            else:
                self.pulse2_env_divider -= 1
        
        # Clock Envelopes Noise
        if self.noise_env_start:
            self.noise_env_start = False
            self.noise_env_decay = 15
            self.noise_env_divider = self.noise_env_vol_period
        else:
            if self.noise_env_divider == 0:
                self.noise_env_divider = self.noise_env_vol_period
                if self.noise_env_decay > 0:
                    self.noise_env_decay -= 1
                elif self.noise_env_loop:
                    self.noise_env_decay = 15
            else:
                self.noise_env_divider -= 1

        # Triangle Linear Counter
        if self.tri_linear_reload_flag:
            self.tri_linear_value = self.tri_linear_reload
        elif self.tri_linear_value > 0:
            self.tri_linear_value -= 1
        
        if not self.tri_lc_halt:
            self.tri_linear_reload_flag = False

    cdef void _clock_half_frame(self):
        self._clock_quarter_frame()
        # Pulse 1 Length Counter
        if self.pulse1_lc_value > 0 and not self.pulse1_lc_halt:
            self.pulse1_lc_value -= 1
        # Pulse 2 Length Counter
        if self.pulse2_lc_value > 0 and not self.pulse2_lc_halt:
            self.pulse2_lc_value -= 1
        # Triangle Length Counter
        if self.tri_lc_value > 0 and not self.tri_lc_halt:
            self.tri_lc_value -= 1
        # Noise Length Counter
        if self.noise_lc_value > 0 and not self.noise_lc_halt:
            self.noise_lc_value -= 1

    cpdef int cpu_read(self, int addr):
        cdef int data = 0
        if addr == 0x4015:
            if self.pulse1_lc_value > 0: data |= 0x01
            if self.pulse2_lc_value > 0: data |= 0x02
            if self.tri_lc_value > 0: data |= 0x04
            if self.noise_lc_value > 0: data |= 0x08
            return data
        return 0

    cpdef void cpu_write(self, int addr, int data):
        # Pulse 1
        if addr == 0x4000:
            self.pulse1_duty_mode = (data >> 6) & 0x03
            self.pulse1_lc_halt = (data & 0x20) != 0
            self.pulse1_env_loop = (data & 0x20) != 0
            self.pulse1_env_const = (data & 0x10) != 0
            self.pulse1_env_vol_period = data & 0x0F
        elif addr == 0x4002:
            self.pulse1_timer_reload = (self.pulse1_timer_reload & 0x0700) | data
        elif addr == 0x4003:
            self.pulse1_timer_reload = (self.pulse1_timer_reload & 0x00FF) | ((data & 0x07) << 8)
            self.pulse1_timer_value = self.pulse1_timer_reload
            self.pulse1_duty_step = 0
            if self.pulse1_enabled:
                self.pulse1_lc_value = LENGTH_TABLE[(data >> 3) & 0x1F]
            self.pulse1_env_start = True
        
        # Pulse 2
        elif addr == 0x4004:
            self.pulse2_duty_mode = (data >> 6) & 0x03
            self.pulse2_lc_halt = (data & 0x20) != 0
            self.pulse2_env_loop = (data & 0x20) != 0
            self.pulse2_env_const = (data & 0x10) != 0
            self.pulse2_env_vol_period = data & 0x0F
        elif addr == 0x4006:
            self.pulse2_timer_reload = (self.pulse2_timer_reload & 0x0700) | data
        elif addr == 0x4007:
            self.pulse2_timer_reload = (self.pulse2_timer_reload & 0x00FF) | ((data & 0x07) << 8)
            self.pulse2_timer_value = self.pulse2_timer_reload
            self.pulse2_duty_step = 0
            if self.pulse2_enabled:
                self.pulse2_lc_value = LENGTH_TABLE[(data >> 3) & 0x1F]
            self.pulse2_env_start = True

        # Triangle
        elif addr == 0x4008:
            self.tri_lc_halt = (data & 0x80) != 0
            self.tri_linear_reload = data & 0x7F
        elif addr == 0x400A:
            self.tri_timer_reload = (self.tri_timer_reload & 0x0700) | data
        elif addr == 0x400B:
            self.tri_timer_reload = (self.tri_timer_reload & 0x00FF) | ((data & 0x07) << 8)
            self.tri_timer_value = self.tri_timer_reload
            if self.triangle_enabled:
                self.tri_lc_value = LENGTH_TABLE[(data >> 3) & 0x1F]
            self.tri_linear_reload_flag = True

        # Noise
        elif addr == 0x400C:
            self.noise_lc_halt = (data & 0x20) != 0
            self.noise_env_loop = (data & 0x20) != 0
            self.noise_env_const = (data & 0x10) != 0
            self.noise_env_vol_period = data & 0x0F
        elif addr == 0x400E:
            self.noise_mode = (data & 0x80) != 0
            self.noise_timer_reload = NOISE_TABLE[data & 0x0F]
        elif addr == 0x400F:
            if self.noise_enabled:
                self.noise_lc_value = LENGTH_TABLE[(data >> 3) & 0x1F]
            self.noise_env_start = True

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
        elif addr == 0x4017:
            self.frame_counter_mode = (data >> 7) & 0x01
            self.frame_counter_cycles = 0
            if self.frame_counter_mode == 1:
                self._clock_half_frame()

    cpdef int get_pulse1_sample(self):
        if not self.pulse1_enabled or self.pulse1_lc_value == 0:
            return 0
        if self.pulse1_timer_reload < 8:
            return 0
        return DUTY_TABLE[self.pulse1_duty_mode][self.pulse1_duty_step]

    cpdef int flush_audio(self, float[:] out):
        cdef int count = self.audio_ptr
        if count > out.shape[0]: count = out.shape[0]
        out[:count] = self.audio_buffer[:count]
        self.audio_ptr = 0
        return count
