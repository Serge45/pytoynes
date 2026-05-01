import unittest
import os
import pygame
import numpy as np
import hashlib
from pytoynes.bus import Bus
from pytoynes.mos6502 import MOS6502
from pytoynes.cartridge import Cartridge

class TestRendering(unittest.TestCase):
    def test_headless_rendering(self):
        # Paths
        base_dir = os.path.dirname(os.path.dirname(__file__))
        rom_path = os.path.join(base_dir, 'pytoynes', 'assets', 'nestest.nes')
        
        # Setup Emulator
        cpu = MOS6502()
        bus = Bus()
        cpu.connect(bus)
        cartridge = Cartridge(rom_path)
        bus.cartridge = cartridge
        bus.ppu.ppu_mask = 0x1E # Enable BG/Sprites

        cpu.reset()
        lo = bus.read(0xFFFC)
        hi = bus.read(0xFFFD)
        cpu.pc = (hi << 8) | lo
        total_cpu_cycles = 7

        # Initialize Pygame in headless mode
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        pygame.init()
        # Using flags=pygame.HIDDEN for modern SDL2, but 'dummy' driver is safer for headless
        screen = pygame.display.set_mode((256, 240))

        # Run for 300 frames
        for frame in range(300):
            cycles_this_frame = 0
            while cycles_this_frame < 29780:
                cycles = cpu.clock()
                cycles_this_frame += cycles
                total_cpu_cycles += cycles
                # PPU synchronization
                bus.ppu.run_to(total_cpu_cycles * 3)
                if bus.ppu.nmi:
                    bus.ppu.nmi = False
                    cpu.nmi()

        # Capture final frame pixels
        final_pixels = bus.ppu.pixels.copy()
        
        # Calculate a hash of the pixels to verify consistency
        pixel_hash = hashlib.md5(final_pixels.tobytes()).hexdigest()
        
        # For now, just assert that it's not all zeros (which would mean no rendering happened)
        self.assertTrue(np.any(final_pixels > 0), "PPU output is empty (all zeros)")
        
        # Expected hash (calculated from current implementation which I verified manually as "good enough" progress)
        expected_hash = "2f32ec5b83d43597924f59acdf440f08" # Hash for 300 frames of nestest
        self.assertEqual(pixel_hash, expected_hash, "Rendering regression detected (pixel hash mismatch)")

        pygame.quit()

if __name__ == '__main__':
    unittest.main()
