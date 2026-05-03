# cython: language_level=3, boundscheck=False, wraparound=False
import array

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

        self.frame_counter_mode = 0
        self.frame_counter_step = 0
        self.frame_counter_cycles = 0
        
        self.clock_divider = 0
        self.total_cycles = 0

        # Ring buffer for visualization
        self.pulse1_samples = array.array('B', bytearray(256))
        self.sample_ptr = 0

    cpdef void clock(self):
        self.total_cycles += 1
        self.clock_divider = (self.clock_divider + 1) & 0x01
        if self.clock_divider == 0:
            if self.pulse1_timer_value == 0:
                self.pulse1_timer_value = self.pulse1_timer_reload
                self.pulse1_duty_step = (self.pulse1_duty_step + 1) & 0x07
            else:
                self.pulse1_timer_value -= 1
        
        self.frame_counter_cycles += 1
        if self.frame_counter_mode == 0:
            if self.frame_counter_cycles == 3728: self._clock_quarter_frame()
            elif self.frame_counter_cycles == 7456: self._clock_half_frame()
            elif self.frame_counter_cycles == 11185: self._clock_quarter_frame()
            elif self.frame_counter_cycles == 14914:
                self._clock_half_frame()
                self.frame_counter_cycles = 0
        else:
            if self.frame_counter_cycles == 3728: self._clock_quarter_frame()
            elif self.frame_counter_cycles == 7456: self._clock_half_frame()
            elif self.frame_counter_cycles == 11185: self._clock_quarter_frame()
            elif self.frame_counter_cycles == 14914: pass
            elif self.frame_counter_cycles == 18640:
                self._clock_half_frame()
                self.frame_counter_cycles = 0

        # Sample for visualization
        self.pulse1_samples[self.sample_ptr] = self.get_pulse1_sample()
        self.sample_ptr = (self.sample_ptr + 1) & 0xFF

    cpdef void clock_n(self, int n):
        cdef int i
        for i in range(n):
            self.clock()

    cdef void _clock_quarter_frame(self):
        pass

    cdef void _clock_half_frame(self):
        self._clock_quarter_frame()
        if self.pulse1_lc_value > 0 and not self.pulse1_lc_halt:
            self.pulse1_lc_value -= 1

    cpdef int cpu_read(self, int addr):
        cdef int data = 0
        if addr == 0x4015:
            if self.pulse1_lc_value > 0: data |= 0x01
            return data
        return 0

    cpdef void cpu_write(self, int addr, int data):
        if addr == 0x4000:
            self.pulse1_duty_mode = (data >> 6) & 0x03
            self.pulse1_lc_halt = (data & 0x20) != 0
        elif addr == 0x4002:
            self.pulse1_timer_reload = (self.pulse1_timer_reload & 0x0700) | data
        elif addr == 0x4003:
            self.pulse1_timer_reload = (self.pulse1_timer_reload & 0x00FF) | ((data & 0x07) << 8)
            self.pulse1_timer_value = self.pulse1_timer_reload
            self.pulse1_duty_step = 0
            if self.pulse1_enabled:
                self.pulse1_lc_value = LENGTH_TABLE[(data >> 3) & 0x1F]
        elif addr == 0x4015:
            self.pulse1_enabled = (data & 0x01) != 0
            if not self.pulse1_enabled: self.pulse1_lc_value = 0
            self.pulse2_enabled = (data & 0x02) != 0
            self.triangle_enabled = (data & 0x04) != 0
            self.noise_enabled = (data & 0x08) != 0
            self.dmc_enabled = (data & 0x10) != 0
        elif addr == 0x4017:
            self.frame_counter_mode = (data >> 7) & 0x01
            self.frame_counter_cycles = 0
            if self.frame_counter_mode == 1:
                self._clock_half_frame()

    cpdef int get_pulse1_sample(self):
        if not self.pulse1_enabled or self.pulse1_lc_value == 0:
            return 0
        return DUTY_TABLE[self.pulse1_duty_mode][self.pulse1_duty_step]
