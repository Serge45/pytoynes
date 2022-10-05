from .cartridge import Cartridge
import numpy as np
class V2C02:
    def __init__(self):
        self.on_ppu_clocked = None
        self.on_frame_completed = None
        self.cycle = 0
        self.scanline = 0
        self.frame_completed = False
        self.cartridge: Cartridge = None
        self.pal_screen = np.zeros((64, 3), dtype=np.uint8)
        self.palette = np.zeros((32,), dtype=np.uint8)
        self._init_pal_screen()

    def _init_pal_screen(self):
        self.pal_screen[0x00] = (84, 84, 84)
        self.pal_screen[0x01] = (0, 30, 116)
        self.pal_screen[0x02] = (8, 16, 144)
        self.pal_screen[0x03] = (48, 0, 136)
        self.pal_screen[0x04] = (68, 0, 100)
        self.pal_screen[0x05] = (92, 0, 48)
        self.pal_screen[0x06] = (84, 4, 0)
        self.pal_screen[0x07] = (60, 24, 0)
        self.pal_screen[0x08] = (32, 42, 0)
        self.pal_screen[0x09] = (8, 58, 0)
        self.pal_screen[0x0A] = (0, 64, 0)
        self.pal_screen[0x0B] = (0, 60, 0)
        self.pal_screen[0x0C] = (0, 50, 60)
        self.pal_screen[0x0D] = (0, 0, 0)
        self.pal_screen[0x0E] = (0, 0, 0)
        self.pal_screen[0x0F] = (0, 0, 0)

        self.pal_screen[0x10] = (152, 150, 152)
        self.pal_screen[0x11] = (8, 76, 196)
        self.pal_screen[0x12] = (48, 50, 236)
        self.pal_screen[0x13] = (92, 30, 228)
        self.pal_screen[0x14] = (136, 20, 176)
        self.pal_screen[0x15] = (160, 20, 100)
        self.pal_screen[0x16] = (152, 34, 32)
        self.pal_screen[0x17] = (120, 60, 0)
        self.pal_screen[0x18] = (84, 90, 0)
        self.pal_screen[0x19] = (40, 114, 0)
        self.pal_screen[0x1A] = (8, 124, 0)
        self.pal_screen[0x1B] = (0, 118, 40)
        self.pal_screen[0x1C] = (0, 102, 120)
        self.pal_screen[0x1D] = (0, 0, 0)
        self.pal_screen[0x1E] = (0, 0, 0)
        self.pal_screen[0x1F] = (0, 0, 0)

        self.pal_screen[0x20] = (236, 238, 236)
        self.pal_screen[0x21] = (76, 154, 236)
        self.pal_screen[0x22] = (120, 124, 236)
        self.pal_screen[0x23] = (176, 98, 236)
        self.pal_screen[0x24] = (228, 84, 236)
        self.pal_screen[0x25] = (236, 88, 180)
        self.pal_screen[0x26] = (236, 106, 100)
        self.pal_screen[0x27] = (212, 136, 32)
        self.pal_screen[0x28] = (160, 170, 0)
        self.pal_screen[0x29] = (116, 196, 0)
        self.pal_screen[0x2A] = (76, 208, 32)
        self.pal_screen[0x2B] = (56, 204, 108)
        self.pal_screen[0x2C] = (56, 180, 204)
        self.pal_screen[0x2D] = (60, 60, 60)
        self.pal_screen[0x2E] = (0, 0, 0)
        self.pal_screen[0x2F] = (0, 0, 0)

        self.pal_screen[0x30] = (236, 238, 236)
        self.pal_screen[0x31] = (168, 204, 236)
        self.pal_screen[0x32] = (188, 188, 236)
        self.pal_screen[0x33] = (212, 178, 236)
        self.pal_screen[0x34] = (236, 174, 236)
        self.pal_screen[0x35] = (236, 174, 212)
        self.pal_screen[0x36] = (236, 180, 176)
        self.pal_screen[0x37] = (228, 196, 144)
        self.pal_screen[0x38] = (204, 210, 120)
        self.pal_screen[0x39] = (180, 222, 120)
        self.pal_screen[0x3A] = (168, 226, 144)
        self.pal_screen[0x3B] = (152, 226, 180)
        self.pal_screen[0x3C] = (160, 214, 228)
        self.pal_screen[0x3D] = (160, 162, 160)
        self.pal_screen[0x3E] = (0, 0, 0)
        self.pal_screen[0x3F] = (0, 0, 0)

    def read(self, addr: int) -> int:
        '''
        Read from PPU bus
        '''
        addr &= 0x3FFF

        if self.cartridge:
            c_data = self.cartridge.ppu_read(addr)

            if c_data is not None:
                return c_data

    def write(self, addr: int, data: int) -> int:
        '''
        Write to PPU bus
        '''
        addr &= 0x3FFF

        if self.cartridge:
            c_data = self.cartridge.ppu_write(addr, data)

            if c_data is not None:
                return c_data

    def getColor(self, palette: int, pixel: int) -> np.ndarray:
        addr = (0x3F00 + palette * 4 + pixel) & 0x3F
        return self.read(addr)

    def clock(self):
        self.cycle += 1
        self.on_ppu_clocked(self.cycle, self.scanline)

        if self.cycle >= 341:
            self.cycle = 0
            self.scanline += 1

            if self.scanline >= 261:
                self.scanline = -1
                self.frame_completed = True

                if self.on_frame_completed:
                    self.on_frame_completed()
