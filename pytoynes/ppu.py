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

    def clock(self):
        if self.scanline >= -1 and self.scanline <= 239:
            # Visible scanlines
            if self.cycle >= 1 and self.cycle <= 256:
                self._update_shifters()
                if self.scanline >= 0:
                    self._render_pixel()
                
                if self.cycle % 8 == 0:
                    self._load_shifters()
                    self._increment_scroll_x()
                    self._fetch_next_tile_data_step()
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
                    self._fetch_next_tile_data_step()
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
                self.ppu_status &= ~0x80
                self.nmi = False

    def _render_pixel(self):
        if not (self.ppu_mask & 0x08): return # BG disabled
        
        bit_mux = 0x8000 >> self.fine_x
        p0_pixel = (self.bg_shifter_tile_lo & bit_mux) > 0
        p1_pixel = (self.bg_shifter_tile_hi & bit_mux) > 0
        pixel = (p1_pixel << 1) | p0_pixel
        
        bg_pal0 = (self.bg_shifter_attrib_lo & bit_mux) > 0
        bg_pal1 = (self.bg_shifter_attrib_hi & bit_mux) > 0
        palette = (bg_pal1 << 1) | bg_pal0
        
        # Color resolution
        # addr = 0x3F00 + palette << 2 + pixel
        color_idx = self.ppu_read(0x3F00 + (palette << 2) + pixel)
        self.pixels[self.scanline * 256 + (self.cycle - 1)] = color_idx

    def _update_shifters(self):
        if self.ppu_mask & 0x08:
            self.bg_shifter_tile_lo = (self.bg_shifter_tile_lo << 1) & 0xFFFF
            self.bg_shifter_tile_hi = (self.bg_shifter_tile_hi << 1) & 0xFFFF
            self.bg_shifter_attrib_lo = (self.bg_shifter_attrib_lo << 1) & 0xFFFF
            self.bg_shifter_attrib_hi = (self.bg_shifter_attrib_hi << 1) & 0xFFFF

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
    def _fetch_next_tile_data_step(self): pass

    def cpu_read(self, addr: int) -> int:
        reg = addr & 0x0007
        data = 0
        if reg == 0x0002:
            data = (self.ppu_status & 0xE0)
            self.ppu_status &= ~0x80
            self.w = 0
        elif reg == 0x0004: data = self.oam_vram[self.oam_addr]
        elif reg == 0x0007:
            data = self.ppu_data_buffer
            self.ppu_data_buffer = self.ppu_read(self.v)
            if self.v >= 0x3F00: data = self.ppu_data_buffer
            increment = 32 if (self.ppu_ctrl & 0x04) else 1
            self.v = (self.v + increment) & 0x7FFF
        return data

    def cpu_write(self, addr: int, data: int):
        reg = addr & 0x0007
        if reg == 0x0000:
            self.ppu_ctrl = data
            self.t = (self.t & 0x73FF) | ((data & 0x03) << 10)
        elif reg == 0x0001: self.ppu_mask = data
        elif reg == 0x0003: self.oam_addr = data
        elif reg == 0x0004:
            self.oam_vram[self.oam_addr] = data
            self.oam_addr = (self.oam_addr + 1) & 0xFF
        elif reg == 0x0005:
            if self.w == 0:
                self.t = (self.t & 0x7FE0) | ((data & 0xF8) >> 3)
                self.fine_x = data & 0x07
                self.w = 1
            else:
                self.t = (self.t & 0x0C1F) | ((data & 0x07) << 12) | ((data & 0xF8) << 2)
                self.w = 0
        elif reg == 0x0006:
            if self.w == 0:
                self.t = (self.t & 0x00FF) | ((data & 0x3F) << 8)
                self.w = 1
            else:
                self.t = (self.t & 0xFF00) | (data & 0xFF)
                self.v = self.t
                self.w = 0
        elif reg == 0x0007:
            self.ppu_write(self.v, data)
            increment = 32 if (self.ppu_ctrl & 0x04) else 1
            self.v = (self.v + increment) & 0x7FFF

    def get_pattern_pixel(self, table: int, tile_idx: int, x: int, y: int) -> int:
        base_addr = table * 0x1000 + tile_idx * 16
        low_byte = self.ppu_read(base_addr + y)
        high_byte = self.ppu_read(base_addr + y + 8)
        bit_pos = 7 - x
        return (((high_byte >> bit_pos) & 0x01) << 1) | ((low_byte >> bit_pos) & 0x01)

    def connect_cartridge(self, cartridge: Cartridge): self.cartridge = cartridge

    def ppu_read(self, addr: int) -> int:
        addr &= 0x3FFF
        if addr <= 0x1FFF:
            return self.cartridge.ppu_read(addr) if self.cartridge else 0
        elif addr <= 0x3EFF:
            return self.vram[self._map_nt_addr(addr)]
        elif addr <= 0x3FFF:
            addr &= 0x001F
            if addr in (0x10, 0x14, 0x18, 0x1C): addr -= 0x10
            return self.palette_vram[addr]
        return 0

    def ppu_write(self, addr: int, data: int):
        addr &= 0x3FFF
        if addr <= 0x1FFF:
            if self.cartridge: self.cartridge.ppu_write(addr, data)
        elif addr <= 0x3EFF:
            self.vram[self._map_nt_addr(addr)] = data & 0xFF
        elif addr <= 0x3FFF:
            addr &= 0x001F
            if addr in (0x10, 0x14, 0x18, 0x1C): addr -= 0x10
            self.palette_vram[addr] = data & 0xFF

    def _map_nt_addr(self, addr: int) -> int:
        addr &= 0x0FFF
        if self.mirror_mode == MirrorMode.VERTICAL:
            # Vertical mirroring: $2000 mirrors $2800, $2400 mirrors $2C00
            # Result is 0-2047
            return addr & 0x07FF
        else:
            # Horizontal mirroring: $2000 mirrors $2400, $2800 mirrors $2C00
            if addr >= 0 and addr < 0x0400: return addr # NT0
            if addr >= 0x0400 and addr < 0x0800: return addr - 0x0400 # NT1 -> NT0
            if addr >= 0x0800 and addr < 0x0C00: return addr - 0x0400 # NT2 -> NT1 (0x400-0x7FF)
            if addr >= 0x0C00 and addr < 0x1000: return addr - 0x0800 # NT3 -> NT1
        return 0
