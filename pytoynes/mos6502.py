from enum import IntEnum
from typing import Callable
from .bus import Bus

class Instruction:
    def __init__(self,
                 name: str,
                 compute: Callable,
                 address: Callable,
                 num_cycles: int):
        self.name = name
        self.compute = compute
        self.address = address
        self.num_cycles = num_cycles


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
        self.bus = None
        self.cycle = 0
        self.pc = 0
        self.stkp = 0x00FD
        self.a = 0
        self.x = 0
        self.y = 0
        self.fetched = None
        self.abs_addr = 0
        self.rel_addr = 0
        self.opcode = None
        self.status = {s: 0 for s in Status}
        self._set_status(Status.U, True)
        self._set_status(Status.I, True)
        self.jammed = False
        self.on_opcode_loaded = None
        self.opcode_to_instruction = {
            0x69: Instruction("ADC", self._comp_adc, self._addr_imm, 2),
            0x65: Instruction("ADC", self._comp_adc, self._addr_zp0, 3),
            0x75: Instruction("ADC", self._comp_adc, self._addr_zpx, 4),
            0x6D: Instruction("ADC", self._comp_adc, self._addr_abs, 4),
            0x7D: Instruction("ADC", self._comp_adc, self._addr_abx, 4),
            0x79: Instruction("ADC", self._comp_adc, self._addr_aby, 4),
            0x61: Instruction("ADC", self._comp_adc, self._addr_izx, 6),
            0x71: Instruction("ADC", self._comp_adc, self._addr_izy, 5),
            0x29: Instruction("AND", self._comp_and, self._addr_imm, 2),
            0x25: Instruction("AND", self._comp_and, self._addr_zp0, 3),
            0x35: Instruction("AND", self._comp_and, self._addr_zpx, 4),
            0x2D: Instruction("AND", self._comp_and, self._addr_abs, 4),
            0x3D: Instruction("AND", self._comp_and, self._addr_abx, 4),
            0x39: Instruction("AND", self._comp_and, self._addr_aby, 4),
            0x21: Instruction("AND", self._comp_and, self._addr_izx, 6),
            0x31: Instruction("AND", self._comp_and, self._addr_izy, 5),
            0x0A: Instruction("ASL", self._comp_asl, self._addr_imp, 2),
            0x06: Instruction("ASL", self._comp_asl, self._addr_zp0, 5),
            0x16: Instruction("ASL", self._comp_asl, self._addr_zpx, 6),
            0x0E: Instruction("ASL", self._comp_asl, self._addr_abs, 6),
            0x1E: Instruction("ASL", self._comp_asl, self._addr_abx, 7),
            0x90: Instruction("BCC", self._comp_bcc, self._addr_rel, 2),
            0xB0: Instruction("BCS", self._comp_bcs, self._addr_rel, 2),
            0xF0: Instruction("BEQ", self._comp_beq, self._addr_rel, 2),
            0x24: Instruction("BIT", self._comp_bit, self._addr_zp0, 3),
            0x2C: Instruction("BIT", self._comp_bit, self._addr_abs, 4),
            0x30: Instruction("BMI", self._comp_bmi, self._addr_rel, 2),
            0xD0: Instruction("BNE", self._comp_bne, self._addr_rel, 2),
            0x10: Instruction("BPL", self._comp_bpl, self._addr_rel, 2),
            0x00: Instruction("BRK", self._comp_brk, self._addr_imp, 7),
            0x50: Instruction("BVC", self._comp_bvc, self._addr_rel, 2),
            0x70: Instruction("BVS", self._comp_bvs, self._addr_rel, 2),
            0x18: Instruction("CLC", self._comp_clc, self._addr_imp, 2),
            0xD8: Instruction("CLD", self._comp_cld, self._addr_imp, 2),
            0x58: Instruction("CLI", self._comp_cli, self._addr_imp, 2),
            0xB8: Instruction("CLV", self._comp_clv, self._addr_imp, 2),
            0xC9: Instruction("CMP", self._comp_cmp, self._addr_imm, 2),
            0xC5: Instruction("CMP", self._comp_cmp, self._addr_zp0, 3),
            0xD5: Instruction("CMP", self._comp_cmp, self._addr_zpx, 4),
            0xCD: Instruction("CMP", self._comp_cmp, self._addr_abs, 4),
            0xDD: Instruction("CMP", self._comp_cmp, self._addr_abx, 4),
            0xD9: Instruction("CMP", self._comp_cmp, self._addr_aby, 4),
            0xC1: Instruction("CMP", self._comp_cmp, self._addr_izx, 6),
            0xD1: Instruction("CMP", self._comp_cmp, self._addr_izy, 5),
            0xE0: Instruction("CPX", self._comp_cpx, self._addr_imm, 2),
            0xE4: Instruction("CPX", self._comp_cpx, self._addr_zp0, 3),
            0xEC: Instruction("CPX", self._comp_cpx, self._addr_abs, 4),
            0xC0: Instruction("CPY", self._comp_cpy, self._addr_imm, 2),
            0xC4: Instruction("CPY", self._comp_cpy, self._addr_zp0, 3),
            0xCC: Instruction("CPY", self._comp_cpy, self._addr_abs, 4),
            0xC6: Instruction("DEC", self._comp_dec, self._addr_zp0, 5),
            0xD6: Instruction("DEC", self._comp_dec, self._addr_zpx, 6),
            0xCE: Instruction("DEC", self._comp_dec, self._addr_abs, 6),
            0xDE: Instruction("DEC", self._comp_dec, self._addr_abx, 7),
            0xCA: Instruction("DEX", self._comp_dex, self._addr_imp, 2),
            0x88: Instruction("DEY", self._comp_dey, self._addr_imp, 2),
            0x49: Instruction("EOR", self._comp_eor, self._addr_imm, 2),
            0x45: Instruction("EOR", self._comp_eor, self._addr_zp0, 3),
            0x55: Instruction("EOR", self._comp_eor, self._addr_zpx, 4),
            0x4D: Instruction("EOR", self._comp_eor, self._addr_abs, 4),
            0x5D: Instruction("EOR", self._comp_eor, self._addr_abx, 4),
            0x59: Instruction("EOR", self._comp_eor, self._addr_aby, 4),
            0x41: Instruction("EOR", self._comp_eor, self._addr_izx, 6),
            0x51: Instruction("EOR", self._comp_eor, self._addr_izy, 5),
            0xE6: Instruction("INC", self._comp_inc, self._addr_zp0, 5),
            0xF6: Instruction("INC", self._comp_inc, self._addr_zpx, 6),
            0xEE: Instruction("INC", self._comp_inc, self._addr_abs, 6),
            0xFE: Instruction("INC", self._comp_inc, self._addr_abx, 7),
            0xE8: Instruction("INX", self._comp_inx, self._addr_imp, 2),
            0xC8: Instruction("INY", self._comp_iny, self._addr_imp, 2),
            0x4C: Instruction("JMP", self._comp_jmp, self._addr_abs, 3),
            0x6C: Instruction("JMP", self._comp_jmp, self._addr_ind, 5),
            0x20: Instruction("JSR", self._comp_jsr, self._addr_abs, 6),
            0xA9: Instruction("LDA", self._comp_lda, self._addr_imm, 2),
            0xA5: Instruction("LDA", self._comp_lda, self._addr_zp0, 3),
            0xB5: Instruction("LDA", self._comp_lda, self._addr_zpx, 4),
            0xAD: Instruction("LDA", self._comp_lda, self._addr_abs, 4),
            0xBD: Instruction("LDA", self._comp_lda, self._addr_abx, 4),
            0xB9: Instruction("LDA", self._comp_lda, self._addr_aby, 4),
            0xA1: Instruction("LDA", self._comp_lda, self._addr_izx, 6),
            0xB1: Instruction("LDA", self._comp_lda, self._addr_izy, 5),
            0xA2: Instruction("LDX", self._comp_ldx, self._addr_imm, 2),
            0xA6: Instruction("LDX", self._comp_ldx, self._addr_zp0, 3),
            0xB6: Instruction("LDX", self._comp_ldx, self._addr_zpy, 4),
            0xAE: Instruction("LDX", self._comp_ldx, self._addr_abs, 4),
            0xBE: Instruction("LDX", self._comp_ldx, self._addr_aby, 4),
            0xA0: Instruction("LDY", self._comp_ldy, self._addr_imm, 2),
            0xA4: Instruction("LDY", self._comp_ldy, self._addr_zp0, 3),
            0xB4: Instruction("LDY", self._comp_ldy, self._addr_zpx, 4),
            0xAC: Instruction("LDY", self._comp_ldy, self._addr_abs, 4),
            0xBC: Instruction("LDY", self._comp_ldy, self._addr_abx, 4),
            0x4A: Instruction("LSR", self._comp_lsr, self._addr_imp, 2),
            0x46: Instruction("LSR", self._comp_lsr, self._addr_zp0, 5),
            0x56: Instruction("LSR", self._comp_lsr, self._addr_zpx, 6),
            0x4E: Instruction("LSR", self._comp_lsr, self._addr_abs, 6),
            0x5E: Instruction("LSR", self._comp_lsr, self._addr_abx, 7),
            0xEA: Instruction("NOP", self._comp_nop, self._addr_imp, 2),
            0x09: Instruction("ORA", self._comp_ora, self._addr_imm, 2),
            0x05: Instruction("ORA", self._comp_ora, self._addr_zp0, 3),
            0x15: Instruction("ORA", self._comp_ora, self._addr_zpx, 4),
            0x0D: Instruction("ORA", self._comp_ora, self._addr_abs, 4),
            0x1D: Instruction("ORA", self._comp_ora, self._addr_abx, 4),
            0x19: Instruction("ORA", self._comp_ora, self._addr_aby, 4),
            0x01: Instruction("ORA", self._comp_ora, self._addr_izx, 6),
            0x11: Instruction("ORA", self._comp_ora, self._addr_izy, 5),
            0x48: Instruction("PHA", self._comp_pha, self._addr_imp, 3),
            0x08: Instruction("PHP", self._comp_php, self._addr_imp, 3),
            0x68: Instruction("PLA", self._comp_pla, self._addr_imp, 4),
            0x28: Instruction("PLP", self._comp_plp, self._addr_imp, 4),
            0x2A: Instruction("ROL", self._comp_rol, self._addr_imp, 2),
            0x26: Instruction("ROL", self._comp_rol, self._addr_zp0, 5),
            0x36: Instruction("ROL", self._comp_rol, self._addr_zpx, 6),
            0x2E: Instruction("ROL", self._comp_rol, self._addr_abs, 6),
            0x3E: Instruction("ROL", self._comp_rol, self._addr_abx, 7),
            0x6A: Instruction("ROR", self._comp_ror, self._addr_imp, 2),
            0x66: Instruction("ROR", self._comp_ror, self._addr_zp0, 5),
            0x76: Instruction("ROR", self._comp_ror, self._addr_zpx, 6),
            0x6E: Instruction("ROR", self._comp_ror, self._addr_abs, 6),
            0x7E: Instruction("ROR", self._comp_ror, self._addr_abx, 7),
            0x40: Instruction("RTI", self._comp_rti, self._addr_imp, 6),
            0x60: Instruction("RTS", self._comp_rts, self._addr_imp, 6),
            0xE9: Instruction("SBC", self._comp_sbc, self._addr_imm, 2),
            0xE5: Instruction("SBC", self._comp_sbc, self._addr_zp0, 3),
            0xF5: Instruction("SBC", self._comp_sbc, self._addr_zpx, 4),
            0xED: Instruction("SBC", self._comp_sbc, self._addr_abs, 4),
            0xFD: Instruction("SBC", self._comp_sbc, self._addr_abx, 4),
            0xF9: Instruction("SBC", self._comp_sbc, self._addr_aby, 4),
            0xE1: Instruction("SBC", self._comp_sbc, self._addr_izx, 6),
            0xF1: Instruction("SBC", self._comp_sbc, self._addr_izy, 5),
            0x38: Instruction("SEC", self._comp_sec, self._addr_imp, 2),
            0xF8: Instruction("SED", self._comp_sed, self._addr_imp, 2),
            0x78: Instruction("SEI", self._comp_sei, self._addr_imp, 2),
            0x85: Instruction("STA", self._comp_sta, self._addr_zp0, 3),
            0x95: Instruction("STA", self._comp_sta, self._addr_zpx, 4),
            0x8D: Instruction("STA", self._comp_sta, self._addr_abs, 4),
            0x9D: Instruction("STA", self._comp_sta, self._addr_abx, 5),
            0x99: Instruction("STA", self._comp_sta, self._addr_aby, 5),
            0x81: Instruction("STA", self._comp_sta, self._addr_izx, 6),
            0x91: Instruction("STA", self._comp_sta, self._addr_izy, 6),
            0x86: Instruction("STX", self._comp_stx, self._addr_zp0, 3),
            0x96: Instruction("STX", self._comp_stx, self._addr_zpy, 4),
            0x8E: Instruction("STX", self._comp_stx, self._addr_abs, 4),
            0x84: Instruction("STY", self._comp_sty, self._addr_zp0, 3),
            0x94: Instruction("STY", self._comp_sty, self._addr_zpx, 4),
            0x8C: Instruction("STY", self._comp_sty, self._addr_abs, 4),
            0xAA: Instruction("TAX", self._comp_tax, self._addr_imp, 2),
            0xA8: Instruction("TAY", self._comp_tay, self._addr_imp, 2),
            0xBA: Instruction("TSX", self._comp_tsx, self._addr_imp, 2),
            0x8A: Instruction("TXA", self._comp_txa, self._addr_imp, 2),
            0x9A: Instruction("TXS", self._comp_txs, self._addr_imp, 2),
            0x98: Instruction("TYA", self._comp_tya, self._addr_imp, 2),
            0x1A: Instruction("NOP", self._comp_nop, self._addr_imp, 2),
            0x3A: Instruction("NOP", self._comp_nop, self._addr_imp, 2),
            0x5A: Instruction("NOP", self._comp_nop, self._addr_imp, 2),
            0x7A: Instruction("NOP", self._comp_nop, self._addr_imp, 2),
            0xDA: Instruction("NOP", self._comp_nop, self._addr_imp, 2),
            0xFA: Instruction("NOP", self._comp_nop, self._addr_imp, 2),
            0x80: Instruction("NOP", self._comp_nop, self._addr_imm, 2),
            0x82: Instruction("NOP", self._comp_nop, self._addr_imm, 2),
            0x89: Instruction("NOP", self._comp_nop, self._addr_imm, 2),
            0xC2: Instruction("NOP", self._comp_nop, self._addr_imm, 2),
            0xE2: Instruction("NOP", self._comp_nop, self._addr_imm, 2),
            0x04: Instruction("NOP", self._comp_nop, self._addr_zp0, 3),
            0x44: Instruction("NOP", self._comp_nop, self._addr_zp0, 3),
            0x64: Instruction("NOP", self._comp_nop, self._addr_zp0, 3),
            0x14: Instruction("NOP", self._comp_nop, self._addr_zpx, 4),
            0x34: Instruction("NOP", self._comp_nop, self._addr_zpx, 4),
            0x54: Instruction("NOP", self._comp_nop, self._addr_zpx, 4),
            0x74: Instruction("NOP", self._comp_nop, self._addr_zpx, 4),
            0xD4: Instruction("NOP", self._comp_nop, self._addr_zpx, 4),
            0xF4: Instruction("NOP", self._comp_nop, self._addr_zpx, 4),
            0x0C: Instruction("NOP", self._comp_nop, self._addr_abs, 4),
            0x1C: Instruction("NOP", self._comp_nop, self._addr_abx, 4),
            0x3C: Instruction("NOP", self._comp_nop, self._addr_abx, 4),
            0x5C: Instruction("NOP", self._comp_nop, self._addr_abx, 4),
            0x7C: Instruction("NOP", self._comp_nop, self._addr_abx, 4),
            0xDC: Instruction("NOP", self._comp_nop, self._addr_abx, 4),
            0xFC: Instruction("NOP", self._comp_nop, self._addr_abx, 4),
            0xA3: Instruction("LAX", self._comp_lax, self._addr_izx, 6),
            0xA7: Instruction("LAX", self._comp_lax, self._addr_zp0, 3),
            0xAF: Instruction("LAX", self._comp_lax, self._addr_abs, 4),
            0xB3: Instruction("LAX", self._comp_lax, self._addr_izy, 5),
            0xB7: Instruction("LAX", self._comp_lax, self._addr_zpy, 4),
            0xBF: Instruction("LAX", self._comp_lax, self._addr_aby, 4),
            0xAB: Instruction("LXA", self._comp_nop, self._addr_imm, 2),
            0x83: Instruction("SAX", self._comp_sax, self._addr_izx, 6),
            0x87: Instruction("SAX", self._comp_sax, self._addr_zp0, 3),
            0x8F: Instruction("SAX", self._comp_sax, self._addr_abs, 4),
            0x97: Instruction("SAX", self._comp_sax, self._addr_zpy, 4),
            0xCB: Instruction("SBX", self._comp_nop, self._addr_imm, 2),
            0xEB: Instruction("USBC", self._comp_sbc, self._addr_imm, 2),
            0xC3: Instruction("DCP", self._comp_dcp, self._addr_izx, 8),
            0xC7: Instruction("DCP", self._comp_dcp, self._addr_zp0, 5),
            0xCF: Instruction("DCP", self._comp_dcp, self._addr_abs, 6),
            0xD3: Instruction("DCP", self._comp_dcp, self._addr_izy, 8),
            0xD7: Instruction("DCP", self._comp_dcp, self._addr_zpx, 6),
            0xDB: Instruction("DCP", self._comp_dcp, self._addr_aby, 7),
            0xDF: Instruction("DCP", self._comp_dcp, self._addr_abx, 7),
            0xE3: Instruction("ISC", self._comp_isc, self._addr_izx, 8),
            0xE7: Instruction("ISC", self._comp_isc, self._addr_zp0, 5),
            0xEF: Instruction("ISC", self._comp_isc, self._addr_abs, 6),
            0xF3: Instruction("ISC", self._comp_isc, self._addr_izy, 4),
            0xF7: Instruction("ISC", self._comp_isc, self._addr_zpx, 6),
            0xFB: Instruction("ISC", self._comp_isc, self._addr_aby, 7),
            0xFF: Instruction("ISC", self._comp_isc, self._addr_abx, 7),
            0x03: Instruction("SLO", self._comp_slo, self._addr_izx, 8),
            0x07: Instruction("SLO", self._comp_slo, self._addr_zp0, 5),
            0x0F: Instruction("SLO", self._comp_slo, self._addr_abs, 6),
            0x13: Instruction("SLO", self._comp_slo, self._addr_izy, 8),
            0x17: Instruction("SLO", self._comp_slo, self._addr_zpx, 6),
            0x1B: Instruction("SLO", self._comp_slo, self._addr_aby, 7),
            0x1F: Instruction("SLO", self._comp_slo, self._addr_abx, 7),
            0x0B: Instruction("ANC", self._comp_nop, self._addr_imm, 2),
            0x2B: Instruction("ANC", self._comp_nop, self._addr_imm, 2),
            0x23: Instruction("RLA", self._comp_rla, self._addr_izx, 8),
            0x27: Instruction("RLA", self._comp_rla, self._addr_zp0, 5),
            0x2F: Instruction("RLA", self._comp_rla, self._addr_abs, 6),
            0x33: Instruction("RLA", self._comp_rla, self._addr_izy, 8),
            0x37: Instruction("RLA", self._comp_rla, self._addr_zpx, 6),
            0x3B: Instruction("RLA", self._comp_rla, self._addr_aby, 7),
            0x3F: Instruction("RLA", self._comp_rla, self._addr_abx, 7),
            0x43: Instruction("SRE", self._comp_sre, self._addr_izx, 8),
            0x47: Instruction("SRE", self._comp_sre, self._addr_zp0, 5),
            0x4F: Instruction("SRE", self._comp_sre, self._addr_abs, 6),
            0x53: Instruction("SRE", self._comp_sre, self._addr_izy, 8),
            0x57: Instruction("SRE", self._comp_sre, self._addr_zpx, 6),
            0x5B: Instruction("SRE", self._comp_sre, self._addr_aby, 7),
            0x5F: Instruction("SRE", self._comp_sre, self._addr_abx, 7),
            0x63: Instruction("RRA", self._comp_rra, self._addr_izx, 8),
            0x67: Instruction("RRA", self._comp_rra, self._addr_zp0, 5),
            0x6F: Instruction("RRA", self._comp_rra, self._addr_abs, 6),
            0x73: Instruction("RRA", self._comp_rra, self._addr_izy, 8),
            0x77: Instruction("RRA", self._comp_rra, self._addr_zpx, 6),
            0x7B: Instruction("RRA", self._comp_rra, self._addr_aby, 7),
            0x7F: Instruction("RRA", self._comp_rra, self._addr_abx, 7),
            0x02: Instruction("JAM", self._comp_jam, self._addr_imp, 1),
            0x12: Instruction("JAM", self._comp_jam, self._addr_imp, 1),
            0x22: Instruction("JAM", self._comp_jam, self._addr_imp, 1),
            0x32: Instruction("JAM", self._comp_jam, self._addr_imp, 1),
            0x42: Instruction("JAM", self._comp_jam, self._addr_imp, 1),
            0x52: Instruction("JAM", self._comp_jam, self._addr_imp, 0),
            0x62: Instruction("JAM", self._comp_jam, self._addr_imp, 0),
            0x72: Instruction("JAM", self._comp_jam, self._addr_imp, 0),
            0x82: Instruction("JAM", self._comp_jam, self._addr_imp, 0),
            0x92: Instruction("JAM", self._comp_jam, self._addr_imp, 0),
            0xB2: Instruction("JAM", self._comp_jam, self._addr_imp, 0),
            0xC2: Instruction("JAM", self._comp_jam, self._addr_imp, 0),
            0xD2: Instruction("JAM", self._comp_jam, self._addr_imp, 0),
            0xE2: Instruction("JAM", self._comp_jam, self._addr_imp, 0),
            0xF2: Instruction("JAM", self._comp_jam, self._addr_imp, 0),
        }

        print(f'{len(self.opcode_to_instruction)} instructions were implemented')

    def __repr__(self):
        op_name = self.opcode_to_instruction[self.opcode].name
        return f'PC: {hex(self.pc).upper()}, OP: {op_name}, A: {self.a}, X: {self.x}, Y: {self.y}'

    def all_status_as_int(self) -> int:
        result = 0

        for f, v in self.status.items():
            if v > 0:
                result |= f

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

    def clock(self):
        if self.jammed is True:
            return

        if self.cycle == 0:
            self.opcode = self.read(self.pc)

            if self.on_opcode_loaded:
                self.on_opcode_loaded()

            self.pc += 1
            ins = self.opcode_to_instruction[self.opcode]
            self.cycle += ins.num_cycles
            extra_cycle_1, extra_cycle_2 = ins.address(), ins.compute()
            self.cycle += extra_cycle_1 & extra_cycle_2

        assert self.cycle > 0
        self.cycle -= 1

    def fetch(self):
        if self.opcode_to_instruction[self.opcode].address != self._addr_imp:
            self.fetched = self.read(self.abs_addr)
        return self.fetched

    def reset(self):
        self.a = 0
        self.x = 0
        self.y = 0
        self.stkp = 0x00FD

        for s in self.status:
            self._set_status(s, False)

        self._set_status(Status.U, True)

        self.abs_addr = 0xFFFC

        lo = self.read(self.abs_addr)
        hi = self.read(self.abs_addr+1)

        self.pc = (hi << 8) | lo
        self.rel_addr = 0
        self.abs_addr = 0
        self.fetched = None
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

            if (self.abs_addr & 0xFF00) != (self.pc & 0xFF00):
                self.cycle += 1

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
        self._set_status(Status.V, ((~self.a ^ self.fetched)
                                    & (self.a ^ added) & 0x0080) > 0)
        self._set_status(Status.N, added & 0x80)
        self.a = added & 0x00FF
        return 1

    def _comp_sbc(self):
        self.fetch()
        value = self.fetched ^ 0x00FF
        added = self.a + value + self.status[Status.C]
        self._set_status(Status.C, added > 255)
        self._set_status(Status.Z, (added & 0x00FF) == 0)
        self._set_status(Status.V, ((~self.a ^ value) &
                                    (self.a ^ added) & 0x0080) > 0)
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

        if self.opcode_to_instruction[self.opcode].address == self._addr_imp:
            self.a = new_val & 0x00FF
        else:
            self.write(self.abs_addr, new_val & 0x00FF)
        return 0

    def _comp_bcc(self):
        return self._branch_if(self._get_status(Status.C) is False)

    def _comp_bcs(self):
        return self._branch_if(self._get_status(Status.C) is True)

    def _comp_beq(self):
        return self._branch_if(self._get_status(Status.Z) is True)

    def _comp_bit(self):
        self.fetch()
        new_val = self.a & self.fetched
        self._set_status(Status.Z, (new_val & 0x00FF) == 0)
        self._set_status(Status.N, self.fetched & (1 << 7))
        self._set_status(Status.V, self.fetched & (1 << 6))
        return 0

    def _comp_bmi(self):
        return self._branch_if(self._get_status(Status.N) is True)

    def _comp_bne(self):
        return self._branch_if(self._get_status(Status.Z) is False)

    def _comp_bpl(self):
        return self._branch_if(self._get_status(Status.N) is False)

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

    def _comp_bvc(self):
        return self._branch_if(self._get_status(Status.V) is False)

    def _comp_bvs(self):
        return self._branch_if(self._get_status(Status.V) is True)

    def _comp_clc(self):
        self._set_status(Status.C, False)
        return 0

    def _comp_cld(self):
        self._set_status(Status.D, False)
        return 0

    def _comp_cli(self):
        self._set_status(Status.I, False)
        return 0

    def _comp_clv(self):
        self._set_status(Status.V, False)
        return 0

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

    def _comp_jmp(self):
        self.pc = self.abs_addr
        return 0

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
        zero_flag = (new_val & 0x00FF) == 0

        self._set_status(Status.C, carry_flag)
        self._set_status(Status.Z, zero_flag)
        self._set_status(Status.N, (new_val & 0x80) > 0)

        if self.opcode_to_instruction[self.opcode].address == self._addr_imp:
            self.a = (new_val & 0xFF)
        else:
            self.write(self.abs_addr, new_val)

        return 0

    def _comp_jam(self):
        self.jammed = True
        return 0

    def _comp_nop(self):
        return 0

    def _comp_ora(self):
        self.fetch()
        self.a |= self.fetched
        self._set_status(Status.Z, (self.a & 0xFF) == 0)
        self._set_status(Status.N, (self.a & 0x80) > 0)
        return 0

    def _comp_pha(self):
        self._push_to_stack(self.a)
        return 0

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
        carry_flag = ((self.fetched & 0xFF00) > 0)
        self._set_status(Status.C, carry_flag)
        self._set_status(Status.Z, (self.fetched & 0xFF) == 0)
        self._set_status(Status.N, (self.fetched & 0x80) > 0)

        if self.opcode_to_instruction[self.opcode].address == self._addr_imp:
            self.a = (self.fetched & 0xFF)
        else:
            self.write(self.abs_addr, (self.fetched & 0xFF))

        return 0

    def _comp_ror(self):
        self.fetch()
        old_carry_flag = self.status[Status.C]
        old_val = self.fetched
        self.fetched = ((self.fetched >> 1) & 0xFF) | (
            int(old_carry_flag) << 7)
        carry_flag = (old_val & 0x01) > 0
        self._set_status(Status.C, carry_flag)
        self._set_status(Status.Z, (self.fetched & 0xFF) == 0)
        self._set_status(Status.N, (self.fetched & 0x80) > 0)

        if self.opcode_to_instruction[self.opcode].address == self._addr_imp:
            self.a = self.fetched
        else:
            self.write(self.abs_addr, self.fetched)

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

    def _comp_sec(self):
        self._set_status(Status.C, True)
        return 0

    def _comp_sed(self):
        self._set_status(Status.D, True)
        return 0

    def _comp_sei(self):
        self._set_status(Status.I, True)
        return 0

    def _comp_sta(self):
        self.write(self.abs_addr, self.a)
        return 0

    def _comp_stx(self):
        self.write(self.abs_addr, self.x)
        return 0

    def _comp_sty(self):
        self.write(self.abs_addr, self.y)
        return 0

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

    def _comp_txs(self):
        self.stkp = self.x
        return 0

    def _comp_tya(self):
        self.a = self.y
        self._set_status(Status.Z, self.a == 0)
        self._set_status(Status.N, (self.a & 0x80) > 0)
        return 0

    def _comp_lax(self):
        self._comp_lda()
        return self._comp_ldx()

    def _comp_sax(self):
        m = self.x & self.a
        self.write(self.abs_addr, m)
        return 0

    def _addr_imp(self):
        self.fetched = self.a
        return 0

    def _addr_imm(self):
        self.abs_addr = self.pc
        self.pc += 1
        return 0

    def _addr_zp0(self):
        self.abs_addr = self.read(self.pc)
        self.pc += 1
        self.abs_addr &= 0x00FF
        return 0

    def _addr_zpx(self):
        self.abs_addr = (self.read(self.pc) + self.x) & 0xFFFF
        self.pc += 1
        self.abs_addr &= 0x00FF
        return 0

    def _addr_zpy(self):
        self.abs_addr = self.read(self.pc) + self.y
        self.pc += 1
        self.abs_addr &= 0x00FF
        return 0

    def _addr_rel(self):
        self.rel_addr = self.read(self.pc)
        self.pc += 1

        if self.rel_addr & 0x80:
            self.rel_addr |= 0xFF00
        return 0

    def _addr_abs(self):
        lo = self.read(self.pc)
        self.pc += 1
        hi = self.read(self.pc)
        self.pc += 1

        self.abs_addr = (hi << 8) | lo
        return 0

    def _addr_abx(self):
        lo = self.read(self.pc)
        self.pc += 1
        hi = self.read(self.pc)
        self.pc += 1

        self.abs_addr = (hi << 8) | lo
        self.abs_addr += self.x
        self.abs_addr &= 0xFFFF

        return 0 if (self.abs_addr & 0xFF00) == (hi << 8) else 1

    def _addr_aby(self):
        lo = self.read(self.pc)
        self.pc += 1
        hi = self.read(self.pc)
        self.pc += 1

        self.abs_addr = (hi << 8) | lo
        self.abs_addr += self.y
        self.abs_addr &= 0xFFFF

        return 0 if (self.abs_addr & 0xFF00) == (hi << 8) else 1

    def _addr_ind(self):
        ptr_lo = self.read(self.pc)
        self.pc += 1
        ptr_hi = self.read(self.pc)
        self.pc += 1

        ptr = (ptr_hi << 8) | ptr_lo

        if ptr_lo == 0x00FF:
            self.abs_addr = (self.read(ptr & 0xFF00) << 8) | self.read(ptr)
        else:
            self.abs_addr = (self.read(ptr+1) << 8) | self.read(ptr)

        return 0

    def _addr_izx(self):
        ptr = self.read(self.pc)
        self.pc += 1

        lo = self.read((ptr + self.x) & 0x00FF)
        hi = self.read((ptr + self.x + 1) & 0x00FF)

        self.abs_addr = (hi << 8) | lo
        return 0

    def _addr_izy(self):
        ptr = self.read(self.pc)
        self.pc += 1

        lo = self.read(ptr & 0x00FF)
        hi = self.read((ptr + 1) & 0x00FF)

        self.abs_addr = (hi << 8) | lo
        self.abs_addr += self.y
        self.abs_addr &= 0xFFFF

        if (self.abs_addr & 0xFF00) != (hi << 8):
            return 1

        return 0
