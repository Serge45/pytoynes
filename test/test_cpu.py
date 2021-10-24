import unittest
import pytoynes
from pytoynes.mos6502 import MOS6502
from pytoynes.bus import Bus

class UnitestAnd(unittest.TestCase):
    def setUp(self):
        self.cpu = MOS6502()
        self.bus = Bus()
        self.cpu.connect(self.bus)
        self.cpu.pc = 0
        self.cpu.abs_addr = 0

    def tearDown(self):
        pass

    def test_and(self):
        pass

    def test_adc_imm(self):
        self.bus.ram[0] = 0x69
        self.bus.ram[1] = 10
        self.cpu.a = 20
        self.cpu.clock()
        self.assertEqual(self.cpu.a, 30)
