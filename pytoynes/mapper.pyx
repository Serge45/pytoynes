# cython: language_level=3, boundscheck=False, wraparound=False
cdef class Mapper:
    def __init__(self, int num_prg_banks, int num_chr_banks, int mirror_mode=0):
        self.num_prg_banks = num_prg_banks
        self.num_chr_banks = num_chr_banks
        self.mirror_mode = mirror_mode
        self.irq_active = False

    cpdef int map_cpu_read_addr(self, int addr):
        return -1

    cpdef int map_cpu_write_addr(self, int addr, int data):
        return -1

    cpdef int map_ppu_read_addr(self, int addr):
        return -1

    cpdef int map_ppu_write_addr(self, int addr, int data):
        return -1

    cpdef void count_scanline(self):
        pass

cdef class Mapper001(Mapper):
    def __init__(self, int num_prg_banks, int num_chr_banks, int mirror_mode=0):
        super().__init__(num_prg_banks, num_chr_banks, mirror_mode)
        self.shift_reg = 0x00
        self.shift_count = 0
        self.control_reg = 0x1C
        self.chr_bank0_reg = 0
        self.chr_bank1_reg = 0
        self.prg_bank_reg = 0

    cpdef int map_cpu_read_addr(self, int addr):
        cdef int prg_mode = (self.control_reg >> 2) & 0x03
        cdef int bank

        if 0x6000 <= addr <= 0x7FFF:
            return (addr & 0x1FFF) | 0x10000000

        if 0x8000 <= addr <= 0xFFFF:
            if prg_mode <= 1: # 32K mode
                bank = (self.prg_bank_reg & 0x0E)
                return bank * 0x4000 + (addr & 0x7FFF)
            elif prg_mode == 2: # Fixed $8000, switch $C000
                if 0x8000 <= addr <= 0xBFFF:
                    return addr & 0x3FFF
                else:
                    bank = self.prg_bank_reg & 0x0F
                    return bank * 0x4000 + (addr & 0x3FFF)
            elif prg_mode == 3: # Switch $8000, fixed $C000
                if 0x8000 <= addr <= 0xBFFF:
                    bank = self.prg_bank_reg & 0x0F
                    return bank * 0x4000 + (addr & 0x3FFF)
                else:
                    return (self.num_prg_banks - 1) * 0x4000 + (addr & 0x3FFF)
        return -1

    cpdef int map_cpu_write_addr(self, int addr, int data):
        if 0x6000 <= addr <= 0x7FFF:
            return (addr & 0x1FFF) | 0x10000000

        if 0x8000 <= addr <= 0xFFFF:
            if data & 0x80: # Reset
                self.shift_reg = 0x00
                self.shift_count = 0
                self.control_reg |= 0x0C
            else:
                self.shift_reg = (self.shift_reg >> 1) | ((data & 0x01) << 4)
                self.shift_count += 1
                if self.shift_count == 5:
                    if 0x8000 <= addr <= 0x9FFF:
                        self.control_reg = self.shift_reg
                        # Mirroring: 0: 1S_LO, 1: 1S_HI, 2: VERT, 3: HORIZ
                        # Our rom.MirrorMode: HORIZ=0, VERT=1, 1S_LO=2, 1S_HI=3
                        m = self.control_reg & 0x03
                        if m == 0: self.mirror_mode = 2 # 1S_LO
                        elif m == 1: self.mirror_mode = 3 # 1S_HI
                        elif m == 2: self.mirror_mode = 1 # VERT
                        elif m == 3: self.mirror_mode = 0 # HORIZ
                    elif 0xA000 <= addr <= 0xBFFF:
                        self.chr_bank0_reg = self.shift_reg
                    elif 0xC000 <= addr <= 0xDFFF:
                        self.chr_bank1_reg = self.shift_reg
                    elif 0xE000 <= addr <= 0xFFFF:
                        self.prg_bank_reg = self.shift_reg

                    self.shift_reg = 0x00
                    self.shift_count = 0
        return -1

    cpdef int map_ppu_read_addr(self, int addr):
        cdef int chr_mode = (self.control_reg >> 4) & 0x01
        cdef int bank

        if 0x0000 <= addr <= 0x1FFF:
            if self.num_chr_banks == 0: # CHR RAM
                return addr

            if chr_mode == 0: # 8K mode
                bank = self.chr_bank0_reg & 0x1E
                return bank * 0x1000 + addr
            else: # 4K mode
                if 0x0000 <= addr <= 0x0FFF:
                    bank = self.chr_bank0_reg
                    return bank * 0x1000 + (addr & 0x0FFF)
                else:
                    bank = self.chr_bank1_reg
                    return bank * 0x1000 + (addr & 0x0FFF)
        return -1

    cpdef int map_ppu_write_addr(self, int addr, int data):
        if 0x0000 <= addr <= 0x1FFF:
            if self.num_chr_banks == 0: # CHR RAM
                return addr
        return -1

