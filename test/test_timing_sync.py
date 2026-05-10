import unittest
from pytoynes.bus import Bus
from pytoynes.mos6502 import MOS6502
from pytoynes.cartridge import Cartridge

class TestTimingSync(unittest.TestCase):
    def setUp(self):
        self.bus = Bus()
        self.cpu = MOS6502()
        self.cpu.connect(self.bus)
        # We need a cartridge to run run_frame safely (it accesses mapper)
        self.bus.cartridge = Cartridge('./pytoynes/assets/nestest.nes')

    def test_ppu_cpu_3to1_ratio(self):
        """Verify that PPU cycles are exactly 3x CPU cycles after instruction execution."""
        # Initial state
        self.bus.apu.total_cycles = 0
        self.bus.ppu.total_cycles = 0
        
        # Run one instruction
        # We'll use a direct clock() call to simulate CPU work
        instr_cycles = self.cpu.clock()
        self.bus.apu.clock_n(instr_cycles)
        self.bus.ppu.run_to(self.bus.apu.total_cycles * 3)
        
        self.assertEqual(self.bus.ppu.total_cycles, self.bus.apu.total_cycles * 3)
        self.assertEqual(self.bus.apu.total_cycles, instr_cycles)

    def test_run_frame_cycle_limit(self):
        """Verify that bus.run_frame executes approximately 29780.5 CPU cycles."""
        start_cycles = self.bus.apu.total_cycles
        self.bus.run_frame(self.cpu)
        end_cycles = self.bus.apu.total_cycles
        
        executed = end_cycles - start_cycles
        
        # NTSC frame is ~29780.5 cycles. 
        # Our loop terminates as soon as we hit >= 29781.
        # So it should be close to 29781 + max_instr_length (7).
        self.assertGreaterEqual(executed, 29780)
        self.assertLessEqual(executed, 29800)

    def test_ppu_vblank_timing(self):
        """Verify that PPU enters VBlank at the expected cycle count."""
        # Reset PPU state
        self.bus.ppu.scanline = 0
        self.bus.ppu.cycle = 0
        self.bus.ppu.total_cycles = 0
        
        # Run to scanline 241 (VBlank start)
        # Scanlines 0-240 = 241 scanlines * 341 cycles = 82181 PPU cycles
        target_ppu_cycles = 241 * 341
        self.bus.ppu.run_to(target_ppu_cycles)
        
        self.assertTrue(self.bus.ppu.ppu_status & 0x80, "PPU Status VBlank bit not set at scanline 241.")
        self.assertEqual(self.bus.ppu.scanline, 241)

if __name__ == '__main__':
    unittest.main()
