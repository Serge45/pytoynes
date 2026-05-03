class APU:
    # Standard NES Duty Cycle sequences (8 steps each)
    DUTY_TABLE = [
        [0, 1, 0, 0, 0, 0, 0, 0], # 12.5%
        [0, 1, 1, 0, 0, 0, 0, 0], # 25%
        [0, 1, 1, 1, 1, 0, 0, 0], # 50%
        [1, 0, 0, 1, 1, 1, 1, 1], # 25% negated
    ]

    def __init__(self):
        # Register stubs
        self.pulse1_enabled = False
        self.pulse2_enabled = False
        self.triangle_enabled = False
        self.noise_enabled = False
        self.dmc_enabled = False
        
        # Pulse 1 Channel State
        self.pulse1_duty_mode = 0
        self.pulse1_duty_step = 0
        self.pulse1_timer_reload = 0
        self.pulse1_timer_value = 0
        
        # Internal Timing
        self.total_cycles = 0
        self.clock_divider = 0 # APU timer clocks every 2 CPU cycles

    def clock(self):
        self.total_cycles += 1
        
        # The Pulse/Noise/DMC timers clock every 2 CPU cycles
        self.clock_divider = (self.clock_divider + 1) & 0x01
        if self.clock_divider == 0:
            if self.pulse1_timer_value == 0:
                self.pulse1_timer_value = self.pulse1_timer_reload
                self.pulse1_duty_step = (self.pulse1_duty_step + 1) & 0x07
            else:
                self.pulse1_timer_value -= 1

    def get_pulse1_sample(self):
        if not self.pulse1_enabled:
            return 0
        # Return 1 if current duty step is active
        return self.DUTY_TABLE[self.pulse1_duty_mode][self.pulse1_duty_step]

    def cpu_read(self, addr):
        if addr == 0x4015:
            # Status register: Currently returning 0 because length counters
            # are not implemented. Returning 1s causes games like Mario to hang.
            return 0
        return 0

    def cpu_write(self, addr, data):
        if addr == 0x4000:
            self.pulse1_duty_mode = (data >> 6) & 0x03
        elif addr == 0x4002:
            self.pulse1_timer_reload = (self.pulse1_timer_reload & 0x0700) | data
        elif addr == 0x4003:
            self.pulse1_timer_reload = (self.pulse1_timer_reload & 0x00FF) | ((data & 0x07) << 8)
            self.pulse1_timer_value = self.pulse1_timer_reload
            self.pulse1_duty_step = 0 # Reset duty cycle step
        elif addr == 0x4015:
            # Status register: Enable/Disable channels
            self.pulse1_enabled = bool(data & 0x01)
            self.pulse2_enabled = bool(data & 0x02)
            self.triangle_enabled = bool(data & 0x04)
            self.noise_enabled = bool(data & 0x08)
            self.dmc_enabled = bool(data & 0x10)
        # Other registers ignored for now
