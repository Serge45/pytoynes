from threading import Thread
import pygame
from pytoynes.bus import Bus
from pytoynes.mos6502 import MOS6502
from pytoynes.cartridge import Cartridge
from pytoynes.ui.memoryview import draw_memory_view, draw_status_bits, draw_program_counter, draw_registers
from random import randint

def main():
    bus = Bus()
    cartridge = Cartridge('./pytoynes/assets/nestest.nes')
    bus.cartridge = cartridge
    bus.cpu.pc = 0xC000
    pygame.init()

    window_size = w, h = 640, 480
    screen = pygame.display.set_mode(window_size)
    memory_view_rect = pygame.Rect(0, 0, w - 128, h - 128)
    status_bits_rect = pygame.Rect(w - 128, 0, 128, 64)
    pc_rect = pygame.Rect(w - 128, 64, 128, 32)
    register_rect = pygame.Rect(w - 128, 64 + 32, 128, 64)
    font = pygame.font.SysFont(None, 16)
    clock = pygame.time.Clock()
    cpu_running = True

    def on_ppu_clocked(clock: int, scanline: int):
        nonlocal screen
        rand = randint(0, 1)
        color = (236, 238, 236) if rand % 2 else (0, 0, 0)
        screen.set_at((clock, scanline), color)

    bus.ppu.on_ppu_clocked = on_ppu_clocked

    def cpu_thread_body():
        nonlocal bus
        cycle = 0

        while cpu_running is True:
            bus.clock()
            cycle += 1

    cpu_thread = Thread(target=cpu_thread_body)
    cpu_thread.start()

    while True:
        events = pygame.event.get()

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.unicode == 'd':
                    print(f'0x0002: {bus.ram[0x0002]:04x}, 0x0003: {bus.ram[0x0003]:04x}')
                elif e.unicode == 'q':
                    cpu_running = False
                    cpu_thread.join()
                    pygame.quit()
                    return

        #screen.fill((0, 0, 0))
        #draw_memory_view(bus, memory_view_rect, 0x0200, screen, font)
        screen.fill((0, 0, 0), status_bits_rect)
        screen.fill((0, 0, 0), pc_rect)
        screen.fill((0, 0, 0), register_rect)
        draw_status_bits(bus.cpu, status_bits_rect, screen, font)
        draw_program_counter(bus.cpu, pc_rect, screen, font)
        draw_registers(bus.cpu, register_rect, screen, font)
        pygame.display.flip()
        clock.tick(60)

if __name__ == '__main__':
    main()
