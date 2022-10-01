from array import array
import os
from threading import Thread
import pygame
from pytoynes.bus import Bus
from pytoynes.rom import Rom 
from pytoynes.mos6502 import MOS6502
from pytoynes.ui.memoryview import draw_memory_view, draw_status_bits, draw_program_counter, draw_registers

def main():
    cpu = MOS6502()
    bus = Bus()
    cpu.connect(bus)
    test_rom = Rom('./pytoynes/assets/nestest.nes')
    program = array('B', test_rom.prg_rom_data)
    bus.ram[0x8000:0xBFFF] = program
    bus.ram[0xC000:0xFFFF] = program
    cpu.pc = 0xC000
    pygame.init()

    window_size = w, h = 640, 480
    screen = pygame.display.set_mode(window_size)
    window_rect = pygame.Rect(0, 0, w, h)
    memory_view_rect = pygame.Rect(0, 0, w - 128, h - 128)
    status_bits_rect = pygame.Rect(w - 128, 0, 128, 64)
    pc_rect = pygame.Rect(w - 128, 64, 128, 32)
    register_rect = pygame.Rect(w - 128, 64 + 32, 128, 64)
    font = pygame.font.SysFont(None, 16)
    clock = pygame.time.Clock()
    cpu_running = True

    def cpu_thread_body():
        nonlocal cpu
        cycle = 0

        while cpu_running is True:
            cpu.clock()
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

        screen.fill((0, 0, 0))
        draw_memory_view(bus, memory_view_rect, 0x0200, screen, font)
        draw_status_bits(cpu, status_bits_rect, screen, font)
        draw_program_counter(cpu, pc_rect, screen, font)
        draw_registers(cpu, register_rect, screen, font)
        pygame.display.flip()
        clock.tick(60)

if __name__ == '__main__':
    main()
