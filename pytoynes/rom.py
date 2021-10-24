from enum import IntEnum

class MirrorMode(IntEnum):
    HORIZONTAL = 0
    VERTICAL = 1

class TvSystem(IntEnum):
    NTSC = 0
    PAL = 1
    DUAL = 2

class Rom:
    def __init__(self, path: str):
        self.path = path

        with open(self.path, 'rb') as f:
            rom_data = f.read()
            cursor = 0
            self.constant = rom_data[cursor:cursor+4]
            cursor += 4
            self.num_prg_banks = rom_data[cursor]
            cursor += 1
            self.num_chr_banks = rom_data[cursor]
            flag_6 = rom_data[cursor]
            cursor += 1
            self.mirroring = MirrorMode(flag_6 & 0b00000001)
            self.has_other_persistent_memory = (flag_6 & 0b00000010) > 0
            self.has_trainer = (flag_6 & 0b00000100) > 0
            self.ignore_mirror = (flag_6 & 0b00001000) > 0
            mapper_lo = (flag_6 >> 4) & 0xFF
            flag_7 = rom_data[cursor]
            cursor += 1
            self.vs_unisystem = (flag_7 & 0b00000001) > 0
            self.play_choice_10 = (flag_7 & 0b00000010) > 0
            self.is_nes_2 = (((flag_7 & 0b00001000) | (flag_7 & 0b00000100)) >> 2) == 2
            assert self.is_nes_2 is False
            mapper_hi = (flag_7 >> 4) & 0xFF
            self.mapper = (mapper_hi << 4) | mapper_lo
            self.num_prg_ram_banks = max(rom_data[cursor], 1) #1 bank == 8kb
            cursor += 1
            flag_9 = rom_data[cursor]
            cursor += 1
            self.tv_system = TvSystem(flag_9 & 0x01)
            flag_10 = rom_data[cursor]
            cursor += 1
            cursor = 16 #padding to align 16 byte
            
            if self.has_trainer:
                self.trainer = rom_data[cursor:cursor+512]
                cursor += 512

            self.prg_rom_data = rom_data[cursor:cursor+self.num_prg_banks*16384]
            cursor += self.num_prg_banks*16384

            self.chr_rom_data = rom_data[cursor:cursor+self.num_chr_banks*8192]
            cursor += self.num_chr_banks*8192

            if self.play_choice_10:
                self.play_choice_data = rom_data[cursor:cursor+8192]
