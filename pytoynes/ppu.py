import array
import numpy as np
from .cartridge import Cartridge
from .rom import MirrorMode
from typing import Optional

_TILE_DECODE = [None] * 65536
for _lo in range(256):
    for _hi in range(256):
        _TILE_DECODE[_lo | (_hi << 8)] = bytes(
            ((_hi >> (7 - _p)) & 1) << 1 | ((_lo >> (7 - _p)) & 1) for _p in range(8)
        )

class PPU:
    def __init__(self):
        self.cartridge: Optional[Cartridge] = None
        self.mirror_mode = 0 # Default HORIZONTAL
        
        self.vram = array.array('B', bytearray(2048))
        self.palette_vram = array.array('B', bytearray(32))
        self.oam_vram = array.array('B', bytearray(256))
        
        self.pixels = np.zeros((240, 256), dtype=np.uint8)
        
        self._bg_pixels = np.zeros(256, dtype=np.uint8)
        self._bg_palettes = np.zeros(256, dtype=np.uint8)
        self._fg_pixels = np.zeros(256, dtype=np.uint8)
        self._fg_palettes = np.zeros(256, dtype=np.uint8)
        self._fg_priorities = np.zeros(256, dtype=np.uint8)
        self._sprite0_possible = np.zeros(256, dtype=np.uint8)

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

    def clock(self):
        scanline = self.scanline
        cycle = self.cycle

        if -1 <= scanline <= 239:
            if cycle == 257:
                if scanline >= -1: self._evaluate_sprites()
            elif cycle == 340:
                if scanline >= -1: self._fetch_sprite_data()

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
            if self.cartridge is not None:
                self.cartridge.mapper.count_scanline()
            self.cycle = 0
            self.scanline += 1
            scanline = self.scanline
            if scanline == 241:
                self.ppu_status |= 0x80
                if self.ppu_ctrl & 0x80: self.nmi = True
            elif scanline >= 261:
                self.scanline = -1
                self.frame_count += 1
                self.ppu_status &= ~0xC0
                self.nmi = False
                self.is_odd_frame = not self.is_odd_frame
                if self.scanline == -1 and (self.ppu_mask & 0x18) and self.is_odd_frame:
                    self.cycle = 1
                    self.total_cycles += 1

    def run_to(self, target_total_cycles: int):
        while self.total_cycles < target_total_cycles:
            self.clock()

    def _render_scanline_fast(self):
        ppu_mask = self.ppu_mask
        scanline = self.scanline
        vram = self.vram
        map_nt = self._map_nt_addr
        bg_pixels = self._bg_pixels
        bg_palettes = self._bg_palettes
        tile_decode = _TILE_DECODE

        bg_pixels.fill(0)
        bg_palettes.fill(0)

        if ppu_mask & 0x08:
            v = (self.v & ~0x041F) | (self.t & 0x041F)
            fine_x = self.fine_x
            table = (self.ppu_ctrl >> 4) & 0x01
            fine_y = (v >> 12) & 0x07
            left_clip = not (ppu_mask & 0x02)

            for t in range(33):
                tile_id = vram[map_nt(0x2000 | (v & 0x0FFF))]
                attr = vram[map_nt(0x23C0 | (v & 0x0C00) | ((v >> 4) & 0x38) | ((v >> 2) & 0x07))]
                if (v >> 6) & 0x01: attr >>= 4
                if (v >> 1) & 0x01: attr >>= 2
                pal_idx = attr & 0x03

                pt_addr = (table << 12) | (tile_id << 4) | fine_y
                lsb = self.ppu_read(pt_addr)
                msb = self.ppu_read(pt_addr + 8)

                base_x = t * 8 - fine_x
                for p in range(8):
                    pixel_x = base_x + p
                    if 0 <= pixel_x < 256:
                        if not (left_clip and pixel_x < 8):
                            bit_pos = 7 - p
                            px = (((msb >> bit_pos) & 1) << 1) | ((lsb >> bit_pos) & 1)
                            if px:
                                bg_pixels[pixel_x] = px
                                bg_palettes[pixel_x] = pal_idx

                if (v & 0x001F) == 31: v = (v & ~0x001F) ^ 0x0400
                else: v += 1

        fg_pixels = self._fg_pixels
        fg_palettes = self._fg_palettes
        fg_priorities = self._fg_priorities
        sprite0_possible = self._sprite0_possible
        fg_pixels.fill(0)
        fg_palettes.fill(0)
        fg_priorities.fill(0)
        sprite0_possible.fill(0)

        if ppu_mask & 0x10:
            self._evaluate_sprites()
            self._fetch_sprite_data()
            left_clip_spr = not (ppu_mask & 0x04)

            for i in range(self.sprite_count - 1, -1, -1):
                attr = self.sprite_attribs[i]
                x = self.sprite_x_counters[i]
                lsb = self.sprite_shifter_pattern_lo[i]
                msb = self.sprite_shifter_pattern_hi[i]
                pal = (attr & 0x03) + 0x04
                priority = (attr & 0x20) == 0
                is_sprite0 = i == 0 and self.sprite_zero_hit_possible

                for p in range(8):
                    pixel_x = x + p + 1
                    if pixel_x < 256:
                        if not (left_clip_spr and pixel_x < 8):
                            bit_pos = 7 - p
                            px = (((msb >> bit_pos) & 1) << 1) | ((lsb >> bit_pos) & 1)
                            if px:
                                fg_pixels[pixel_x] = px
                                fg_palettes[pixel_x] = pal
                                fg_priorities[pixel_x] = 1 if priority else 0
                                if is_sprite0:
                                    sprite0_possible[pixel_x] = 1

        bg_opaque = bg_pixels > 0
        fg_opaque = fg_pixels > 0
        
        if (ppu_mask & 0x18) == 0x18 and self.sprite_zero_hit_possible:
            hit_mask = bg_opaque & fg_opaque & (sprite0_possible > 0)
            if hit_mask[:255].any(): self.ppu_status |= 0x40

        final_pixel = np.zeros(256, dtype=np.uint8)
        final_palette = np.zeros(256, dtype=np.uint8)
        final_pixel[bg_opaque] = bg_pixels[bg_opaque]
        final_palette[bg_opaque] = bg_palettes[bg_opaque]
        
        fg_overwrites = fg_opaque & (~bg_opaque | (fg_priorities > 0))
        final_pixel[fg_overwrites] = fg_pixels[fg_overwrites]
        final_palette[fg_overwrites] = fg_palettes[fg_overwrites]

        out_pixels = np.full(256, self.palette_vram[0], dtype=np.uint8)
        mask = final_pixel > 0
        if mask.any():
            pal_indices = (final_palette[mask].astype(np.uint16) << 2) + final_pixel[mask]
            mirror_mask = (pal_indices & 0x13) == 0x10
            pal_indices[mirror_mask] &= 0xFFEF
            pal_vram_np = np.frombuffer(self.palette_vram, dtype=np.uint8)
            out_pixels[mask] = pal_vram_np[pal_indices & 0x1F]

        if ppu_mask & 0x01: out_pixels &= 0x30
        self.pixels[scanline] = out_pixels

        if ppu_mask & 0x18:
            self._increment_scroll_y()
            self._reset_scroll_x()
            self._increment_scroll_x()
            self._increment_scroll_x()

    def _render_pixel(self):
        ppu_mask = self.ppu_mask
        cycle = self.cycle
        bg_pixel = 0
        bg_palette = 0
        if ppu_mask & 0x08:
            if cycle > 8 or (ppu_mask & 0x02):
                bit_mux = 0x8000 >> self.fine_x
                p0_pixel = (self.bg_shifter_tile_lo & bit_mux) > 0
                p1_pixel = (self.bg_shifter_tile_hi & bit_mux) > 0
                bg_pixel = (p1_pixel << 1) | p0_pixel
                bg_pal0 = (self.bg_shifter_attrib_lo & bit_mux) > 0
                bg_pal1 = (self.bg_shifter_attrib_hi & bit_mux) > 0
                bg_palette = (bg_pal1 << 1) | bg_pal0

        fg_pixel = 0
        fg_palette = 0
        fg_priority = 0
        sprite_zero_hit = False
        
        if ppu_mask & 0x10:
            if cycle > 8 or (ppu_mask & 0x04):
                for i in range(self.sprite_count):
                    if self.sprite_x_counters[i] == 0:
                        pixel_lo = (self.sprite_shifter_pattern_lo[i] & 0x80) > 0
                        pixel_hi = (self.sprite_shifter_pattern_hi[i] & 0x80) > 0
                        fg_pixel = (pixel_hi << 1) | pixel_lo
                        if fg_pixel != 0:
                            fg_palette = (self.sprite_attribs[i] & 0x03) + 0x04
                            fg_priority = (self.sprite_attribs[i] & 0x20) == 0
                            if i == 0 and self.sprite_zero_hit_possible:
                                sprite_zero_hit = True
                            break

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
        self.pixels[self.scanline, self.cycle - 1] = color_idx

    def _update_shifters(self):
        ppu_mask = self.ppu_mask
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

    def _load_shifters(self):
        self.bg_shifter_tile_lo = (self.bg_shifter_tile_lo & 0xFF00) | self.bg_next_tile_lsb
        self.bg_shifter_tile_hi = (self.bg_shifter_tile_hi & 0xFF00) | self.bg_next_tile_msb
        self.bg_shifter_attrib_lo = (self.bg_shifter_attrib_lo & 0xFF00) | (0xFF if (self.bg_next_tile_attrib & 0x01) else 0x00)
        self.bg_shifter_attrib_hi = (self.bg_shifter_attrib_hi & 0xFF00) | (0xFF if (self.bg_next_tile_attrib & 0x02) else 0x00)

    def _increment_scroll_x(self):
        if not (self.ppu_mask & 0x18): return
        if (self.v & 0x001F) == 31: self.v &= ~0x001F; self.v ^= 0x0400
        else: self.v += 1

    def _increment_scroll_y(self):
        if not (self.ppu_mask & 0x18): return
        if (self.v & 0x7000) != 0x7000: self.v += 0x1000
        else:
            self.v &= ~0x7000
            y = (self.v & 0x03E0) >> 5
            if y == 29: y = 0; self.v ^= 0x0800
            elif y == 31: y = 0
            else: y += 1
            self.v = (self.v & ~0x03E0) | (y << 5)

    def _reset_scroll_x(self):
        if not (self.ppu_mask & 0x18): return
        self.v = (self.v & ~0x041F) | (self.t & 0x041F)

    def _reset_scroll_y(self):
        if not (self.ppu_mask & 0x18): return
        self.v = (self.v & ~0x7BE0) | (self.t & 0x7BE0)

    def _fetch_nt(self): self.bg_next_tile_id = self.ppu_read(0x2000 | (self.v & 0x0FFF))
    def _fetch_at(self):
        v = self.v
        at_addr = 0x23C0 | (v & 0x0C00) | ((v >> 4) & 0x38) | ((v >> 2) & 0x07)
        self.bg_next_tile_attrib = self.ppu_read(at_addr)
        if (v >> 6) & 0x01: self.bg_next_tile_attrib >>= 4
        if (v >> 1) & 0x01: self.bg_next_tile_attrib >>= 2
        self.bg_next_tile_attrib &= 0x03
    def _fetch_pt_lo(self):
        table = (self.ppu_ctrl >> 4) & 0x01
        fine_y = (self.v >> 12) & 0x07
        self.bg_next_tile_lsb = self.ppu_read(table * 0x1000 + self.bg_next_tile_id * 16 + fine_y)
    def _fetch_pt_hi(self):
        table = (self.ppu_ctrl >> 4) & 0x01
        fine_y = (self.v >> 12) & 0x07
        self.bg_next_tile_msb = self.ppu_read(table * 0x1000 + self.bg_next_tile_id * 16 + fine_y + 8)

    def _evaluate_sprites(self):
        self.sprite_count = 0
        self.sprite_zero_hit_possible = False
        sprite_size = 16 if (self.ppu_ctrl & 0x20) else 8
        for i in range(64):
            y = self.oam_vram[i * 4]
            diff = self.scanline - (y + 1)
            if 0 <= diff < sprite_size:
                if self.sprite_count < 8:
                    if i == 0: self.sprite_zero_hit_possible = True
                    for j in range(4):
                        self.secondary_oam[self.sprite_count * 4 + j] = self.oam_vram[i * 4 + j]
                    self.sprite_count += 1
                else:
                    self.ppu_status |= 0x20
                    break

    def _fetch_sprite_data(self):
        sprite_size = 16 if (self.ppu_ctrl & 0x20) else 8
        table = (self.ppu_ctrl >> 3) & 0x01
        for i in range(self.sprite_count):
            y = self.secondary_oam[i * 4]
            tile_id = self.secondary_oam[i * 4 + 1]
            attr = self.secondary_oam[i * 4 + 2]
            x = self.secondary_oam[i * 4 + 3]
            row = self.scanline - (y + 1)
            if attr & 0x80: row = (sprite_size - 1) - row
            if sprite_size == 8:
                addr = table * 0x1000 + tile_id * 16 + row
            else:
                table_16 = tile_id & 0x01
                tile_idx = tile_id & 0xFE
                if row >= 8: tile_idx += 1; row -= 8
                addr = table_16 * 0x1000 + tile_idx * 16 + row
            lsb = self.ppu_read(addr)
            msb = self.ppu_read(addr + 8)
            if attr & 0x40:
                lsb = int('{:08b}'.format(lsb)[::-1], 2)
                msb = int('{:08b}'.format(msb)[::-1], 2)
            self.sprite_shifter_pattern_lo[i] = lsb
            self.sprite_shifter_pattern_hi[i] = msb
            self.sprite_attribs[i] = attr
            self.sprite_x_counters[i] = x

    def cpu_read(self, addr: int) -> int:
        reg = addr & 0x0007
        data = 0
        if reg == 0x02:
            data = self.ppu_status & 0xE0; self.ppu_status &= ~0x80; self.w = 0
        elif reg == 0x04: data = self.oam_vram[self.oam_addr]
        elif reg == 0x07:
            data = self.ppu_data_buffer; self.ppu_data_buffer = self.ppu_read(self.v)
            if self.v >= 0x3F00: data = self.ppu_data_buffer
            self.v = (self.v + (32 if (self.ppu_ctrl & 0x04) else 1)) & 0x7FFF
        return data

    def cpu_write(self, addr: int, data: int):
        reg = addr & 0x0007
        if reg == 0x00: self.ppu_ctrl = data; self.t = (self.t & 0x73FF) | ((data & 0x03) << 10)
        elif reg == 0x01: self.ppu_mask = data
        elif reg == 0x03: self.oam_addr = data
        elif reg == 0x04: self.oam_vram[self.oam_addr] = data; self.oam_addr = (self.oam_addr + 1) & 0xFF
        elif reg == 0x05:
            if self.w == 0: self.t = (self.t & 0x7FE0) | ((data & 0xF8) >> 3); self.fine_x = data & 0x07; self.w = 1
            else: self.t = (self.t & 0x0C1F) | ((data & 0x07) << 12) | ((data & 0xF8) << 2); self.w = 0
        elif reg == 0x06:
            if self.w == 0: self.t = (self.t & 0x00FF) | ((data & 0x3F) << 8); self.w = 1
            else: self.t = (self.t & 0xFF00) | (data & 0xFF); self.v = self.t; self.w = 0
        elif reg == 0x07:
            self.ppu_write(self.v, data)
            self.v = (self.v + (32 if (self.ppu_ctrl & 0x04) else 1)) & 0x7FFF

    def get_pattern_pixel(self, table: int, tile_idx: int, x: int, y: int) -> int:
        base_addr = table * 0x1000 + tile_idx * 16
        low_byte = self.ppu_read(base_addr + y)
        high_byte = self.ppu_read(base_addr + y + 8)
        bit_pos = 7 - x
        return (((high_byte >> bit_pos) & 0x01) << 1) | ((low_byte >> bit_pos) & 0x01)

    def connect_cartridge(self, cartridge: Cartridge):
        self.cartridge = cartridge

    def ppu_read(self, addr: int) -> int:
        addr &= 0x3FFF
        if addr <= 0x1FFF: return self.cartridge.ppu_read(addr)
        elif addr <= 0x3EFF: return self.vram[self._map_nt_addr(addr)]
        else:
            addr &= 0x001F
            if (addr & 0x13) == 0x10: addr &= ~0x10
            return self.palette_vram[addr]

    def ppu_write(self, addr: int, data: int):
        addr &= 0x3FFF
        if addr <= 0x1FFF: self.cartridge.ppu_write(addr, data)
        elif addr <= 0x3EFF: self.vram[self._map_nt_addr(addr)] = data & 0xFF
        else:
            addr &= 0x001F
            if (addr & 0x13) == 0x10: addr &= ~0x10
            self.palette_vram[addr] = data & 0x3F

    def _map_nt_addr(self, addr: int) -> int:
        mode = self.mirror_mode
        if self.cartridge is not None and self.cartridge.mapper is not None:
             mode = self.cartridge.mapper.mirror_mode
             
        addr &= 0x0FFF
        if mode == 1: # VERTICAL
            return addr & 0x07FF
        elif mode == 0: # HORIZONTAL
            if addr < 0x0400: return addr
            if addr < 0x0800: return addr - 0x0400
            if addr < 0x0C00: return addr - 0x0400
            return addr - 0x0800
        elif mode == 2: # ONESCREEN_LO
            return addr & 0x03FF
        elif mode == 3: # ONESCREEN_HI
            return 0x0400 | (addr & 0x03FF)
        return addr & 0x07FF
