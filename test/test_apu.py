import unittest
from pytoynes.apu import APU

class TestAPU(unittest.TestCase):
    def test_status_register(self):
        apu = APU()
        # Enable Pulse 1
        apu.cpu_write(0x4015, 0x01)
        # Status should be 0 because length counter is 0
        self.assertEqual(apu.cpu_read(0x4015), 0x00)
        
        # Load length counter for Pulse 1
        # Timer High $4003: Bits 3-7 are length index
        # Index 0 is 10
        apu.cpu_write(0x4003, 0x00) 
        # Now status should be 1
        self.assertEqual(apu.cpu_read(0x4015), 0x01)

    def test_pulse1_timer_and_duty(self):
        apu = APU()
        apu.cpu_write(0x4015, 0x01)
        apu.cpu_write(0x4000, 0x80) # 50%
        apu.cpu_write(0x4002, 0x01)
        apu.cpu_write(0x4003, 0x00) # Length index 0 (10)
        
        # Step 0
        self.assertEqual(apu.get_pulse1_sample(), 0)
        apu.clock_n(4)
        self.assertEqual(apu.get_pulse1_sample(), 1)

    def test_length_counter_decrement(self):
        apu = APU()
        apu.cpu_write(0x4015, 0x01)
        # Length index 3 is 2
        apu.cpu_write(0x4003, (0x03 << 3))
        self.assertEqual(apu.pulse1_lc_value, 2)
        
        # 4-step mode (default)
        # Half frame at 7456 and 14914
        apu.clock_n(7456)
        self.assertEqual(apu.pulse1_lc_value, 1)
        apu.clock_n(7458) # Total 14914
        self.assertEqual(apu.pulse1_lc_value, 0)
        self.assertEqual(apu.get_pulse1_sample(), 0)
        self.assertEqual(apu.cpu_read(0x4015), 0)

    def test_frame_counter_mode1(self):
        apu = APU()
        # 5-step mode
        apu.cpu_write(0x4017, 0x80)
        # Setting mode 1 triggers an immediate half frame clock
        # Load LC index 0 (10)
        apu.cpu_write(0x4015, 0x01)
        apu.cpu_write(0x4003, 0x00)
        self.assertEqual(apu.pulse1_lc_value, 10)
        
        apu.cpu_write(0x4017, 0x80) # Reset and trigger immediate half frame
        self.assertEqual(apu.pulse1_lc_value, 9)

if __name__ == '__main__':
    unittest.main()
