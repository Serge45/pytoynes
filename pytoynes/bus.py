import array

class Bus:
    def __init__(self):
        self.ram = array.array('B', bytearray(64*1024))

    def write(self, addr, data):
        self.ram[addr] = data

    def read(self, addr):
        return self.ram[addr]
