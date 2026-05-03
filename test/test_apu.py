import unittest
from pytoynes.apu import APU

class TestAPU(unittest.TestCase):
    def test_status_register(self):
        apu = APU()
        apu.cpu_write(0x4015, 0x09)
        # We now return 0 intentionally until length counters are implemented
        self.assertEqual(apu.cpu_read(0x4015), 0x00)

    def test_pulse1_timer_and_duty(self):
        apu = APU()
        # Enable Pulse 1
        apu.cpu_write(0x4015, 0x01)
        # Set Duty 50% (Mode 2)
        apu.cpu_write(0x4000, 0x80)
        # Set Timer to 1 (reloads every (1+1)*2 = 4 CPU cycles)
        apu.cpu_write(0x4002, 0x01)
        apu.cpu_write(0x4003, 0x00)
        
        # Mode 2 sequence: [0, 1, 1, 1, 1, 0, 0, 0]
        # Step 0
        self.assertEqual(apu.get_pulse1_sample(), 0)
        
        # Clock 4 times (2 APU ticks) -> Should advance to step 1
        apu.clock_n(4)
        self.assertEqual(apu.get_pulse1_sample(), 1)
        
        # Clock 4 more times -> Step 2
        apu.clock_n(4)
        self.assertEqual(apu.get_pulse1_sample(), 1)
        
        # Clock 12 more times (3 steps) -> Step 5 (value 0)
        apu.clock_n(12)
        self.assertEqual(apu.get_pulse1_sample(), 0)

    def test_clock_n(self):
        apu = APU()
        self.assertEqual(apu.total_cycles, 0)
        apu.clock_n(100)
        self.assertEqual(apu.total_cycles, 100)

if __name__ == '__main__':
    unittest.main()
