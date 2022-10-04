import unittest
import pytoynes
from pytoynes.mos6502 import MOS6502
from pytoynes.bus import Bus

class UnitestAnd(unittest.TestCase):
    def setUp(self):
        class FakeCartidge:
            def cpu_read(self, _):
                return None

        self.bus = Bus()
        self.bus.cpu.pc = 0
        self.bus.cpu.abs_addr = 0
        self.bus.cartridge = FakeCartidge()

    def tearDown(self):
        pass

    def test_and(self):
        pass

    def test_adc_imm(self):
        self.bus.ram[0] = 0x69
        self.bus.ram[1] = 10
        self.bus.cpu.a = 20
        self.bus.cpu.clock()
        self.assertEqual(self.bus.cpu.a, 30)
