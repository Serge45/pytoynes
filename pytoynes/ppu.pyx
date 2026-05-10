# cython: language_level=3, boundscheck=False, wraparound=False
import array
cimport numpy as np
import numpy as np
from .cartridge cimport Cartridge

# Precomputed bit reversal table for sprite flipping
cdef unsigned char BIT_REVERSE[256]
def _init_bit_reverse():
    for i in range(256):
        b = '{:08b}'.format(i)
        BIT_REVERSE[i] = int(b[::-1], 2)
_init_bit_reverse()

cdef class PPU:
    def __init__(self):
        self.cartridge = None
        self.mirror_mode = 0

        self.vram = array.array('B', bytearray(2048))
        self.palette_vram = array.array('B', bytearray(32))
        self.oam_vram = array.array('B', bytearray(256))

        # Pixel buffer for the full frame
        self.pixels = np.zeros((240, 256), dtype=np.uint8)
        self.pixels_view = self.pixels

        self.ppu_ctrl = 0
        self.ppu_mask = 0
        self.ppu_status = 0
        self.oam_addr = 0
        self.oam_data = 0
        self.v = 0
        self.t = 0
        self.fine_x = 0
        self.w = 0
        self.ppu_data_buffer = 0
        self.scanline = 0
        self.cycle = 0
        self.total_cycles = 0
        self.frame_count = 0
        self.nmi = False

        self.bg_next_tile_id = 0
        self.bg_next_tile_attrib = 0
        self.bg_next_tile_lsb = 0
        self.bg_next_tile_msb = 0
        self.bg_shifter_tile_lo = 0
        self.bg_shifter_tile_hi = 0
        self.bg_shifter_attrib_lo = 0
        self.bg_shifter_attrib_hi = 0

        self.secondary_oam = array.array('B', bytearray(32))
        self.sprite_count = 0
        self.sprite_shifter_pattern_lo = array.array('B', bytearray(8))
        self.sprite_shifter_pattern_hi = array.array('B', bytearray(8))
        self.sprite_attribs = array.array('B', bytearray(8))
        self.sprite_x_counters = array.array('B', bytearray(8))
        self.sprite_zero_hit_possible = False
        self.is_odd_frame = False

    cpdef void clock(self):
        cdef int scanline = self.scanline
        cdef int cycle = self.cycle
        cdef int phase

        if -1 <= scanline <= 239:
            # Sprite evaluation and fetches
            if cycle == 257:
                self._evaluate_sprites()
            elif cycle == 340:
                self._fetch_sprite_data()

            if 1 <= cycle <= 256:
                if scanline >= 0: self._render_pixel()
                self._update_shifters()
                phase = cycle & 0x07
                if phase == 0:
                    self._load_shifters()
                    self._increment_scroll_x()
                elif phase == 1: self._fetch_nt()
                elif phase == 3: self._fetch_at()
                elif phase == 5: self._fetch_pt_lo()
                elif phase == 7: self._fetch_pt_hi()

            if cycle == 256: self._increment_scroll_y()
            elif cycle == 257: self._reset_scroll_x()

            if 321 <= cycle <= 336:
                self._update_shifters()
                phase = cycle & 0x07
                if phase == 0:
                    self._load_shifters()
                    self._increment_scroll_x()
                elif phase == 1: self._fetch_nt()
                elif phase == 3: self._fetch_at()
                elif phase == 5: self._fetch_pt_lo()
                elif phase == 7: self._fetch_pt_hi()

            if scanline == -1 and 280 <= cycle <= 304:
                self._reset_scroll_y()

        self.cycle += 1
        self.total_cycles += 1

        if self.cycle >= 341:
            self.cycle = 0
            self.scanline += 1
            if self.scanline == 241:
                self.ppu_status |= 0x80
                if self.ppu_ctrl & 0x80: self.nmi = True
            elif self.scanline >= 261:
                self.scanline = -1
                self.frame_count += 1
                self.ppu_status &= ~0xC0
                self.nmi = False
                self.is_odd_frame = not self.is_odd_frame
                # Skip cycle on odd frames
                if (self.ppu_mask & 0x18) and self.is_odd_frame:
                    self.cycle = 1
                    self.total_cycles += 1

    cpdef void run_to(self, long long target_total_cycles):
        while self.total_cycles < target_total_cycles:
            self.clock()

    cpdef void _render_pixel(self):
        cdef int ppu_mask = self.ppu_mask
        cdef int cycle = self.cycle
        cdef int bg_pixel = 0, bg_palette = 0
        cdef int fg_pixel = 0, fg_palette = 0, fg_priority = 0
        cdef bint sprite_zero_hit = False
        cdef int bit_mux, p0_pixel, p1_pixel, bg_pal0, bg_pal1
        cdef int pixel_lo, pixel_hi, i, palette, pixel, pal_addr, color_idx

        # Background
        if ppu_mask & 0x08:
            if cycle > 8 or (ppu_mask & 0x02):
                bit_mux = 0x8000 >> self.fine_x
                p0_pixel = 1 if (self.bg_shifter_tile_lo & bit_mux) else 0
                p1_pixel = 1 if (self.bg_shifter_tile_hi & bit_mux) else 0
                bg_pixel = (p1_pixel << 1) | p0_pixel
                bg_pal0 = 1 if (self.bg_shifter_attrib_lo & bit_mux) else 0
                bg_pal1 = 1 if (self.bg_shifter_attrib_hi & bit_mux) else 0
                bg_palette = (bg_pal1 << 1) | bg_pal0

        # Sprites
        if ppu_mask & 0x10:
            if cycle > 8 or (ppu_mask & 0x04):
                for i in range(self.sprite_count):
                    if self.sprite_x_counters[i] == 0:
                        pixel_lo = 1 if (self.sprite_shifter_pattern_lo[i] & 0x80) else 0
                        pixel_hi = 1 if (self.sprite_shifter_pattern_hi[i] & 0x80) else 0
                        fg_pixel = (pixel_hi << 1) | pixel_lo
                        if fg_pixel != 0:
                            fg_palette = (self.sprite_attribs[i] & 0x03) + 0x04
                            fg_priority = 1 if (self.sprite_attribs[i] & 0x20) == 0 else 0
                            if i == 0 and self.sprite_zero_hit_possible:
                                sprite_zero_hit = True
                            break

        # Mixing
        palette = 0
        pixel = 0
        if bg_pixel == 0:
            if fg_pixel > 0: pixel = fg_pixel; palette = fg_palette
        elif fg_pixel == 0:
            pixel = bg_pixel; palette = bg_palette
        else:
            if fg_priority: pixel = fg_pixel; palette = fg_palette
            else: pixel = bg_pixel; palette = bg_palette
            if sprite_zero_hit and (ppu_mask & 0x18) == 0x18:
                if 1 <= cycle <= 255:
                    if not (self.ppu_status & 0x40): self.ppu_status |= 0x40

        if pixel == 0: color_idx = self.palette_vram[0]
        else:
            pal_addr = (palette << 2) + pixel
            if (pal_addr & 0x13) == 0x10: pal_addr &= ~0x10
            color_idx = self.palette_vram[pal_addr & 0x1F]
        if ppu_mask & 0x01: color_idx &= 0x30
        
        # Write to pixel buffer via memoryview
        if 0 <= self.scanline < 240 and 1 <= cycle <= 256:
            self.pixels_view[self.scanline, cycle - 1] = color_idx

    cpdef void _update_shifters(self):
        cdef int ppu_mask = self.ppu_mask
        cdef int i
        if ppu_mask & 0x08:
            self.bg_shifter_tile_lo = (self.bg_shifter_tile_lo << 1) & 0xFFFF
            self.bg_shifter_tile_hi = (self.bg_shifter_tile_hi << 1) & 0xFFFF
            self.bg_shifter_attrib_lo = (self.bg_shifter_attrib_lo << 1) & 0xFFFF
            self.bg_shifter_attrib_hi = (self.bg_shifter_attrib_hi << 1) & 0xFFFF
        if ppu_mask & 0x10 and 1 <= self.cycle <= 256:
            for i in range(self.sprite_count):
                if self.sprite_x_counters[i] > 0: self.sprite_x_counters[i] -= 1
                else:
                    self.sprite_shifter_pattern_lo[i] = (self.sprite_shifter_pattern_lo[i] << 1) & 0xFF
                    self.sprite_shifter_pattern_hi[i] = (self.sprite_shifter_pattern_hi[i] << 1) & 0xFF

    cdef void _load_shifters(self):
        self.bg_shifter_tile_lo = (self.bg_shifter_tile_lo & 0xFF00) | self.bg_next_tile_lsb
        self.bg_shifter_tile_hi = (self.bg_shifter_tile_hi & 0xFF00) | self.bg_next_tile_msb
        self.bg_shifter_attrib_lo = (self.bg_shifter_attrib_lo & 0xFF00) | (0xFF if (self.bg_next_tile_attrib & 0x01) else 0x00)
        self.bg_shifter_attrib_hi = (self.bg_shifter_attrib_hi & 0xFF00) | (0xFF if (self.bg_next_tile_attrib & 0x02) else 0x00)

    cdef void _increment_scroll_x(self):
        if not (self.ppu_mask & 0x18): return
        if (self.v & 0x001F) == 31: self.v &= ~0x001F; self.v ^= 0x0400
        else: self.v += 1

    cdef void _increment_scroll_y(self):
        cdef int y
        if not (self.ppu_mask & 0x18): return
        if (self.v & 0x7000) != 0x7000: self.v += 0x1000
        else:
            self.v &= ~0x7000
            y = (self.v & 0x03E0) >> 5
            if y == 29: y = 0; self.v ^= 0x0800
            elif y == 31: y = 0
            else: y += 1
            self.v = (self.v & ~0x03E0) | (y << 5)

    cdef void _reset_scroll_x(self):
        if not (self.ppu_mask & 0x18): return
        self.v = (self.v & ~0x041F) | (self.t & 0x041F)

    cdef void _reset_scroll_y(self):
        if not (self.ppu_mask & 0x18): return
        self.v = (self.v & ~0x7BE0) | (self.t & 0x7BE0)

    cdef void _fetch_nt(self):
        self.bg_next_tile_id = self.ppu_read(0x2000 | (self.v & 0x0FFF))
    cdef void _fetch_at(self):
        cdef int v = self.v
        cdef int at_addr = 0x23C0 | (v & 0x0C00) | ((v >> 4) & 0x38) | ((v >> 2) & 0x07)
        self.bg_next_tile_attrib = self.ppu_read(at_addr)
        if (v >> 6) & 0x01: self.bg_next_tile_attrib >>= 4
        if (v >> 1) & 0x01: self.bg_next_tile_attrib >>= 2
        self.bg_next_tile_attrib &= 0x03
    cdef void _fetch_pt_lo(self):
        cdef int table = (self.ppu_ctrl >> 4) & 0x01
        cdef int fine_y = (self.v >> 12) & 0x07
        self.bg_next_tile_lsb = self.ppu_read(table * 0x1000 + self.bg_next_tile_id * 16 + fine_y)
    cdef void _fetch_pt_hi(self):
        cdef int table = (self.ppu_ctrl >> 4) & 0x01
        cdef int fine_y = (self.v >> 12) & 0x07
        self.bg_next_tile_msb = self.ppu_read(table * 0x1000 + self.bg_next_tile_id * 16 + fine_y + 8)

    cdef void _evaluate_sprites(self):
        cdef int h = 16 if (self.ppu_ctrl & 0x20) else 8
        cdef int y, i, n, diff
        self.sprite_count = 0
        self.sprite_zero_hit_possible = False
        
        for i in range(64):
            y = self.oam_vram[i*4]
            diff = self.scanline - y
            if 0 <= diff < h:
                if self.sprite_count < 8:
                    if i == 0: self.sprite_zero_hit_possible = True
                    for n in range(4): self.secondary_oam[self.sprite_count*4 + n] = self.oam_vram[i*4 + n]
                    self.sprite_count += 1
                else:
                    self.ppu_status |= 0x20 # Sprite overflow
                    break

    cdef void _fetch_sprite_data(self):
        cdef int h = 16 if (self.ppu_ctrl & 0x20) else 8
        cdef int i, tile_id, y, attrib, x, addr, diff
        
        for i in range(8):
            if i < self.sprite_count:
                y = self.secondary_oam[i*4]
                tile_id = self.secondary_oam[i*4 + 1]
                attrib = self.secondary_oam[i*4 + 2]
                x = self.secondary_oam[i*4 + 3]
                diff = self.scanline - y
                
                if h == 8:
                    if not (attrib & 0x80): addr = ((self.ppu_ctrl & 0x08) << 9) | (tile_id << 4) | diff
                    else: addr = ((self.ppu_ctrl & 0x08) << 9) | (tile_id << 4) | (7 - diff)
                else:
                    if not (attrib & 0x80):
                        if diff < 8: addr = ((tile_id & 0x01) << 12) | ((tile_id & 0xFE) << 4) | diff
                        else: addr = ((tile_id & 0x01) << 12) | (((tile_id & 0xFE) + 1) << 4) | (diff - 8)
                    else:
                        if diff < 8: addr = ((tile_id & 0x01) << 12) | (((tile_id & 0xFE) + 1) << 4) | (7 - diff)
                        else: addr = ((tile_id & 0x01) << 12) | ((tile_id & 0xFE) << 4) | (15 - diff)
                
                self.sprite_shifter_pattern_lo[i] = self.ppu_read(addr)
                self.sprite_shifter_pattern_hi[i] = self.ppu_read(addr + 8)
                if attrib & 0x40:
                    self.sprite_shifter_pattern_lo[i] = BIT_REVERSE[self.sprite_shifter_pattern_lo[i]]
                    self.sprite_shifter_pattern_hi[i] = BIT_REVERSE[self.sprite_shifter_pattern_hi[i]]
                
                self.sprite_attribs[i] = attrib
                self.sprite_x_counters[i] = x
            else:
                self.sprite_shifter_pattern_lo[i] = 0
                self.sprite_shifter_pattern_hi[i] = 0
                self.sprite_attribs[i] = 0
                self.sprite_x_counters[i] = 0

    cpdef int cpu_read(self, int addr):
        cdef int data = 0
        if addr == 0x2002:
            data = (self.ppu_status & 0xE0) | (self.ppu_data_buffer & 0x1F)
            self.ppu_status &= ~0x80
            self.w = 0
            return data
        elif addr == 0x2004: return self.oam_vram[self.oam_addr]
        elif addr == 0x2007:
            data = self.ppu_data_buffer
            self.ppu_data_buffer = self.ppu_read(self.v & 0x3FFF)
            if (self.v & 0x3FFF) >= 0x3F00: data = self.ppu_data_buffer
            self.v += (32 if (self.ppu_ctrl & 0x04) else 1)
            return data
        return 0

    cpdef void cpu_write(self, int addr, int data):
        if addr == 0x2000:
            self.ppu_ctrl = data
            self.t = (self.t & ~0x0C00) | ((data & 0x03) << 10)
        elif addr == 0x2001: self.ppu_mask = data
        elif addr == 0x2003: self.oam_addr = data
        elif addr == 0x2004:
            self.oam_vram[self.oam_addr] = data
            self.oam_addr = (self.oam_addr + 1) & 0xFF
        elif addr == 0x2005:
            if self.w == 0:
                self.fine_x = data & 0x07
                self.t = (self.t & ~0x001F) | (data >> 3)
                self.w = 1
            else:
                self.t = (self.t & ~0x73E0) | ((data & 0x07) << 12) | ((data & 0xF8) << 2)
                self.w = 0
        elif addr == 0x2006:
            if self.w == 0:
                self.t = (self.t & ~0x7F00) | ((data & 0x3F) << 8)
                self.w = 1
            else:
                self.t = (self.t & ~0x00FF) | data
                self.v = self.t
                self.w = 0
        elif addr == 0x2007:
            self.ppu_write(self.v & 0x3FFF, data)
            self.v += (32 if (self.ppu_ctrl & 0x04) else 1)

    cpdef int ppu_read(self, int addr):
        cdef int res
        addr &= 0x3FFF
        if self.cartridge is not None:
            res = self.cartridge.ppu_read(addr)
            if res != -1: return res # Fall through if -1
        
        if addr <= 0x1FFF: return 0
        elif addr <= 0x3EFF: return self.vram[self._map_nt_addr(addr)]
        else:
            addr &= 0x001F
            if (addr & 0x13) == 0x10: addr &= ~0x10
            return self.palette_vram[addr]

    cpdef void ppu_write(self, int addr, int data):
        addr &= 0x3FFF
        if self.cartridge is not None:
            if self.cartridge.ppu_write(addr, data) != -1: return # Fall through if -1

        if addr <= 0x1FFF: return
        elif addr <= 0x3EFF: self.vram[self._map_nt_addr(addr)] = data & 0xFF
        else:
            addr &= 0x001F
            if (addr & 0x13) == 0x10: addr &= ~0x10
            self.palette_vram[addr] = data & 0x3F

    cpdef void connect_cartridge(self, Cartridge cartridge):
        self.cartridge = cartridge
        if cartridge is not None and cartridge.rom is not None:
            self.mirror_mode = cartridge.rom.mirroring

    cdef inline int _map_nt_addr(self, int addr):
        cdef int mode = self.mirror_mode
        if self.cartridge is not None and self.cartridge.mapper is not None:
             mode = self.cartridge.mapper.mirror_mode
             
        addr &= 0x0FFF
        if mode == 1: # VERTICAL: A B A B
            return addr & 0x07FF
        elif mode == 0: # HORIZONTAL: A A B B
            return (addr & 0x03FF) | ((addr & 0x0800) >> 1)
        elif mode == 2: # ONESCREEN_LO
            return addr & 0x03FF
        elif mode == 3: # ONESCREEN_HI
            return (addr & 0x03FF) | 0x0400
        return addr & 0x07FF
