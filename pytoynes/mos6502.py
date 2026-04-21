from enum import IntEnum
from typing import Callable, Optional
from .bus import Bus

class Status(IntEnum):
    C = 1
    Z = 1 << 1
    I = 1 << 2
    D = 1 << 3
    B = 1 << 4
    U = 1 << 5
    V = 1 << 6
    N = 1 << 7


class MOS6502:
    def __init__(self):
        self.bus: Optional[Bus] = None
        self.cycle = 0
        self.pc = 0
        self.stkp = 0x00FD
        self.a = 0
        self.x = 0
        self.y = 0
        self.fetched = 0
        self.abs_addr = 0
        self.rel_addr = 0
        self.opcode = 0
        self.status = {s: 0 for s in Status}
        self._set_status(Status.U, True)
        self._set_status(Status.I, True)
        self.jammed = False
        self.on_opcode_loaded = None
        
        # Optimized opcode dispatch table
        self.opcode_table = [None] * 256
        self._init_opcode_table()
        print(f'{len([x for x in self.opcode_table if x is not None])} instructions were implemented')

    def _init_opcode_table(self):
        # (Name, Compute, Address, Cycles)
        lookup = {
            0x69: ("ADC", self._comp_adc, self._addr_imm, 2),
            0x65: ("ADC", self._comp_adc, self._addr_zp0, 3),
            0x75: ("ADC", self._comp_adc, self._addr_zpx, 4),
            0x6D: ("ADC", self._comp_adc, self._addr_abs, 4),
            0x7D: ("ADC", self._comp_adc, self._addr_abx, 4),
            0x79: ("ADC", self._comp_adc, self._addr_aby, 4),
            0x61: ("ADC", self._comp_adc, self._addr_izx, 6),
            0x71: ("ADC", self._comp_adc, self._addr_izy, 5),
            0x29: ("AND", self._comp_and, self._addr_imm, 2),
            0x25: ("AND", self._comp_and, self._addr_zp0, 3),
            0x35: ("AND", self._comp_and, self._addr_zpx, 4),
            0x2D: ("AND", self._comp_and, self._addr_abs, 4),
            0x3D: ("AND", self._comp_and, self._addr_abx, 4),
            0x39: ("AND", self._comp_and, self._addr_aby, 4),
            0x21: ("AND", self._comp_and, self._addr_izx, 6),
            0x31: ("AND", self._comp_and, self._addr_izy, 5),
            0x0A: ("ASL", self._comp_asl, self._addr_imp, 2),
            0x06: ("ASL", self._comp_asl, self._addr_zp0, 5),
            0x16: ("ASL", self._comp_asl, self._addr_zpx, 6),
            0x0E: ("ASL", self._comp_asl, self._addr_abs, 6),
            0x1E: ("ASL", self._comp_asl, self._addr_abx, 7),
            0x90: ("BCC", self._comp_bcc, self._addr_rel, 2),
            0xB0: ("BCS", self._comp_bcs, self._addr_rel, 2),
            0xF0: ("BEQ", self._comp_beq, self._addr_rel, 2),
            0x24: ("BIT", self._comp_bit, self._addr_zp0, 3),
            0x2C: ("BIT", self._comp_bit, self._addr_abs, 4),
            0x30: ("BMI", self._comp_bmi, self._addr_rel, 2),
            0xD0: ("BNE", self._comp_bne, self._addr_rel, 2),
            0x10: ("BPL", self._comp_bpl, self._addr_rel, 2),
            0x00: ("BRK", self._comp_brk, self._addr_imp, 7),
            0x50: ("BVC", self._comp_bvc, self._addr_rel, 2),
            0x70: ("BVS", self._comp_bvs, self._addr_rel, 2),
            0x18: ("CLC", self._comp_clc, self._addr_imp, 2),
            0xD8: ("CLD", self._comp_cld, self._addr_imp, 2),
            0x58: ("CLI", self._comp_cli, self._addr_imp, 2),
            0xB8: ("CLV", self._comp_clv, self._addr_imp, 2),
            0xC9: ("CMP", self._comp_cmp, self._addr_imm, 2),
            0xC5: ("CMP", self._comp_cmp, self._addr_zp0, 3),
            0xD5: ("CMP", self._comp_cmp, self._addr_zpx, 4),
            0xCD: ("CMP", self._comp_cmp, self._addr_abs, 4),
            0xDD: ("CMP", self._comp_cmp, self._addr_abx, 4),
            0xD9: ("CMP", self._comp_cmp, self._addr_aby, 4),
            0xC1: ("CMP", self._comp_cmp, self._addr_izx, 6),
            0xD1: ("CMP", self._comp_cmp, self._addr_izy, 5),
            0xE0: ("CPX", self._comp_cpx, self._addr_imm, 2),
            0xE4: ("CPX", self._comp_cpx, self._addr_zp0, 3),
            0xEC: ("CPX", self._comp_cpx, self._addr_abs, 4),
            0xC0: ("CPY", self._comp_cpy, self._addr_imm, 2),
            0xC4: ("CPY", self._comp_cpy, self._addr_zp0, 3),
            0xCC: ("CPY", self._comp_cpy, self._addr_abs, 4),
            0xC6: ("DEC", self._comp_dec, self._addr_zp0, 5),
            0xD6: ("DEC", self._comp_dec, self._addr_zpx, 6),
            0xCE: ("DEC", self._comp_dec, self._addr_abs, 6),
            0xDE: ("DEC", self._comp_dec, self._addr_abx, 7),
            0xCA: ("DEX", self._comp_dex, self._addr_imp, 2),
            0x88: ("DEY", self._comp_dey, self._addr_imp, 2),
            0x49: ("EOR", self._comp_eor, self._addr_imm, 2),
            0x45: ("EOR", self._comp_eor, self._addr_zp0, 3),
            0x55: ("EOR", self._comp_eor, self._addr_zpx, 4),
            0x4D: ("EOR", self._comp_eor, self._addr_abs, 4),
            0x5D: ("EOR", self._comp_eor, self._addr_abx, 4),
            0x59: ("EOR", self._comp_eor, self._addr_aby, 4),
            0x41: ("EOR", self._comp_eor, self._addr_izx, 6),
            0x51: ("EOR", self._comp_eor, self._addr_izy, 5),
            0xE6: ("INC", self._comp_inc, self._addr_zp0, 5),
            0xF6: ("INC", self._comp_inc, self._addr_zpx, 6),
            0xEE: ("INC", self._comp_inc, self._addr_abs, 6),
            0xFE: ("INC", self._comp_inc, self._addr_abx, 7),
            0xE8: ("INX", self._comp_inx, self._addr_imp, 2),
            0xC8: ("INY", self._comp_iny, self._addr_imp, 2),
            0x4C: ("JMP", self._comp_jmp, self._addr_abs, 3),
            0x6C: ("JMP", self._comp_jmp, self._addr_ind, 5),
            0x20: ("JSR", self._comp_jsr, self._addr_abs, 6),
            0xA9: ("LDA", self._comp_lda, self._addr_imm, 2),
            0xA5: ("LDA", self._comp_lda, self._addr_zp0, 3),
            0xB5: ("LDA", self._comp_lda, self._addr_zpx, 4),
            0xAD: ("LDA", self._comp_lda, self._addr_abs, 4),
            0xBD: ("LDA", self._comp_lda, self._addr_abx, 4),
            0xB9: ("LDA", self._comp_lda, self._addr_aby, 4),
            0xA1: ("LDA", self._comp_lda, self._addr_izx, 6),
            0xB1: ("LDA", self._comp_lda, self._addr_izy, 5),
            0xA2: ("LDX", self._comp_ldx, self._addr_imm, 2),
            0xA6: ("LDX", self._comp_ldx, self._addr_zp0, 3),
            0xB6: ("LDX", self._comp_ldx, self._addr_zpy, 4),
            0xAE: ("LDX", self._comp_ldx, self._addr_abs, 4),
            0xBE: ("LDX", self._comp_ldx, self._addr_aby, 4),
            0xA0: ("LDY", self._comp_ldy, self._addr_imm, 2),
            0xA4: ("LDY", self._comp_ldy, self._addr_zp0, 3),
            0xB4: ("LDY", self._comp_ldy, self._addr_zpx, 4),
            0xAC: ("LDY", self._comp_ldy, self._addr_abs, 4),
            0xBC: ("LDY", self._comp_ldy, self._addr_abx, 4),
            0x4A: ("LSR", self._comp_lsr, self._addr_imp, 2),
            0x46: ("LSR", self._comp_lsr, self._addr_zp0, 5),
            0x56: ("LSR", self._comp_lsr, self._addr_zpx, 6),
            0x4E: ("LSR", self._comp_lsr, self._addr_abs, 6),
            0x5E: ("LSR", self._comp_lsr, self._addr_abx, 7),
            0xEA: ("NOP", self._comp_nop, self._addr_imp, 2),
            0x09: ("ORA", self._comp_ora, self._addr_imm, 2),
            0x05: ("ORA", self._comp_ora, self._addr_zp0, 3),
            0x15: ("ORA", self._comp_ora, self._addr_zpx, 4),
            0x0D: ("ORA", self._comp_ora, self._addr_abs, 4),
            0x1D: ("ORA", self._comp_ora, self._addr_abx, 4),
            0x19: ("ORA", self._comp_ora, self._addr_aby, 4),
            0x01: ("ORA", self._comp_ora, self._addr_izx, 6),
            0x11: ("ORA", self._comp_ora, self._addr_izy, 5),
            0x48: ("PHA", self._comp_pha, self._addr_imp, 3),
            0x08: ("PHP", self._comp_php, self._addr_imp, 3),
            0x68: ("PLA", self._comp_pla, self._addr_imp, 4),
            0x28: ("PLP", self._comp_plp, self._addr_imp, 4),
            0x2A: ("ROL", self._comp_rol, self._addr_imp, 2),
            0x26: ("ROL", self._comp_rol, self._addr_zp0, 5),
            0x36: ("ROL", self._comp_rol, self._addr_zpx, 6),
            0x2E: ("ROL", self._comp_rol, self._addr_abs, 6),
            0x3E: ("ROL", self._comp_rol, self._addr_abx, 7),
            0x6A: ("ROR", self._comp_ror, self._addr_imp, 2),
            0x66: ("ROR", self._comp_ror, self._addr_zp0, 5),
            0x76: ("ROR", self._comp_ror, self._addr_zpx, 6),
            0x6E: ("ROR", self._comp_ror, self._addr_abs, 6),
            0x7E: ("ROR", self._comp_ror, self._addr_abx, 7),
            0x40: ("RTI", self._comp_rti, self._addr_imp, 6),
            0x60: ("RTS", self._comp_rts, self._addr_imp, 6),
            0xE9: ("SBC", self._comp_sbc, self._addr_imm, 2),
            0xE5: ("SBC", self._comp_sbc, self._addr_zp0, 3),
            0xF5: ("SBC", self._comp_sbc, self._addr_zpx, 4),
            0xED: ("SBC", self._comp_sbc, self._addr_abs, 4),
            0xFD: ("SBC", self._comp_sbc, self._addr_abx, 4),
            0xF9: ("SBC", self._comp_sbc, self._addr_aby, 4),
            0xE1: ("SBC", self._comp_sbc, self._addr_izx, 6),
            0xF1: ("SBC", self._comp_sbc, self._addr_izy, 5),
            0x38: ("SEC", self._comp_sec, self._addr_imp, 2),
            0xF8: ("SED", self._comp_sed, self._addr_imp, 2),
            0x78: ("SEI", self._comp_sei, self._addr_imp, 2),
            0x85: ("STA", self._comp_sta, self._addr_zp0, 3),
            0x95: ("STA", self._comp_sta, self._addr_zpx, 4),
            0x8D: ("STA", self._comp_sta, self._addr_abs, 4),
            0x9D: ("STA", self._comp_sta, self._addr_abx, 5),
            0x99: ("STA", self._comp_sta, self._addr_aby, 5),
            0x81: ("STA", self._comp_sta, self._addr_izx, 6),
            0x91: ("STA", self._comp_sta, self._addr_izy, 6),
            0x86: ("STX", self._comp_stx, self._addr_zp0, 3),
            0x96: ("STX", self._comp_stx, self._addr_zpy, 4),
            0x8E: ("STX", self._comp_stx, self._addr_abs, 4),
            0x84: ("STY", self._comp_sty, self._addr_zp0, 3),
            0x94: ("STY", self._comp_sty, self._addr_zpx, 4),
            0x8C: ("STY", self._comp_sty, self._addr_abs, 4),
            0xAA: ("TAX", self._comp_tax, self._addr_imp, 2),
            0xA8: ("TAY", self._comp_tay, self._addr_imp, 2),
            0xBA: ("TSX", self._comp_tsx, self._addr_imp, 2),
            0x8A: ("TXA", self._comp_txa, self._addr_imp, 2),
            0x9A: ("TXS", self._comp_txs, self._addr_imp, 2),
            0x98: ("TYA", self._comp_tya, self._addr_imp, 2),
            0x1A: ("NOP", self._comp_nop, self._addr_imp, 2),
            0x3A: ("NOP", self._comp_nop, self._addr_imp, 2),
            0x5A: ("NOP", self._comp_nop, self._addr_imp, 2),
            0x7A: ("NOP", self._comp_nop, self._addr_imp, 2),
            0xDA: ("NOP", self._comp_nop, self._addr_imp, 2),
            0xFA: ("NOP", self._comp_nop, self._addr_imp, 2),
            0x80: ("NOP", self._comp_nop, self._addr_imm, 2),
            0x82: ("NOP", self._comp_nop, self._addr_imm, 2),
            0x89: ("NOP", self._comp_nop, self._addr_imm, 2),
            0xC2: ("NOP", self._comp_nop, self._addr_imm, 2),
            0xE2: ("NOP", self._comp_nop, self._addr_imm, 2),
            0x04: ("NOP", self._comp_nop, self._addr_zp0, 3),
            0x44: ("NOP", self._comp_nop, self._addr_zp0, 3),
            0x64: ("NOP", self._comp_nop, self._addr_zp0, 3),
            0x14: ("NOP", self._comp_nop, self._addr_zpx, 4),
            0x34: ("NOP", self._comp_nop, self._addr_zpx, 4),
            0x54: ("NOP", self._comp_nop, self._addr_zpx, 4),
            0x74: ("NOP", self._comp_nop, self._addr_zpx, 4),
            0xD4: ("NOP", self._comp_nop, self._addr_zpx, 4),
            0xF4: ("NOP", self._comp_nop, self._addr_zpx, 4),
            0x0C: ("NOP", self._comp_nop, self._addr_abs, 4),
            0x1C: ("NOP", self._comp_nop, self._addr_abx, 4),
            0x3C: ("NOP", self._comp_nop, self._addr_abx, 4),
            0x5C: ("NOP", self._comp_nop, self._addr_abx, 4),
            0x7C: ("NOP", self._comp_nop, self._addr_abx, 4),
            0xDC: ("NOP", self._comp_nop, self._addr_abx, 4),
            0xFC: ("NOP", self._comp_nop, self._addr_abx, 4),
            0xA3: ("LAX", self._comp_lax, self._addr_izx, 6),
            0xA7: ("LAX", self._comp_lax, self._addr_zp0, 3),
            0xAF: ("LAX", self._comp_lax, self._addr_abs, 4),
            0xB3: ("LAX", self._comp_lax, self._addr_izy, 5),
            0xB7: ("LAX", self._comp_lax, self._addr_zpy, 4),
            0xBF: ("LAX", self._comp_lax, self._addr_aby, 4),
            0xAB: ("LXA", self._comp_nop, self._addr_imm, 2),
            0x83: ("SAX", self._comp_sax, self._addr_izx, 6),
            0x87: ("SAX", self._comp_sax, self._addr_zp0, 3),
            0x8F: ("SAX", self._comp_sax, self._addr_abs, 4),
            0x97: ("SAX", self._comp_sax, self._addr_zpy, 4),
            0xCB: ("SBX", self._comp_nop, self._addr_imm, 2),
            0xEB: ("USBC", self._comp_sbc, self._addr_imm, 2),
            0xC3: ("DCP", self._comp_dcp, self._addr_izx, 8),
            0xC7: ("DCP", self._comp_dcp, self._addr_zp0, 5),
            0xCF: ("DCP", self._comp_dcp, self._addr_abs, 6),
            0xD3: ("DCP", self._comp_dcp, self._addr_izy, 8),
            0xD7: ("DCP", self._comp_dcp, self._addr_zpx, 6),
            0xDB: ("DCP", self._comp_dcp, self._addr_aby, 7),
            0xDF: ("DCP", self._comp_dcp, self._addr_abx, 7),
            0xE3: ("ISC", self._comp_isc, self._addr_izx, 8),
            0xE7: ("ISC", self._comp_isc, self._addr_zp0, 5),
            0xEF: ("ISC", self._comp_isc, self._addr_abs, 6),
            0xF3: ("ISC", self._comp_isc, self._addr_izy, 4),
            0xF7: ("ISC", self._comp_isc, self._addr_zpx, 6),
            0xFB: ("ISC", self._comp_isc, self._addr_aby, 7),
            0xFF: ("ISC", self._comp_isc, self._addr_abx, 7),
            0x03: ("SLO", self._comp_slo, self._addr_izx, 8),
            0x07: ("SLO", self._comp_slo, self._addr_zp0, 5),
            0x0F: ("SLO", self._comp_slo, self._addr_abs, 6),
            0x13: ("SLO", self._comp_slo, self._addr_izy, 8),
            0x17: ("SLO", self._comp_slo, self._addr_zpx, 6),
            0x1B: ("SLO", self._comp_slo, self._addr_aby, 7),
            0x1F: ("SLO", self._comp_slo, self._addr_abx, 7),
            0x0B: ("ANC", self._comp_nop, self._addr_imm, 2),
            0x2B: ("ANC", self._comp_nop, self._addr_imm, 2),
            0x23: ("RLA", self._comp_rla, self._addr_izx, 8),
            0x27: ("RLA", self._comp_rla, self._addr_zp0, 5),
            0x2F: ("RLA", self._comp_rla, self._addr_abs, 6),
            0x33: ("RLA", self._comp_rla, self._addr_izy, 8),
            0x37: ("RLA", self._comp_rla, self._addr_zpx, 6),
            0x3B: ("RLA", self._comp_rla, self._addr_aby, 7),
            0x3F: ("RLA", self._comp_rla, self._addr_abx, 7),
            0x43: ("SRE", self._comp_sre, self._addr_izx, 8),
            0x47: ("SRE", self._comp_sre, self._addr_zp0, 5),
            0x4F: ("SRE", self._comp_sre, self._addr_abs, 6),
            0x53: ("SRE", self._comp_sre, self._addr_izy, 8),
            0x57: ("SRE", self._comp_sre, self._addr_zpx, 6),
            0x5B: ("SRE", self._comp_sre, self._addr_aby, 7),
            0x5F: ("SRE", self._comp_sre, self._addr_abx, 7),
            0x63: ("RRA", self._comp_rra, self._addr_izx, 8),
            0x67: ("RRA", self._comp_rra, self._addr_zp0, 5),
            0x6F: ("RRA", self._comp_rra, self._addr_abs, 6),
            0x73: ("RRA", self._comp_rra, self._addr_izy, 8),
            0x77: ("RRA", self._comp_rra, self._addr_zpx, 6),
            0x7B: ("RRA", self._comp_rra, self._addr_aby, 7),
            0x7F: ("RRA", self._comp_rra, self._addr_abx, 7),
            0x02: ("JAM", self._comp_jam, self._addr_imp, 1),
            0x12: ("JAM", self._comp_jam, self._addr_imp, 1),
            0x22: ("JAM", self._comp_jam, self._addr_imp, 1),
            0x32: ("JAM", self._comp_jam, self._addr_imp, 1),
            0x42: ("JAM", self._comp_jam, self._addr_imp, 1),
            0x52: ("JAM", self._comp_jam, self._addr_imp, 0),
            0x62: ("JAM", self._comp_jam, self._addr_imp, 0),
            0x72: ("JAM", self._comp_jam, self._addr_imp, 0),
            0x82: ("JAM", self._comp_jam, self._addr_imp, 0),
            0x92: ("JAM", self._comp_jam, self._addr_imp, 0),
            0xB2: ("JAM", self._comp_jam, self._addr_imp, 0),
            0xC2: ("JAM", self._comp_jam, self._addr_imp, 0),
            0xD2: ("JAM", self._comp_jam, self._addr_imp, 0),
            0xE2: ("JAM", self._comp_jam, self._addr_imp, 0),
            0xF2: ("JAM", self._comp_jam, self._addr_imp, 0),
        }
        for op, data in lookup.items():
            self.opcode_table[op] = data

    def __repr__(self):
        op_data = self.opcode_table[self.opcode]
        op_name = op_data[0] if op_data else "???"
        return f'PC: {hex(self.pc).upper()}, OP: {op_name}, A: {self.a}, X: {self.x}, Y: {self.y}'

    def all_status_as_int(self) -> int:
        result = 0
        for f, v in self.status.items():
            if v > 0: result |= f
        return result

    def restore_all_status_from_int(self, status_int: int):
        for f in Status:
            self._set_status(f, (status_int & f) > 0)

    def connect(self, bus: Bus):
        self.bus = bus

    def read(self, addr: int):
        return self.bus.read(addr)

    def write(self, addr: int, data: int):
        self.bus.write(addr, data)

    def clock(self) -> int:
        if self.jammed: return 1
        
        self.opcode = self.bus.read(self.pc)
        if self.on_opcode_loaded: self.on_opcode_loaded()
        self.pc += 1
        
        entry = self.opcode_table[self.opcode]
        if entry is None:
            self.jammed = True
            return 1
            
        name, comp, addr, cycles = entry
        # addr() and comp() return 1 if an extra cycle might be needed (e.g. page cross)
        extra1 = addr()
        extra2 = comp()
        
        total_cycles = cycles + (extra1 & extra2)
        return total_cycles

    def fetch(self):
        entry = self.opcode_table[self.opcode]
        if entry and entry[2] != self._addr_imp:
            self.fetched = self.bus.read(self.abs_addr)
        return self.fetched

    def reset(self):
        self.a = 0
        self.x = 0
        self.y = 0
        self.stkp = 0xFD
        for s in self.status: self._set_status(s, False)
        self._set_status(Status.U, True)
        self._set_status(Status.I, True)
        self.abs_addr = 0xFFFC
        lo = self.read(self.abs_addr)
        hi = self.read(self.abs_addr + 1)
        self.pc = (hi << 8) | lo
        self.rel_addr = 0
        self.abs_addr = 0
        self.fetched = 0
        self.cycle = 0
        self.jammed = False

    def _interupt_if(self, cond, dst_addr, num_cycles):
        if cond is True:
            self._push_to_stack((self.pc >> 8) & 0x00FF)
            self._push_to_stack(self.pc & 0x00FF)
            self._set_status(Status.B, False)
            self._set_status(Status.U, True)
            self._set_status(Status.I, True)
            self._push_to_stack(self.all_status_as_int())
            self.abs_addr = dst_addr
            lo, hi = self.read(self.abs_addr), self.read(self.abs_addr+1)
            self.pc = (hi << 8) | lo
            self.cycle = num_cycles

    def _push_to_stack(self, data):
        self.write(0x0100 + self.stkp, data)
        self.stkp -= 1

    def _pop_from_stack(self):
        self.stkp += 1
        return self.read(0x0100 + self.stkp)

    def irq(self):
        self._interupt_if(self._get_status(Status.I) is True, 0xFFFE, 7)

    def nmi(self):
        self._interupt_if(True, 0xFFFA, 8)

    def _branch_if(self, cond: bool):
        if cond is True:
            self.cycle += 1
            self.abs_addr = (self.pc + self.rel_addr) & 0xFFFF
            if (self.abs_addr & 0xFF00) != (self.pc & 0xFF00): self.cycle += 1
            self.pc = self.abs_addr
        return 0

    def _get_status(self, flag: Status):
        return self.status[flag] != 0

    def _set_status(self, flag: Status, enabled: bool):
        self.status[flag] = 1 if enabled else 0

    def _comp_adc(self):
        self.fetch()
        added = self.a + self.fetched + self.status[Status.C]
        self._set_status(Status.C, added > 255)
        self._set_status(Status.Z, (added & 0x00FF) == 0)
        self._set_status(Status.V, ((~self.a ^ self.fetched) & (self.a ^ added) & 0x0080) > 0)
        self._set_status(Status.N, added & 0x80)
        self.a = added & 0x00FF
        return 1

    def _comp_sbc(self):
        self.fetch()
        value = self.fetched ^ 0x00FF
        added = self.a + value + self.status[Status.C]
        self._set_status(Status.C, added > 255)
        self._set_status(Status.Z, (added & 0x00FF) == 0)
        self._set_status(Status.V, ((~self.a ^ value) & (self.a ^ added) & 0x0080) > 0)
        self._set_status(Status.N, added & 0x80)
        self.a = added & 0x00FF
        return 1

    def _comp_dcp(self):
        self._comp_dec()
        return self._comp_cmp()

    def _comp_isc(self):
        self._comp_inc()
        return self._comp_sbc()

    def _comp_slo(self):
        self._comp_asl()
        return self._comp_ora()

    def _comp_rla(self):
        self._comp_rol()
        return self._comp_and()

    def _comp_sre(self):
        self._comp_lsr()
        return self._comp_eor()

    def _comp_rra(self):
        self._comp_ror()
        return self._comp_adc()

    def _comp_and(self):
        self.fetch()
        self.a &= self.fetched
        self._set_status(Status.Z, self.a == 0)
        self._set_status(Status.N, self.a & 0x80)
        return 1

    def _comp_asl(self):
        self.fetch()
        new_val = self.fetched << 1
        self._set_status(Status.C, (new_val & 0xFF00) > 0)
        self._set_status(Status.Z, (new_val & 0x00FF) == 0)
        self._set_status(Status.N, (new_val & 0x80) > 0)
        if self.opcode_table[self.opcode][2] == self._addr_imp:
            self.a = new_val & 0x00FF
        else:
            self.write(self.abs_addr, new_val & 0x00FF)
        return 0

    def _comp_bcc(self): return self._branch_if(self._get_status(Status.C) is False)
    def _comp_bcs(self): return self._branch_if(self._get_status(Status.C) is True)
    def _comp_beq(self): return self._branch_if(self._get_status(Status.Z) is True)

    def _comp_bit(self):
        self.fetch()
        new_val = self.a & self.fetched
        self._set_status(Status.Z, (new_val & 0x00FF) == 0)
        self._set_status(Status.N, self.fetched & (1 << 7))
        self._set_status(Status.V, self.fetched & (1 << 6))
        return 0

    def _comp_bmi(self): return self._branch_if(self._get_status(Status.N) is True)
    def _comp_bne(self): return self._branch_if(self._get_status(Status.Z) is False)
    def _comp_bpl(self): return self._branch_if(self._get_status(Status.N) is False)

    def _comp_brk(self):
        self.pc += 1
        self._push_to_stack((self.pc >> 8) & 0x00FF)
        self._push_to_stack(self.pc & 0x00FF)
        self._set_status(Status.B, True)
        self._push_to_stack(self.all_status_as_int())
        self._set_status(Status.B, False)
        lo = self.read(0xFFFE)
        hi = self.read(0xFFFF)
        self.pc = (hi << 8) | lo
        return 0

    def _comp_bvc(self): return self._branch_if(self._get_status(Status.V) is False)
    def _comp_bvs(self): return self._branch_if(self._get_status(Status.V) is True)

    def _comp_clc(self): self._set_status(Status.C, False); return 0
    def _comp_cld(self): self._set_status(Status.D, False); return 0
    def _comp_cli(self): self._set_status(Status.I, False); return 0
    def _comp_clv(self): self._set_status(Status.V, False); return 0

    def _comp_cmp(self):
        self.fetch()
        val = self.a - self.fetched
        self._set_status(Status.C, self.a >= self.fetched)
        self._set_status(Status.Z, (val & 0x00FF) == 0)
        self._set_status(Status.N, (val & 0x80) > 0)
        return 0

    def _comp_cpx(self):
        self.fetch()
        val = self.x - self.fetched
        self._set_status(Status.C, self.x >= self.fetched)
        self._set_status(Status.Z, (val & 0x00FF) == 0)
        self._set_status(Status.N, (val & 0x80) > 0)
        return 0

    def _comp_cpy(self):
        self.fetch()
        val = self.y - self.fetched
        self._set_status(Status.C, self.y >= self.fetched)
        self._set_status(Status.Z, (val & 0x00FF) == 0)
        self._set_status(Status.N, (val & 0x80) > 0)
        return 0

    def _comp_dec(self):
        self.fetch()
        val = self.fetched - 1
        self._set_status(Status.Z, (val & 0x00FF) == 0)
        self._set_status(Status.N, (val & 0x0080) > 0)
        self.write(self.abs_addr, val & 0x00FF)
        return 0

    def _comp_dex(self):
        self.x -= 1
        self.x &= 0xFF
        self._set_status(Status.Z, (self.x & 0x00FF) == 0)
        self._set_status(Status.N, (self.x & 0x0080) > 0)
        return 0

    def _comp_dey(self):
        self.y -= 1
        self.y &= 0xFF
        self._set_status(Status.Z, (self.y & 0x00FF) == 0)
        self._set_status(Status.N, (self.y & 0x0080) > 0)
        return 0

    def _comp_eor(self):
        self.fetch()
        self.a = self.a ^ self.fetched
        self._set_status(Status.Z, (self.a & 0x00FF) == 0)
        self._set_status(Status.N, (self.a & 0x0080) > 0)
        return 1

    def _comp_inc(self):
        self.fetch()
        val = ((self.fetched + 1) & 0x00FF)
        self._set_status(Status.Z, (val & 0x00FF) == 0)
        self._set_status(Status.N, (val & 0x0080) > 0)
        self.write(self.abs_addr, val)
        return 0

    def _comp_inx(self):
        self.x += 1
        self._set_status(Status.Z, (self.x & 0x00FF) == 0)
        self._set_status(Status.N, (self.x & 0x0080) > 0)
        return 0

    def _comp_iny(self):
        self.y += 1
        self._set_status(Status.Z, (self.y & 0x00FF) == 0)
        self._set_status(Status.N, (self.y & 0x0080) > 0)
        return 0

    def _comp_jmp(self): self.pc = self.abs_addr; return 0
    def _comp_jsr(self):
        self.pc -= 1
        self._push_to_stack((self.pc >> 8) & 0x00FF)
        self._push_to_stack(self.pc & 0x00FF)
        self.pc = self.abs_addr
        return 0

    def _comp_lda(self):
        self.fetch()
        self.a = self.fetched
        self._set_status(Status.Z, self.a == 0)
        self._set_status(Status.N, (self.a & 0x0080) > 0)
        return 1

    def _comp_ldx(self):
        self.fetch()
        self.x = self.fetched
        self._set_status(Status.Z, self.x == 0)
        self._set_status(Status.N, (self.x & 0x0080) > 0)
        return 1

    def _comp_ldy(self):
        self.fetch()
        self.y = self.fetched
        self._set_status(Status.Z, self.y == 0)
        self._set_status(Status.N, (self.y & 0x0080) > 0)
        return 1

    def _comp_lsr(self):
        self.fetch()
        carry_flag = (self.fetched & 0x01) > 0
        new_val = self.fetched >> 1
        self._set_status(Status.C, carry_flag)
        self._set_status(Status.Z, (new_val & 0x00FF) == 0)
        self._set_status(Status.N, (new_val & 0x80) > 0)
        if self.opcode_table[self.opcode][2] == self._addr_imp: self.a = (new_val & 0xFF)
        else: self.write(self.abs_addr, new_val)
        return 0

    def _comp_jam(self): self.jammed = True; return 0
    def _comp_nop(self): return 0

    def _comp_ora(self):
        self.fetch()
        self.a |= self.fetched
        self._set_status(Status.Z, (self.a & 0xFF) == 0)
        self._set_status(Status.N, (self.a & 0x80) > 0)
        return 0

    def _comp_pha(self): self._push_to_stack(self.a); return 0
    def _comp_php(self):
        status_int = self.all_status_as_int()
        status_int |= Status.U
        status_int |= Status.B
        self._push_to_stack(status_int)
        self._set_status(Status.U, True)
        self._set_status(Status.B, False)
        return 0

    def _comp_pla(self):
        self.a = self._pop_from_stack()
        self._set_status(Status.Z, (self.a & 0xFF) == 0)
        self._set_status(Status.N, (self.a & 0x80) > 0)
        return 0

    def _comp_plp(self):
        status_int = self._pop_from_stack()
        current_b = self._get_status(Status.B)
        self.restore_all_status_from_int(status_int)
        self._set_status(Status.U, True)
        self._set_status(Status.B, current_b)
        return 0

    def _comp_rol(self):
        self.fetch()
        old_carry_flag = self.status[Status.C]
        self.fetched = (self.fetched << 1) | (old_carry_flag)
        self._set_status(Status.C, (self.fetched & 0xFF00) > 0)
        self._set_status(Status.Z, (self.fetched & 0xFF) == 0)
        self._set_status(Status.N, (self.fetched & 0x80) > 0)
        if self.opcode_table[self.opcode][2] == self._addr_imp: self.a = (self.fetched & 0xFF)
        else: self.write(self.abs_addr, (self.fetched & 0xFF))
        return 0

    def _comp_ror(self):
        self.fetch()
        old_carry_flag = self.status[Status.C]
        old_val = self.fetched
        self.fetched = ((self.fetched >> 1) & 0xFF) | (int(old_carry_flag) << 7)
        self._set_status(Status.C, (old_val & 0x01) > 0)
        self._set_status(Status.Z, (self.fetched & 0xFF) == 0)
        self._set_status(Status.N, (self.fetched & 0x80) > 0)
        if self.opcode_table[self.opcode][2] == self._addr_imp: self.a = self.fetched
        else: self.write(self.abs_addr, self.fetched)
        return 0

    def _comp_rti(self):
        status_int = self._pop_from_stack()
        status_int &= ~Status.B
        status_int |= Status.U
        self.restore_all_status_from_int(status_int)
        self.pc = self._pop_from_stack()
        self.pc |= (self._pop_from_stack() << 8)
        return 0

    def _comp_rts(self):
        lo = self._pop_from_stack()
        hi = self._pop_from_stack()
        self.pc = (hi << 8) | lo
        self.pc += 1
        return 0

    def _comp_sec(self): self._set_status(Status.C, True); return 0
    def _comp_sed(self): self._set_status(Status.D, True); return 0
    def _comp_sei(self): self._set_status(Status.I, True); return 0

    def _comp_sta(self): self.write(self.abs_addr, self.a); return 0
    def _comp_stx(self): self.write(self.abs_addr, self.x); return 0
    def _comp_sty(self): self.write(self.abs_addr, self.y); return 0

    def _comp_tax(self):
        self.x = self.a
        self._set_status(Status.Z, (self.x & 0xFF) == 0)
        self._set_status(Status.N, (self.x & 0x80) > 0)
        return 0

    def _comp_tay(self):
        self.y = self.a
        self._set_status(Status.Z, (self.y & 0xFF) == 0)
        self._set_status(Status.N, (self.y & 0x80) > 0)
        return 0

    def _comp_tsx(self):
        self.x = self.stkp
        self._set_status(Status.Z, self.x == 0)
        self._set_status(Status.N, (self.x & 0x80) > 0)
        return 0

    def _comp_txa(self):
        self.a = self.x
        self._set_status(Status.Z, self.a == 0)
        self._set_status(Status.N, (self.a & 0x80) > 0)
        return 0

    def _comp_txs(self): self.stkp = self.x; return 0
    def _comp_tya(self):
        self.a = self.y
        self._set_status(Status.Z, self.a == 0)
        self._set_status(Status.N, (self.a & 0x80) > 0)
        return 0

    def _comp_lax(self): self._comp_lda(); return self._comp_ldx()
    def _comp_sax(self): m = self.x & self.a; self.write(self.abs_addr, m); return 0

    def _addr_imp(self): self.fetched = self.a; return 0
    def _addr_imm(self): self.abs_addr = self.pc; self.pc += 1; return 0
    def _addr_zp0(self): self.abs_addr = self.read(self.pc) & 0x00FF; self.pc += 1; return 0
    def _addr_zpx(self): self.abs_addr = (self.read(self.pc) + self.x) & 0x00FF; self.pc += 1; return 0
    def _addr_zpy(self): self.abs_addr = (self.read(self.pc) + self.y) & 0x00FF; self.pc += 1; return 0
    def _addr_rel(self):
        self.rel_addr = self.read(self.pc); self.pc += 1
        if self.rel_addr & 0x80: self.rel_addr |= 0xFF00
        return 0
    def _addr_abs(self):
        lo, hi = self.read(self.pc), self.read(self.pc+1)
        self.pc += 2; self.abs_addr = (hi << 8) | lo; return 0
    def _addr_abx(self):
        lo, hi = self.read(self.pc), self.read(self.pc+1)
        self.pc += 2; self.abs_addr = ((hi << 8) | lo) + self.x; self.abs_addr &= 0xFFFF
        return 1 if (self.abs_addr & 0xFF00) != (hi << 8) else 0
    def _addr_aby(self):
        lo, hi = self.read(self.pc), self.read(self.pc+1)
        self.pc += 2; self.abs_addr = ((hi << 8) | lo) + self.y; self.abs_addr &= 0xFFFF
        return 1 if (self.abs_addr & 0xFF00) != (hi << 8) else 0
    def _addr_ind(self):
        ptr_lo, ptr_hi = self.read(self.pc), self.read(self.pc+1); self.pc += 2
        ptr = (ptr_hi << 8) | ptr_lo
        if ptr_lo == 0x00FF: self.abs_addr = (self.read(ptr & 0xFF00) << 8) | self.read(ptr)
        else: self.abs_addr = (self.read(ptr+1) << 8) | self.read(ptr)
        return 0
    def _addr_izx(self):
        ptr = self.read(self.pc); self.pc += 1
        lo, hi = self.read((ptr + self.x) & 0x00FF), self.read((ptr + self.x + 1) & 0x00FF)
        self.abs_addr = (hi << 8) | lo; return 0
    def _addr_izy(self):
        ptr = self.read(self.pc); self.pc += 1
        lo, hi = self.read(ptr & 0x00FF), self.read((ptr + 1) & 0x00FF)
        self.abs_addr = ((hi << 8) | lo) + self.y; self.abs_addr &= 0xFFFF
        return 1 if (self.abs_addr & 0xFF00) != (hi << 8) else 0
