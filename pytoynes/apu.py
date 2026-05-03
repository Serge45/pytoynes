class APU:
    def __init__(self):
        # Register stubs
        self.pulse1_enabled = False
        self.pulse2_enabled = False
        self.triangle_enabled = False
        self.noise_enabled = False
        self.dmc_enabled = False
        
        # Internal state
        self.total_cycles = 0

    def clock(self):
        self.total_cycles += 1

    def cpu_read(self, addr):
        if addr == 0x4015:
            # Status register: Currently returning 0 because length counters
            # are not implemented. Returning 1s causes games like Mario to hang.
            return 0
        return 0

    def cpu_write(self, addr, data):
        if addr == 0x4015:
            # Status register: Enable/Disable channels
            self.pulse1_enabled = bool(data & 0x01)
            self.pulse2_enabled = bool(data & 0x02)
            self.triangle_enabled = bool(data & 0x04)
            self.noise_enabled = bool(data & 0x08)
            self.dmc_enabled = bool(data & 0x10)
        # Other registers ignored for now
