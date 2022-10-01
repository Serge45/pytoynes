import array

class Bus:
    def __init__(self):
        self.ram = array.array('B', bytearray(2*1024))

    def write(self, addr, data):
        self.ram[addr & 0x07FF] = data & 0xFF

    def read(self, addr):
        return self.ram[addr & 0x07FF]
