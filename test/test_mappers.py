import unittest
from pytoynes.mapper import Mapper001, Mapper002, Mapper003, Mapper004

class TestMappers(unittest.TestCase):
    def test_mapper004_mmc3(self):
        # MMC3: 256KB PRG (32 banks of 8KB), 128KB CHR (128 banks of 1KB)
        mapper = Mapper004(16, 16) # num_prg_banks is 16KB units, so 32 8KB banks
        
        # 1. Test PRG Switching (Mode 0)
        # Select Register 6 (PRG bank at $8000)
        mapper.map_cpu_write_addr(0x8000, 0x06)
        mapper.map_cpu_write_addr(0x8001, 10)
        self.assertEqual(mapper.map_cpu_read_addr(0x8000), 10 * 8192 + 0x0000)
        # $E000 should be last bank (31)
        self.assertEqual(mapper.map_cpu_read_addr(0xE000), 31 * 8192 + 0x0000)
        
        # 2. Test CHR Switching
        # Select Register 0 (2KB CHR at $0000)
        mapper.map_cpu_write_addr(0x8000, 0x00)
        mapper.map_cpu_write_addr(0x8001, 4) # bank 4
        self.assertEqual(mapper.map_ppu_read_addr(0x0000), 4 * 1024 + 0x0000)
        self.assertEqual(mapper.map_ppu_read_addr(0x07FF), 4 * 1024 + 0x07FF)
        
        # 3. Test IRQ Counter
        mapper.map_cpu_write_addr(0xC000, 5) # Latch = 5
        mapper.map_cpu_write_addr(0xC001, 0) # Reload
        mapper.map_cpu_write_addr(0xE001, 1) # Enable
        
        for i in range(6): # Needs 6 calls to go from 0 -> Latch -> 0
            if i < 5:
                self.assertFalse(mapper.irq_active)
            mapper.count_scanline()
            
        self.assertTrue(mapper.irq_active)

    def test_mapper001_mmc1(self):
        # MMC1: 256KB PRG (16 banks), 128KB CHR (16 banks)
        mapper = Mapper001(16, 16)
        
        # Helper to write 5 bits to MMC1 shift register
        def write_mmc1(addr, val):
            for i in range(5):
                mapper.map_cpu_write_addr(addr, (val >> i) & 0x01)

        # 1. Test Control Register (Mirroring)
        # Write 0x00 to Control: 1S_LO mirroring
        write_mmc1(0x8000, 0x00)
        self.assertEqual(mapper.mirror_mode, 2) # ONESCREEN_LO
        
        # Write 0x1F to Control: HORIZ mirroring, PRG mode 3, CHR mode 1
        write_mmc1(0x8000, 0x1F)
        self.assertEqual(mapper.mirror_mode, 0) # HORIZONTAL
        
        # 2. Test PRG Switching (Mode 3: switch $8000, fixed $C000)
        # Mode 3 is default (0x1C)
        # Switch $8000 to bank 5
        write_mmc1(0xE000, 5)
        self.assertEqual(mapper.map_cpu_read_addr(0x8000), 5 * 16384 + 0x0000)
        self.assertEqual(mapper.map_cpu_read_addr(0xC000), 15 * 16384 + 0x0000)
        
        # 3. Test CHR Switching (Mode 1: 4K mode)
        # Mode 1 is default (0x1C has bit 4 set)
        # Switch CHR 0 to bank 10
        write_mmc1(0xA000, 10)
        self.assertEqual(mapper.map_ppu_read_addr(0x0000), 10 * 4096 + 0x0000)
        # Switch CHR 1 to bank 12
        write_mmc1(0xC000, 12)
        self.assertEqual(mapper.map_ppu_read_addr(0x1000), 12 * 4096 + 0x0000)

    def test_mapper002_unrom(self):
        # UNROM: 128KB PRG (8 banks), 0 CHR (using RAM)
        mapper = Mapper002(8, 0)
        
        # Initial state: bank 0 at 0x8000, bank 7 at 0xC000
        self.assertEqual(mapper.map_cpu_read_addr(0x8000), 0 * 16384 + 0x0000)
        self.assertEqual(mapper.map_cpu_read_addr(0xBFFF), 0 * 16384 + 0x3FFF)
        self.assertEqual(mapper.map_cpu_read_addr(0xC000), 7 * 16384 + 0x0000)
        self.assertEqual(mapper.map_cpu_read_addr(0xFFFF), 7 * 16384 + 0x3FFF)
        
        # Switch to bank 3
        mapper.map_cpu_write_addr(0x8000, 3)
        self.assertEqual(mapper.map_cpu_read_addr(0x8000), 3 * 16384 + 0x0000)
        # Bank 7 should remain at 0xC000
        self.assertEqual(mapper.map_cpu_read_addr(0xC000), 7 * 16384 + 0x0000)
        
        # CHR RAM access
        self.assertEqual(mapper.map_ppu_read_addr(0x0000), 0x0000)
        self.assertEqual(mapper.map_ppu_write_addr(0x0000, 0x55), 0x0000)

    def test_mapper003_cnrom(self):
        # CNROM: 32KB PRG (2 banks), 32KB CHR (4 banks)
        mapper = Mapper003(2, 4)
        
        # PRG should be identity (flat 32KB)
        self.assertEqual(mapper.map_cpu_read_addr(0x8000), 0x0000)
        self.assertEqual(mapper.map_cpu_read_addr(0xFFFF), 0x7FFF)
        
        # Initial CHR bank 0
        self.assertEqual(mapper.map_ppu_read_addr(0x0000), 0 * 8192 + 0x0000)
        
        # Switch to CHR bank 2
        mapper.map_cpu_write_addr(0x8000, 2)
        self.assertEqual(mapper.map_ppu_read_addr(0x0000), 2 * 8192 + 0x0000)
        self.assertEqual(mapper.map_ppu_read_addr(0x1FFF), 2 * 8192 + 0x1FFF)
        
        # CHR ROM should be read-only
        self.assertEqual(mapper.map_ppu_write_addr(0x0000, 0x55), -1)

if __name__ == '__main__':
    unittest.main()
