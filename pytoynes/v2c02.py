class V2C02:
    def __init__(self):
        self.on_ppu_clocked = None
        self.cycle = 0
        self.scanline = 0

    def clock(self):
        self.cycle += 1
        self.on_ppu_clocked(self.cycle, self.scanline)

        if self.cycle >= 341:
            self.cycle = 0
            self.scanline += 1

            if self.scanline >= 261:
                self.scanline = -1
