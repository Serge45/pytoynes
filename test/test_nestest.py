import unittest
import os
from pytoynes.bus import Bus
from pytoynes.mos6502 import MOS6502
from pytoynes.cartridge import Cartridge

class TestNestest(unittest.TestCase):
    def test_nestest_execution(self):
        # Paths
        base_dir = os.path.dirname(os.path.dirname(__file__))
        rom_path = os.path.join(base_dir, 'pytoynes', 'assets', 'nestest.nes')
        ref_path = os.path.join(base_dir, 'pytoynes', 'assets', 'ref_ans.txt')
        
        # Setup
        cpu = MOS6502()
        bus = Bus()
        cpu.connect(bus)
        cartridge = Cartridge(rom_path)
        bus.cartridge = cartridge

        # Start at 0xC000 for automated tests
        cpu.reset()
        cpu.pc = 0xC000
        cpu.cycle = 7 # nestest starts at cycle 7

        with open(ref_path, 'r') as f:
            ref_lines = f.readlines()

        # Compare first 8991 instructions (the automated part of nestest)
        for i in range(8991):
            ref_line = ref_lines[i].strip()
            
            # Parse reference state
            # Example line: C000  4C F5 C5  JMP $C5F5                       A:00 X:00 Y:00 P:24 SP:FD PPU:  0, 21 CYC:7
            ref_pc = int(ref_line[0:4], 16)
            ref_a = int(ref_line[50:52], 16)
            ref_x = int(ref_line[55:57], 16)
            ref_y = int(ref_line[60:62], 16)
            ref_p = int(ref_line[65:67], 16)
            ref_sp = int(ref_line[71:73], 16)
            ref_cyc = int(ref_line.split('CYC:')[1])

            # Check state BEFORE execution
            msg = f"Instruction {i} (PC: {ref_pc:04X}): "
            self.assertEqual(cpu.pc, ref_pc, msg + "PC mismatch")
            self.assertEqual(cpu.a, ref_a, msg + "A mismatch")
            self.assertEqual(cpu.x, ref_x, msg + "X mismatch")
            self.assertEqual(cpu.y, ref_y, msg + "Y mismatch")
            self.assertEqual(cpu.p, ref_p, msg + "P mismatch")
            self.assertEqual(cpu.stkp, ref_sp, msg + "SP mismatch")
            self.assertEqual(cpu.cycle, ref_cyc, msg + "Cycle mismatch")

            # Execute
            cycles = cpu.clock()
            cpu.cycle += cycles

if __name__ == '__main__':
    unittest.main()
