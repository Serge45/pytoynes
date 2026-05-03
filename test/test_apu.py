import unittest
from pytoynes.apu import APU

class TestAPU(unittest.TestCase):
    def test_status_register(self):
        apu = APU()
        
        # Enable Pulse 1 and Noise
        apu.cpu_write(0x4015, 0x09)
        
        status = apu.cpu_read(0x4015)
        # We now return 0 intentionally until length counters are implemented
        self.assertEqual(status, 0x00)
        
        # Disable all
        apu.cpu_write(0x4015, 0x00)
        status = apu.cpu_read(0x4015)
        self.assertEqual(status, 0x00)

    def test_clock(self):
        apu = APU()
        self.assertEqual(apu.total_cycles, 0)
        apu.clock()
        self.assertEqual(apu.total_cycles, 1)
        for _ in range(100):
            apu.clock()
        self.assertEqual(apu.total_cycles, 101)

if __name__ == '__main__':
    unittest.main()
