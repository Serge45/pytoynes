import unittest
from pytoynes.mos6502 import MOS6502, Status
from pytoynes.bus import Bus

from pytoynes.cartridge import Cartridge

class TestCPUEdge(unittest.TestCase):
    def setUp(self):
        self.cpu = MOS6502()
        self.bus = Bus()
        self.cpu.connect(self.bus)
        self.bus.cartridge = Cartridge() # Uses default dummy constructor

    def test_adc_overflow(self):
        # 127 + 1 = 128 (-128 signed), should set V
        self.cpu.a = 0x7F
        self.cpu.p &= ~Status.V
        self.bus.ram[0x0000] = 0x69 # ADC Imm
        self.bus.ram[0x0001] = 0x01
        self.cpu.pc = 0x0000
        self.cpu.clock()
        self.assertEqual(self.cpu.a, 0x80)
        self.assertTrue(self.cpu.p & Status.V)

    def test_sbc_overflow(self):
        # -128 - 1 = -129 (127 signed), should set V
        self.cpu.a = 0x80
        self.cpu.p |= Status.C # SBC needs C=1 for no borrow
        self.cpu.p &= ~Status.V
        self.bus.ram[0x0000] = 0xE9 # SBC Imm
        self.bus.ram[0x0001] = 0x01
        self.cpu.pc = 0x0000
        self.cpu.clock()
        self.assertEqual(self.cpu.a, 0x7F)
        self.assertTrue(self.cpu.p & Status.V)

    def test_brk_flags(self):
        self.cpu.p = Status.U | Status.I
        self.bus.ram[0x0000] = 0x00 # BRK
        # Vector must be in "Cartridge" space for addr >= 0x8000
        self.bus.cartridge.prg_memory[0xFFFE] = 0x00
        self.bus.cartridge.prg_memory[0xFFFF] = 0x10
        self.cpu.pc = 0x0000
        self.cpu.clock()
        # Stack should contain PC+2 and P with B set
        sp = self.cpu.stkp
        p_on_stack = self.bus.ram[0x0100 + sp + 1]
        self.assertTrue(p_on_stack & Status.B)
        self.assertTrue(p_on_stack & Status.U)

if __name__ == '__main__':
    unittest.main()
