import array
from .cartridge import Cartridge
from typing import Optional

class PPU:
    def __init__(self):
        self.cartridge: Optional[Cartridge] = None
        
        # PPU Internal Memory
        # Name Tables (2KB, usually mapped to 4KB with mirroring)
        self.vram = array.array('B', bytearray(2048))
        # Palette RAM (32 bytes)
        self.palette_vram = array.array('B', bytearray(32))
        # OAM (Object Attribute Memory) (256 bytes)
        self.oam_vram = array.array('B', bytearray(256))
        
        # PPU Registers
        self.ppu_ctrl = 0
        self.ppu_mask = 0
        self.ppu_status = 0
        self.oam_addr = 0
        self.oam_data = 0
        self.ppu_scroll = 0
        self.ppu_addr = 0
        self.ppu_data = 0
        
        # Internal registers for PPU address and scrolling
        self.ppu_addr_internal = 0
        self.address_latch = 0 # 0: high byte, 1: low byte
        self.ppu_data_buffer = 0
        
        # Rendering state
        self.scanline = 0
        self.cycle = 0
        self.nmi = False

    def clock(self):
        # Basic timing and VBlank
        self.cycle += 1
        
        if self.cycle >= 341:
            self.cycle = 0
            self.scanline += 1
            
            if self.scanline == 241:
                # Set VBlank flag in PPUSTATUS
                self.ppu_status |= 0x80
                # Trigger NMI if enabled in PPUCTRL
                if self.ppu_ctrl & 0x80:
                    self.nmi = True
            
            if self.scanline >= 261:
                self.scanline = 0
                # Clear VBlank and other flags
                self.ppu_status &= ~0x80
                self.nmi = False

    def cpu_read(self, addr: int) -> int:
        # Map 0x2000-0x3FFF to registers
        reg = addr & 0x0007
        data = 0
        
        if reg == 0x0000: # PPUCTRL (Write Only)
            pass
        elif reg == 0x0001: # PPUMASK (Write Only)
            pass
        elif reg == 0x0002: # PPUSTATUS
            # Read resets the address latch
            data = (self.ppu_status & 0xE0) # Top 3 bits
            self.ppu_status &= ~0x80 # Clear VBlank bit on read
            self.address_latch = 0
        elif reg == 0x0003: # OAMADDR (Write Only)
            pass
        elif reg == 0x0004: # OAMDATA
            pass
        elif reg == 0x0005: # PPUSCROLL (Write Only)
            pass
        elif reg == 0x0006: # PPUADDR (Write Only)
            pass
        elif reg == 0x0007: # PPUDATA
            # Reading from PPUDATA returns the previous content of the internal buffer
            # UNLESS the address is in the palette range ($3F00-$3FFF).
            data = self.ppu_data_buffer
            
            # Fetch new data into the buffer for the NEXT read
            # For addresses < $3F00, the buffer is updated with data from that address.
            # For addresses >= $3F00 (Palettes), the buffer is updated with the MIRRORED nametable data.
            if self.ppu_addr_internal >= 0x3F00:
                # Palettes: data returned immediately, buffer gets mirrored NT data
                data = self.ppu_read(self.ppu_addr_internal)
                # The mirrored NT data is at (addr - 0x1000) or simply addr & 0x2FFF
                self.ppu_data_buffer = self.ppu_read(self.ppu_addr_internal & 0x2FFF)
            else:
                # Normal VRAM: return buffer, update buffer with new data
                self.ppu_data_buffer = self.ppu_read(self.ppu_addr_internal)
                
            # Increment address
            increment = 32 if (self.ppu_ctrl & 0x04) else 1
            self.ppu_addr_internal = (self.ppu_addr_internal + increment) & 0x3FFF
            
        return data

    def cpu_write(self, addr: int, data: int):
        reg = addr & 0x0007
        
        if reg == 0x0000: # PPUCTRL
            self.ppu_ctrl = data
        elif reg == 0x0001: # PPUMASK
            self.ppu_mask = data
        elif reg == 0x0003: # OAMADDR
            self.oam_addr = data
        elif reg == 0x0004: # OAMDATA
            self.oam_data = data
        elif reg == 0x0005: # PPUSCROLL
            if self.address_latch == 0:
                # X Scroll
                self.address_latch = 1
            else:
                # Y Scroll
                self.address_latch = 0
        elif reg == 0x0006: # PPUADDR
            if self.address_latch == 0:
                self.ppu_addr_internal = (self.ppu_addr_internal & 0x00FF) | ((data & 0x3F) << 8)
                self.address_latch = 1
            else:
                self.ppu_addr_internal = (self.ppu_addr_internal & 0xFF00) | (data & 0xFF)
                self.address_latch = 0
        elif reg == 0x0007: # PPUDATA
            self.ppu_write(self.ppu_addr_internal, data)
            increment = 32 if (self.ppu_ctrl & 0x04) else 1
            self.ppu_addr_internal = (self.ppu_addr_internal + increment) & 0x3FFF

    def connect_cartridge(self, cartridge: Cartridge):
        self.cartridge = cartridge

    def ppu_read(self, addr: int) -> int:
        addr &= 0x3FFF
        
        if addr >= 0x0000 and addr <= 0x1FFF:
            # Pattern Tables (from Cartridge)
            if self.cartridge:
                return self.cartridge.ppu_read(addr)
        elif addr >= 0x2000 and addr <= 0x3EFF:
            # Name Tables (mapped to vram with basic mirroring)
            # For now, simple mirroring to 2KB
            return self.vram[addr & 0x07FF]
        elif addr >= 0x3F00 and addr <= 0x3FFF:
            # Palettes
            addr &= 0x001F
            # Palette mirroring ($3F10, $3F14, $3F18, $3F1C mirror $3F00, $3F04, $3F08, $3F0C)
            if addr == 0x0010: addr = 0x0000
            elif addr == 0x0014: addr = 0x0004
            elif addr == 0x0018: addr = 0x0008
            elif addr == 0x001C: addr = 0x000C
            return self.palette_vram[addr]
            
        return 0

    def ppu_write(self, addr: int, data: int):
        addr &= 0x3FFF
        
        if addr >= 0x0000 and addr <= 0x1FFF:
            # Pattern Tables (from Cartridge)
            if self.cartridge:
                self.cartridge.ppu_write(addr, data)
        elif addr >= 0x2000 and addr <= 0x3EFF:
            # Name Tables
            self.vram[addr & 0x07FF] = data & 0xFF
        elif addr >= 0x3F00 and addr <= 0x3FFF:
            # Palettes
            addr &= 0x001F
            if addr == 0x0010: addr = 0x0000
            elif addr == 0x0014: addr = 0x0004
            elif addr == 0x0018: addr = 0x0008
            elif addr == 0x001C: addr = 0x000C
            self.palette_vram[addr] = data & 0xFF