cdef class Mapper000(Mapper):
    cdef inline int _map_cpu_addr(self, int addr):
        cdef int mask
        if addr >= 0x8000 and addr <= 0xFFFF:
            mask = 0x7FFF if self.num_prg_banks > 1 else 0x3FFF
            return addr & mask
        return -1

    cpdef int map_cpu_read_addr(self, int addr):
        return self._map_cpu_addr(addr)

    cpdef int map_cpu_write_addr(self, int addr, int data):
        return self._map_cpu_addr(addr)

    cpdef int map_ppu_read_addr(self, int addr):
        if addr >= 0x0000 and addr <= 0x1FFF:
            return addr
        return -1

    cpdef int map_ppu_write_addr(self, int addr, int data):
        if addr >= 0x0000 and addr <= 0x1FFF:
            if self.num_chr_banks == 0:
                # Treat as CHR-RAM
                return addr
        return -1

cdef class Mapper002(Mapper):
    def __init__(self, int num_prg_banks, int num_chr_banks, int mirror_mode=0):
        super().__init__(num_prg_banks, num_chr_banks, mirror_mode)
        self.prg_bank_lo = 0
        self.prg_bank_hi = num_prg_banks - 1

    cpdef int map_cpu_read_addr(self, int addr):
        if 0x8000 <= addr <= 0xBFFF:
            return self.prg_bank_lo * 0x4000 + (addr & 0x3FFF)
        if 0xC000 <= addr <= 0xFFFF:
            return self.prg_bank_hi * 0x4000 + (addr & 0x3FFF)
        return -1

    cpdef int map_cpu_write_addr(self, int addr, int data):
        if 0x8000 <= addr <= 0xFFFF:
            self.prg_bank_lo = data & 0x0F
        return -1

    cpdef int map_ppu_read_addr(self, int addr):
        if 0x0000 <= addr <= 0x1FFF:
            return addr
        return -1

    cpdef int map_ppu_write_addr(self, int addr, int data):
        if 0x0000 <= addr <= 0x1FFF:
            if self.num_chr_banks == 0:
                return addr
        return -1

cdef class Mapper003(Mapper):
    def __init__(self, int num_prg_banks, int num_chr_banks, int mirror_mode=0):
        super().__init__(num_prg_banks, num_chr_banks, mirror_mode)
        self.chr_bank = 0

    cpdef int map_cpu_read_addr(self, int addr):
        cdef int mask = 0x7FFF if self.num_prg_banks > 1 else 0x3FFF
        if addr >= 0x8000 and addr <= 0xFFFF:
            return addr & mask
        return -1

    cpdef int map_cpu_write_addr(self, int addr, int data):
        if 0x8000 <= addr <= 0xFFFF:
            self.chr_bank = data & 0x03
        return -1

    cpdef int map_ppu_read_addr(self, int addr):
        if 0x0000 <= addr <= 0x1FFF:
            return self.chr_bank * 0x2000 + addr
        return -1

    cpdef int map_ppu_write_addr(self, int addr, int data):
        return -1

