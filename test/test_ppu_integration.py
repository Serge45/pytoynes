import unittest
import numpy as np
from pytoynes.bus import Bus
from pytoynes.ppu import PPU
from pytoynes.cartridge import Cartridge
from pytoynes.mos6502 import MOS6502

class TestPPUIntegration(unittest.TestCase):
    def setUp(self):
        self.bus = Bus()
        self.cpu = MOS6502()
        self.cpu.connect(self.bus)

    def test_memory_mapping_fallback(self):
        """Verify that PPU falls back to internal VRAM when cartridge doesn't map address."""
        # Cartridge ppu_read should return -1 for 0x2000 (standard nametable)
        # by default if not specialized by a mapper.
        cart = Cartridge() # No ROM, default mapper 0
        self.bus.cartridge = cart
        
        # Write to internal PPU VRAM through PPU register
        self.bus.ppu.vram[0] = 0xA5
        
        # PPU.ppu_read should see this because Cartridge returns -1
        self.assertEqual(self.bus.ppu.ppu_read(0x2000), 0xA5)
        
        # Verify Cartridge itself returns -1
        self.assertEqual(cart.ppu_read(0x2000), -1)

    def test_headless_rendering(self):
        """Verify that running for many frames produces non-zero pixels."""
        rom_path = './pytoynes/assets/nestest.nes'
        cart = Cartridge(rom_path)
        self.bus.cartridge = cart
        self.bus.ppu.ppu_mask = 0x1E # Enable rendering
        
        self.cpu.reset()
        lo = self.bus.read(0xFFFC)
        hi = self.bus.read(0xFFFD)
        self.cpu.pc = (hi << 8) | lo
        
        # Run 60 frames (1 second of emulation)
        for _ in range(60):
            self.bus.run_frame(self.cpu)
            
        # Assert non-zero pixels (it shouldn't be a black screen)
        pixels = np.array(self.bus.ppu.pixels)
        non_zero_count = np.count_nonzero(pixels)
        
        print(f"DEBUG: PPU non-zero pixels after 60 frames: {non_zero_count}")
        self.assertGreater(non_zero_count, 1000, "PPU produced a black or nearly black screen.")

if __name__ == '__main__':
    unittest.main()
