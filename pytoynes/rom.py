from enum import IntEnum

class MirrorMode(IntEnum):
    HORIZONTAL = 0
    VERTICAL = 1
    ONESCREEN_LO = 2
    ONESCREEN_HI = 3

class TvSystem(IntEnum):
    NTSC = 0
    PAL = 1
    DUAL = 2

class Rom:
    def __init__(self, path: str):
        self.path = path

        with open(self.path, 'rb') as f:
            rom_data = f.read()
            if rom_data[0:3] != b'NES' or rom_data[3] != 0x1A:
                raise ValueError("Invalid iNES header")

            cursor = 4
            prg_size_lsb = rom_data[cursor]; cursor += 1
            chr_size_lsb = rom_data[cursor]; cursor += 1
            flag_6 = rom_data[cursor]; cursor += 1
            flag_7 = rom_data[cursor]; cursor += 1
            mapper_lo = (flag_6 >> 4) & 0x0F
            mapper_mid = (flag_7 >> 4) & 0x0F
            
            self.mirroring = MirrorMode(flag_6 & 0b00000001)
            self.has_other_persistent_memory = (flag_6 & 0b00000010) > 0
            self.has_trainer = (flag_6 & 0b00000100) > 0
            self.ignore_mirror = (flag_6 & 0b00001000) > 0
            
            self.is_nes_2 = ((flag_7 & 0x0C) == 0x08)
            
            if self.is_nes_2:
                flag_8 = rom_data[cursor]; cursor += 1
                flag_9 = rom_data[cursor]; cursor += 1
                mapper_hi = flag_8 & 0x0F
                self.mapper = (mapper_hi << 8) | (mapper_mid << 4) | mapper_lo
                
                prg_size_msb = flag_9 & 0x0F
                chr_size_msb = (flag_9 >> 4) & 0x0F
                
                if prg_size_msb == 0x0F:
                    # Exponential PRG size
                    exponent = (prg_size_lsb >> 2) & 0x3F
                    multiplier = (prg_size_lsb & 0x03) * 2 + 1
                    self.num_prg_banks = (2 ** exponent) * multiplier // 16384
                else:
                    self.num_prg_banks = (prg_size_msb << 8) | prg_size_lsb
                
                if chr_size_msb == 0x0F:
                    # Exponential CHR size
                    exponent = (chr_size_lsb >> 2) & 0x3F
                    multiplier = (chr_size_lsb & 0x03) * 2 + 1
                    self.num_chr_banks = (2 ** exponent) * multiplier // 8192
                else:
                    self.num_chr_banks = (chr_size_msb << 8) | chr_size_lsb
                
                # PRG-RAM size (Byte 10)
                prg_ram_shift = rom_data[cursor] & 0x0F; cursor += 1
                self.num_prg_ram_banks = (64 << prg_ram_shift) // 8192 if prg_ram_shift > 0 else 0
            else:
                self.mapper = (mapper_mid << 4) | mapper_lo
                self.num_prg_banks = prg_size_lsb
                self.num_chr_banks = chr_size_lsb
                # iNES 1.0 PRG-RAM size (Byte 8)
                self.num_prg_ram_banks = max(rom_data[cursor], 1); cursor += 1
                
            cursor = 16 # Padding
            
            if self.has_trainer:
                self.trainer = rom_data[cursor:cursor+512]
                cursor += 512

            self.prg_rom_data = rom_data[cursor:cursor+self.num_prg_banks*16384]
            cursor += self.num_prg_banks*16384

            self.chr_rom_data = rom_data[cursor:cursor+self.num_chr_banks*8192]
            cursor += self.num_chr_banks*8192