cdef class Mapper004(Mapper):
    def __init__(self, int num_prg_banks, int num_chr_banks, int mirror_mode=0):
        super().__init__(num_prg_banks, num_chr_banks, mirror_mode)
        self.target_reg = 0
        self.prg_bank_mode = 0
        self.chr_invert = 0
        for i in range(8): self.regs[i] = 0
        self.irq_counter = 0
        self.irq_latch = 0
        self.irq_enabled = False
        self.irq_active = False

    cpdef int map_cpu_read_addr(self, int addr):
        cdef int bank
        if 0x6000 <= addr <= 0x7FFF:
            return (addr & 0x1FFF) | 0x10000000
        if 0x8000 <= addr <= 0x9FFF:
            bank = self.regs[6] if self.prg_bank_mode == 0 else (self.num_prg_banks * 2 - 2)
            return bank * 0x2000 + (addr & 0x1FFF)
        if 0xA000 <= addr <= 0xBFFF:
            bank = self.regs[7]
            return bank * 0x2000 + (addr & 0x1FFF)
        if 0xC000 <= addr <= 0xDFFF:
            bank = (self.num_prg_banks * 2 - 2) if self.prg_bank_mode == 0 else self.regs[6]
            return bank * 0x2000 + (addr & 0x1FFF)
        if 0xE000 <= addr <= 0xFFFF:
            return (self.num_prg_banks * 2 - 1) * 0x2000 + (addr & 0x1FFF)
        return -1

    cpdef int map_cpu_write_addr(self, int addr, int data):
        if 0x6000 <= addr <= 0x7FFF:
            return (addr & 0x1FFF) | 0x10000000
        if 0x8000 <= addr <= 0x9FFF:
            if not (addr & 0x01): # $8000
                self.target_reg = data & 0x07
                self.prg_bank_mode = (data >> 6) & 0x01
                self.chr_invert = (data >> 7) & 0x01
            else: # $8001
                self.regs[self.target_reg] = data
        elif 0xA000 <= addr <= 0xBFFF:
            if not (addr & 0x01): # $A000
                self.mirror_mode = 0 if (data & 0x01) else 1 # 0: HORIZ, 1: VERT
        elif 0xC000 <= addr <= 0xDFFF:
            if not (addr & 0x01): # $C000
                self.irq_latch = data
            else: # $C001
                self.irq_counter = 0
        elif 0xE000 <= addr <= 0xFFFF:
            if not (addr & 0x01): # $E000
                self.irq_enabled = False
                self.irq_active = False
            else: # $E001
                self.irq_enabled = True
        return -1

    cpdef int map_ppu_read_addr(self, int addr):
        if 0x0000 <= addr <= 0x1FFF:
            if self.chr_invert == 0:
                if 0x0000 <= addr <= 0x07FF: return (self.regs[0] & 0xFE) * 0x0400 + (addr & 0x07FF)
                if 0x0800 <= addr <= 0x0FFF: return (self.regs[1] & 0xFE) * 0x0400 + (addr & 0x07FF)
                if 0x1000 <= addr <= 0x13FF: return self.regs[2] * 0x0400 + (addr & 0x03FF)
                if 0x1400 <= addr <= 0x17FF: return self.regs[3] * 0x0400 + (addr & 0x03FF)
                if 0x1800 <= addr <= 0x1BFF: return self.regs[4] * 0x0400 + (addr & 0x03FF)
                if 0x1C00 <= addr <= 0x1FFF: return self.regs[5] * 0x0400 + (addr & 0x03FF)
            else:
                if 0x0000 <= addr <= 0x03FF: return self.regs[2] * 0x0400 + (addr & 0x03FF)
                if 0x0400 <= addr <= 0x07FF: return self.regs[3] * 0x0400 + (addr & 0x03FF)
                if 0x0800 <= addr <= 0x0BFF: return self.regs[4] * 0x0400 + (addr & 0x03FF)
                if 0x0C00 <= addr <= 0x0FFF: return self.regs[5] * 0x0400 + (addr & 0x03FF)
                if 0x1000 <= addr <= 0x17FF: return (self.regs[0] & 0xFE) * 0x0400 + (addr & 0x07FF)
                if 0x1800 <= addr <= 0x1FFF: return (self.regs[1] & 0xFE) * 0x0400 + (addr & 0x07FF)
        return -1

    cpdef int map_ppu_write_addr(self, int addr, int data):
        if 0x0000 <= addr <= 0x1FFF:
            if self.num_chr_banks == 0: return addr
        return -1

    cpdef void count_scanline(self):
        if self.irq_counter == 0:
            self.irq_counter = self.irq_latch
        else:
            self.irq_counter -= 1
        
        if self.irq_counter == 0:
            if self.irq_enabled:
                self.irq_active = True
