from threading import Thread
import pygame
import sys
from pytoynes.bus import Bus
from pytoynes.rom import Rom 
from pytoynes.mos6502 import MOS6502
from pytoynes.cartridge import Cartridge
from pytoynes.ui.memoryview import draw_memory_view, draw_status_bits, draw_program_counter, draw_registers, draw_pattern_table, draw_ppu_screen
from pytoynes.controller import *

def main():
    rom_path = './pytoynes/assets/nestest.nes'
    if len(sys.argv) > 1:
        rom_path = sys.argv[1]

    cpu = MOS6502()
    bus = Bus()
    cpu.connect(bus)
    
    try:
        cartridge = Cartridge(rom_path)
    except FileNotFoundError:
        print(f"Error: ROM file not found: {rom_path}")
        return

    bus.cartridge = cartridge
    bus.ppu.connect_cartridge(cartridge)
    bus.ppu.ppu_mask = 0x1E # Enable BG and Sprites
    
    # Initialize CPU
    cpu.reset()
    if 'nestest.nes' in rom_path:
        cpu.pc = 0xC000 # Specific entry for nestest automation
    
    pygame.init()

    window_size = w, h = 1024, 768
    screen = pygame.display.set_mode(window_size)
    pygame.display.set_caption(f"Pytoynes - {rom_path}")
    
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
        while cpu_running is True:
            cpu.clock()
            # PPU clocks 3 times for every CPU clock (NTSC)
            for _ in range(3):
                bus.ppu.clock()
            
            if bus.ppu.nmi:
                bus.ppu.nmi = False
                cpu.nmi()

    cpu_thread = Thread(target=cpu_thread_body)
    cpu_thread.start()

    key_map = {
        pygame.K_z: BUTTON_A,
        pygame.K_x: BUTTON_B,
        pygame.K_RSHIFT: BUTTON_SELECT,
        pygame.K_RETURN: BUTTON_START,
        pygame.K_UP: BUTTON_UP,
        pygame.K_DOWN: BUTTON_DOWN,
        pygame.K_LEFT: BUTTON_LEFT,
        pygame.K_RIGHT: BUTTON_RIGHT
    }

    while True:
        events = pygame.event.get()

        for e in events:
            if e.type == pygame.QUIT:
                cpu_running = False
                cpu_thread.join()
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN:
                if e.unicode == 'd':
                    print(f'0x0002: {bus.ram[0x0002]:04x}, 0x0003: {bus.ram[0x0003]:04x}')
                elif e.unicode == 'q':
                    cpu_running = False
                    cpu_thread.join()
                    pygame.quit()
                    return
                if e.key in key_map:
                    bus.controllers[0].set_button(key_map[e.key], True)
            if e.type == pygame.KEYUP:
                if e.key in key_map:
                    bus.controllers[0].set_button(key_map[e.key], False)

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
