from threading import Thread
import pygame
from pytoynes.bus import Bus
from pytoynes.rom import Rom 
from pytoynes.mos6502 import MOS6502
from pytoynes.cartridge import Cartridge
from pytoynes.ui.memoryview import draw_memory_view, draw_status_bits, draw_program_counter, draw_registers, draw_pattern_table, draw_ppu_screen

def main():
    cpu = MOS6502()
    bus = Bus()
    cpu.connect(bus)
    cartridge = Cartridge('./pytoynes/assets/nestest.nes')
    bus.cartridge = cartridge
    bus.ppu.connect_cartridge(cartridge)
    bus.ppu.ppu_mask = 0x08 # Enable background rendering
    cpu.pc = 0xC000
    pygame.init()

    window_size = w, h = 1024, 768
    screen = pygame.display.set_mode(window_size)
    memory_view_rect = pygame.Rect(0, 0, 400, 300)
    status_bits_rect = pygame.Rect(420, 0, 128, 64)
    pc_rect = pygame.Rect(420, 64, 128, 32)
    register_rect = pygame.Rect(420, 64 + 32, 128, 64)
    ppu_screen_rect = pygame.Rect(560, 0, 256*2, 240*2)
    pattern_table_0_rect = pygame.Rect(0, 320, 256, 256)
    pattern_table_1_rect = pygame.Rect(270, 320, 256, 256)
    
    font = pygame.font.SysFont(None, 16)
    clock = pygame.time.Clock()
    cpu_running = True

    def cpu_thread_body():
        nonlocal cpu
        cycle = 0

        while cpu_running is True:
            cpu.clock()
            # PPU clocks 3 times for every CPU clock (NTSC)
            for _ in range(3):
                bus.ppu.clock()
            
            if bus.ppu.nmi:
                bus.ppu.nmi = False
                cpu.nmi()
            
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
        draw_memory_view(bus, memory_view_rect, 0x0000, screen, font)
        draw_status_bits(cpu, status_bits_rect, screen, font)
        draw_program_counter(cpu, pc_rect, screen, font)
        draw_registers(cpu, register_rect, screen, font)
        draw_pattern_table(bus, 0, pattern_table_0_rect, screen)
        draw_pattern_table(bus, 1, pattern_table_1_rect, screen)
        draw_ppu_screen(bus, ppu_screen_rect, screen)
        pygame.display.flip()
        clock.tick(60)

if __name__ == '__main__':
    main()
