from array import array
import os
import pathlib
import unittest
from pytoynes.rom import Rom
from pytoynes.mos6502 import MOS6502
from pytoynes.bus import Bus

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
        # TODO: use cartridge
        p = pathlib.Path('./pytoynes/assets/nestest.nes').absolute()
        rom = Rom(str(p))
        self.assertIsNotNone(rom.prg_rom_data)
        self.assertIsNotNone(rom.chr_rom_data)
        
        bus = Bus()
        cpu = MOS6502()
        cpu.connect(bus)
        ref_status = load_ref_ans_status(os.path.abspath('./pytoynes/assets/ref_ans.txt'))
        program = array('B', rom.prg_rom_data)
        bus.ram[0x8000:0xBFFF] = program
        bus.ram[0xC000:0xFFFF] = program
        cpu.pc = 0xC000
        n_ops = 0

        def on_opcode_loaded():
            nonlocal n_ops
            if cpu.opcode:
                if n_ops < len(ref_status):
                    self.assertEqual(cpu.all_status_as_int(), ref_status[n_ops])
                n_ops += 1

        cpu.on_opcode_loaded = on_opcode_loaded

        while n_ops < len(ref_status):
            cpu.clock()
