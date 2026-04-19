from array import array
import os
import pathlib
import unittest
from pytoynes.rom import Rom
from pytoynes.mos6502 import MOS6502
from pytoynes.bus import Bus
from pytoynes.cartridge import Cartridge

def load_ref_ans_status(path: str):
    status = []
    with open(path) as f:
        for line in f.readlines():
            idx = line.find('P:')
            m = line[idx:idx + 4]
            status.append(int(m.split(':')[1], base=16))

    return status

class UnitestRom(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_rom_read(self):
        p = pathlib.Path('./pytoynes/assets/nestest.nes').absolute()
        cartridge = Cartridge(str(p))
        self.assertIsNotNone(cartridge.rom.prg_rom_data)
        self.assertIsNotNone(cartridge.rom.chr_rom_data)

    def test_ppu_access(self):
        p = pathlib.Path('./pytoynes/assets/nestest.nes').absolute()
        cartridge = Cartridge(str(p))
        
        # Test CHR-ROM reading (Mapper 000)
        # nestest.nes should have 8KB of CHR-ROM
        data = cartridge.ppu_read(0x0000)
        self.assertIsNotNone(data)
        
        # Mapper 000 CHR is usually ROM, but our implementation allows 
        # writing if num_chr_banks == 0 (CHR-RAM).
        # nestest has CHR-ROM, so ppu_write should do nothing or at least
        # not crash and not change the ROM.
        original_data = cartridge.ppu_read(0x0000)
        cartridge.ppu_write(0x0000, original_data ^ 0xFF)
        self.assertEqual(cartridge.ppu_read(0x0000), original_data)

    def test_bus_ppu_mapping(self):
        bus = Bus()
        # Test PPUCTRL (0x2000)
        bus.write(0x2000, 0x55)
        self.assertEqual(bus.ppu.ppu_ctrl, 0x55)
        
        # Test Mirroring (0x2008 should map to PPUCTRL too)
        bus.write(0x2008, 0xAA)
        self.assertEqual(bus.ppu.ppu_ctrl, 0xAA)
        
        # Test PPUSTATUS (0x2002) - read only (in our current skeleton)
        bus.ppu.ppu_status = 0x80
        self.assertEqual(bus.read(0x2002), 0x80)
        # Check if address latch was reset by reading PPUSTATUS
        self.assertEqual(bus.ppu.w, 0)

    def test_ppu_data_access(self):
        bus = Bus()
        # Set PPU address to 0x2000 (VRAM)
        bus.write(0x2006, 0x20) # High byte
        bus.write(0x2006, 0x00) # Low byte
        
        # Write some data to VRAM via PPUDATA
        bus.write(0x2007, 0xDE)
        bus.write(0x2007, 0xAD)
        
        # Reset address to 0x2000
        bus.write(0x2006, 0x20)
        bus.write(0x2006, 0x00)
        
        # Read back (buffered)
        # First read should return the buffer (garbage initially, or 0)
        val1 = bus.read(0x2007)
        # Second read should return 0xDE
        val2 = bus.read(0x2007)
        # Third read should return 0xAD
        val3 = bus.read(0x2007)
        
        self.assertEqual(val2, 0xDE)
        self.assertEqual(val3, 0xAD)

    def test_ppu_palette_access(self):
        bus = Bus()
        # Set address to Palette RAM $3F01
        bus.write(0x2006, 0x3F)
        bus.write(0x2006, 0x01)
        
        # Write to palette
        bus.write(0x2007, 0x0F) # black
        
        # Reset address to $3F01
        bus.write(0x2006, 0x3F)
        bus.write(0x2006, 0x01)
        
        # Read back - should be immediate (no buffer delay for palettes)
        val = bus.read(0x2007)
        self.assertEqual(val, 0x0F)
        
        # Address should be $3F02 now. Buffer should contain mirrored nametable data
        # but let's just verify the palette read was immediate.

    def test_oam_dma(self):
        bus = Bus()
        # Fill RAM at 0x0200 with 0-255
        for i in range(256):
            bus.ram[0x0200 + i] = i
            
        # Trigger OAM DMA for page 0x02
        bus.write(0x4014, 0x02)
        
        # Verify PPU OAM content
        for i in range(256):
            self.assertEqual(bus.ppu.oam_vram[i], i)

    def test_nametable_mirroring(self):
        from pytoynes.rom import MirrorMode
        bus = Bus()
        
        # Test Vertical Mirroring
        bus.ppu.mirror_mode = MirrorMode.VERTICAL
        # Write to NT0 ($2000)
        bus.ppu.ppu_write(0x2000, 0xAA)
        # Should be mirrored to NT2 ($2800)
        self.assertEqual(bus.ppu.ppu_read(0x2800), 0xAA)
        
        # Test Horizontal Mirroring
        bus.ppu.mirror_mode = MirrorMode.HORIZONTAL
        # Clear VRAM
        bus.ppu.vram = bytearray(2048)
        # Write to NT0 ($2000)
        bus.ppu.ppu_write(0x2000, 0xBB)
        # Should be mirrored to NT1 ($2400)
        self.assertEqual(bus.ppu.ppu_read(0x2400), 0xBB)
        # NT2 ($2800) should be different from NT0
        bus.ppu.ppu_write(0x2800, 0xCC)
        self.assertEqual(bus.ppu.ppu_read(0x2C00), 0xCC)
        self.assertNotEqual(bus.ppu.ppu_read(0x2000), 0xCC)

    def test_sprite_zero_hit(self):
        bus = Bus()
        ppu = bus.ppu
        
        # Enable BG and Sprites
        ppu.ppu_mask = 0x18
        
        # Setup Sprite 0 at (10, 10)
        ppu.oam_vram[0] = 10 # Y
        ppu.oam_vram[1] = 0x01 # Tile
        ppu.oam_vram[2] = 0x00 # Attr
        ppu.oam_vram[3] = 10 # X
        
        # We need a cartridge for pattern data
        # For simplicity, let's mock cartridge.ppu_read to return 0xFF for tile 0x01
        class MockCartridge:
            def ppu_read(self, addr): return 0xFF
            def ppu_write(self, addr, data): pass
        ppu.cartridge = MockCartridge()
        
        # Setup Background to be opaque at (10, 10)
        # Force bg_shifter_tile_lo to have an opaque bit at the right time
        ppu.bg_shifter_tile_lo = 0xFFFF
        
        # Run PPU until scanline 10, cycle 10
        ppu.scanline = 10
        ppu.cycle = 1
        ppu.sprite_count = 1
        ppu.sprite_shifter_pattern_lo[0] = 0xFF
        ppu.sprite_x_counters[0] = 10
        ppu.sprite_zero_hit_possible = True
        
        # Step cycles
        for i in range(20):
            ppu._update_shifters()
            ppu._render_pixel()
            ppu.cycle += 1
            if ppu.ppu_status & 0x40:
                break
                
        self.assertTrue(ppu.ppu_status & 0x40, "Sprite 0 Hit should be set")

    def test_nestest_cpu(self):
        p = pathlib.Path('./pytoynes/assets/nestest.nes').absolute()
        cartridge = Cartridge(str(p))
        bus = Bus()
        bus.cartridge = cartridge
        cpu = MOS6502()
        cpu.connect(bus)
        cpu.pc = 0xC000
        ref_status = load_ref_ans_status(os.path.abspath('./pytoynes/assets/ref_ans.txt'))
        n_ops = 0

        def on_opcode_loaded():
            nonlocal n_ops
            if cpu.opcode:
                if n_ops < len(ref_status):
                    self.assertEqual(cpu.all_status_as_int(), ref_status[n_ops], f'Status mismatched at n_ops: {n_ops}')
                n_ops += 1

        cpu.on_opcode_loaded = on_opcode_loaded

        while n_ops < len(ref_status):
            cpu.clock()
