import array
from .cartridge import Cartridge
from .rom import MirrorMode
from typing import Optional

class PPU:
    def __init__(self):
        self.cartridge: Optional[Cartridge] = None
        self.mirror_mode = MirrorMode.HORIZONTAL
        
        # PPU Internal Memory
        self.vram = array.array('B', bytearray(2048))
        self.palette_vram = array.array('B', bytearray(32))
        self.oam_vram = array.array('B', bytearray(256))
        
        # Output pixels (256x240)
        self.pixels = array.array('B', bytearray(256 * 240))
        
        # PPU Registers
        self.ppu_ctrl = 0
        self.ppu_mask = 0
        self.ppu_status = 0
        self.oam_addr = 0
        self.oam_data = 0
        
        # Loopy registers
        self.v = 0 
        self.t = 0 
        self.fine_x = 0 
        self.w = 0 
        
        self.ppu_data_buffer = 0
        
        # Rendering state
        self.scanline = 0
        self.cycle = 0
        self.nmi = False
        
        # Background fetch buffers
        self.bg_next_tile_id = 0
        self.bg_next_tile_attrib = 0
        self.bg_next_tile_lsb = 0
        self.bg_next_tile_msb = 0
        
        # Shift registers
        self.bg_shifter_tile_lo = 0
        self.bg_shifter_tile_hi = 0
        self.bg_shifter_attrib_lo = 0
        self.bg_shifter_attrib_hi = 0

        # Sprite Rendering
        self.secondary_oam = array.array('B', bytearray(32))
        self.sprite_count = 0
        self.sprite_shifter_pattern_lo = array.array('B', bytearray(8))
        self.sprite_shifter_pattern_hi = array.array('B', bytearray(8))
        self.sprite_attribs = array.array('B', bytearray(8))
        self.sprite_x_counters = array.array('B', bytearray(8))
        self.sprite_zero_hit_possible = False
        
        self.is_odd_frame = False

    def clock(self):
        # Odd frame cycle skip
        if self.scanline == -1 and self.cycle == 339 and (self.ppu_mask & 0x18) and self.is_odd_frame:
            self.cycle = 0
            self.scanline = 0
            self.is_odd_frame = not self.is_odd_frame
            return

        if self.scanline >= -1 and self.scanline <= 239:
            # Sprite evaluation and fetches
            if self.cycle == 257 and self.scanline >= 0:
                self._evaluate_sprites()
            
            if self.cycle == 340 and self.scanline >= -1:
                self._fetch_sprite_data()

            # Visible scanlines
            if self.cycle >= 1 and self.cycle <= 256:
                self._update_shifters()
                if self.scanline >= 0:
                    self._render_pixel()
                
                if self.cycle % 8 == 0:
                    self._load_shifters()
                    self._increment_scroll_x()
                elif self.cycle % 8 == 1: self._fetch_nt()
                elif self.cycle % 8 == 3: self._fetch_at()
                elif self.cycle % 8 == 5: self._fetch_pt_lo()
                elif self.cycle % 8 == 7: self._fetch_pt_hi()
            
            if self.cycle == 256:
                self._increment_scroll_y()
            elif self.cycle == 257:
                self._reset_scroll_x()
            
            # Pre-fetch for next scanline
            if self.cycle > 256 and self.cycle <= 336:
                 if self.cycle % 8 == 0:
                    self._load_shifters()
                    self._increment_scroll_x()
                 elif self.cycle % 8 == 1: self._fetch_nt()
                 elif self.cycle % 8 == 3: self._fetch_at()
                 elif self.cycle % 8 == 5: self._fetch_pt_lo()
                 elif self.cycle % 8 == 7: self._fetch_pt_hi()
            
            if self.scanline == -1 and self.cycle >= 280 and self.cycle <= 304:
                self._reset_scroll_y()

        self.cycle += 1
        if self.cycle >= 341:
            self.cycle = 0
            self.scanline += 1
            if self.scanline == 241:
                self.ppu_status |= 0x80
                if self.ppu_ctrl & 0x80: self.nmi = True
            if self.scanline >= 261:
                self.scanline = 0
                self.ppu_status &= ~0xC0 # Clear VBlank and Sprite 0 Hit
                self.nmi = False
                self.is_odd_frame = not self.is_odd_frame

    def _render_pixel(self):
        # Background pixel
        bg_pixel = 0
        bg_palette = 0
        if self.ppu_mask & 0x08:
            if self.cycle > 8 or (self.ppu_mask & 0x02):
                bit_mux = 0x8000 >> self.fine_x
                p0_pixel = (self.bg_shifter_tile_lo & bit_mux) > 0
                p1_pixel = (self.bg_shifter_tile_hi & bit_mux) > 0
                bg_pixel = (p1_pixel << 1) | p0_pixel
                
                bg_pal0 = (self.bg_shifter_attrib_lo & bit_mux) > 0
                bg_pal1 = (self.bg_shifter_attrib_hi & bit_mux) > 0
                bg_palette = (bg_pal1 << 1) | bg_pal0

        # Sprite pixel
        fg_pixel = 0
        fg_palette = 0
        fg_priority = 0
        sprite_zero_hit = False
        
        if self.ppu_mask & 0x10: # Sprite rendering enabled
            if self.cycle > 8 or (self.ppu_mask & 0x04):
                for i in range(self.sprite_count):
                    if self.sprite_x_counters[i] == 0:
                        pixel_lo = (self.sprite_shifter_pattern_lo[i] & 0x80) > 0
                        pixel_hi = (self.sprite_shifter_pattern_hi[i] & 0x80) > 0
                        fg_pixel = (pixel_hi << 1) | pixel_lo
                        fg_palette = (self.sprite_attribs[i] & 0x03) + 0x04
                        fg_priority = (self.sprite_attribs[i] & 0x20) == 0 # 0: in front, 1: behind
                        
                        if fg_pixel != 0:
                            if i == 0 and self.sprite_zero_hit_possible:
                                sprite_zero_hit = True
                            break

        # Priority Multiplexer
        pixel = 0
        palette = 0
        if bg_pixel == 0 and fg_pixel == 0:
            pixel = 0
            palette = 0
        elif bg_pixel == 0 and fg_pixel > 0:
            pixel = fg_pixel
            palette = fg_palette
        elif bg_pixel > 0 and fg_pixel == 0:
            pixel = bg_pixel
            palette = bg_palette
        else: # Both opaque
            if fg_priority:
                pixel = fg_pixel
                palette = fg_palette
            else:
                pixel = bg_pixel
                palette = bg_palette
            
            if sprite_zero_hit and (self.ppu_mask & 0x18) == 0x18:
                if self.cycle >= 1 and self.cycle <= 255:
                    if not (self.ppu_status & 0x40):
                         self.ppu_status |= 0x40
        
        color_idx = self.ppu_read(0x3F00 + (palette << 2) + pixel)
        if self.ppu_mask & 0x01: # Grayscale
            color_idx &= 0x30
            
        self.pixels[self.scanline * 256 + (self.cycle - 1)] = color_idx

    def _update_shifters(self):
        if self.ppu_mask & 0x08:
            self.bg_shifter_tile_lo = (self.bg_shifter_tile_lo << 1) & 0xFFFF
            self.bg_shifter_tile_hi = (self.bg_shifter_tile_hi << 1) & 0xFFFF
            self.bg_shifter_attrib_lo = (self.bg_shifter_attrib_lo << 1) & 0xFFFF
            self.bg_shifter_attrib_hi = (self.bg_shifter_attrib_hi << 1) & 0xFFFF

        if self.ppu_mask & 0x10 and self.cycle >= 1 and self.cycle <= 256:
            for i in range(self.sprite_count):
                if self.sprite_x_counters[i] > 0:
                    self.sprite_x_counters[i] -= 1
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
        if (self.v & 0x001F) == 31:
            self.v &= ~0x001F
            self.v ^= 0x0400
        else:
            self.v += 1

    def _increment_scroll_y(self):
        if not (self.ppu_mask & 0x18): return
        if (self.v & 0x7000) != 0x7000:
            self.v += 0x1000
        else:
            self.v &= ~0x7000
            y = (self.v & 0x03E0) >> 5
            if y == 29:
                y = 0
                self.v ^= 0x0800
            elif y == 31:
                y = 0
            else:
                y += 1
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
            diff = self.scanline - y
            if diff >= 0 and diff < sprite_size:
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
            y = self.secondary_oam[i * 4]; tile_id = self.secondary_oam[i * 4 + 1]
            attr = self.secondary_oam[i * 4 + 2]; x = self.secondary_oam[i * 4 + 3]
            row = self.scanline - y
            if attr & 0x80: row = (sprite_size - 1) - row
            if sprite_size == 8: addr = table * 0x1000 + tile_id * 16 + row
            else:
                table_16 = tile_id & 0x01; tile_idx = tile_id & 0xFE
                if row >= 8: tile_idx += 1; row -= 8
                addr = table_16 * 0x1000 + tile_idx * 16 + row
            lsb = self.ppu_read(addr); msb = self.ppu_read(addr + 8)
            if attr & 0x40:
                lsb = int('{:08b}'.format(lsb)[::-1], 2); msb = int('{:08b}'.format(msb)[::-1], 2)
            self.sprite_shifter_pattern_lo[i] = lsb; self.sprite_shifter_pattern_hi[i] = msb
            self.sprite_attribs[i] = attr; self.sprite_x_counters[i] = x

    def cpu_read(self, addr: int) -> int:
        reg = addr & 0x0007
        data = 0
        if reg == 0x02:
            data = (self.ppu_status & 0xE0); self.ppu_status &= ~0x80; self.w = 0
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

    def connect_cartridge(self, cartridge: Cartridge): self.cartridge = cartridge

    def ppu_read(self, addr: int) -> int:
        addr &= 0x3FFF
        if addr <= 0x1FFF: return self.cartridge.ppu_read(addr) if self.cartridge else 0
        elif addr <= 0x3EFF: return self.vram[self._map_nt_addr(addr)]
        elif addr <= 0x3FFF:
            addr &= 0x001F
            if addr in (0x10, 0x14, 0x18, 0x1C): addr -= 0x10
            return self.palette_vram[addr]
        return 0

    def ppu_write(self, addr: int, data: int):
        addr &= 0x3FFF
        if addr <= 0x1FFF:
            if self.cartridge: self.cartridge.ppu_write(addr, data)
        elif addr <= 0x3EFF: self.vram[self._map_nt_addr(addr)] = data & 0xFF
        elif addr <= 0x3FFF:
            addr &= 0x001F
            if addr in (0x10, 0x14, 0x18, 0x1C): addr -= 0x10
            self.palette_vram[addr] = data & 0xFF

    def _map_nt_addr(self, addr: int) -> int:
        addr &= 0x0FFF
        if self.mirror_mode == MirrorMode.VERTICAL: return addr & 0x07FF
        else:
            if addr < 0x0400: return addr
            if addr < 0x0800: return addr - 0x0400
            if addr < 0x0C00: return addr - 0x0400
            return addr - 0x0800
