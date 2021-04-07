import pathlib
import unittest
import pytoynes
from pytoynes.rom import Rom

class UnitestRom(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_rom_read(self):
        p = pathlib.Path('./pytoynes/assets/nestest.nes').absolute()
        rom = Rom(str(p))
        self.assertIsNotNone(rom.prg_rom_data)
        self.assertIsNotNone(rom.chr_rom_data)
