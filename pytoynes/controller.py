class Controller:
    def __init__(self):
        self.state = 0x00
        self.snapshot = 0x00
        self.strobe = False

    def set_button(self, button_mask, pressed):
        if pressed:
            self.state |= button_mask
        else:
            self.state &= ~button_mask

    def write(self, data):
        self.strobe = (data & 0x01) > 0
        if self.strobe:
            self.snapshot = self.state

    def read(self):
        if self.strobe:
            # While strobe is high, return status of A button
            return (self.state & 0x01) > 0
        
        # Return the current button in the sequence and shift
        data = (self.snapshot & 0x01) > 0
        self.snapshot >>= 1
        # NES controller returns 1s after all 8 buttons are read
        self.snapshot |= 0x80 
        return data

# Button Masks
BUTTON_A      = 0x01
BUTTON_B      = 0x02
BUTTON_SELECT = 0x04
BUTTON_START  = 0x08
BUTTON_UP     = 0x10
BUTTON_DOWN   = 0x20
BUTTON_LEFT   = 0x40
BUTTON_RIGHT  = 0x80
