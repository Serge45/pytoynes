from threading import Thread
import time
import pygame
import sys
from pytoynes.bus import Bus
from pytoynes.rom import Rom 
from pytoynes.mos6502 import MOS6502
from pytoynes.cartridge import Cartridge
from pytoynes.ui.memoryview import draw_memory_view, draw_status_bits, draw_program_counter, draw_registers, draw_pattern_table, draw_ppu_screen, draw_fps
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
    bus.ppu.ppu_mask = 0x1E # Enable BG and Sprites
    
    # Initialize CPU
    cpu.reset()
    # Read reset vector from 0xFFFC
    lo = bus.read(0xFFFC)
    hi = bus.read(0xFFFD)
    cpu.pc = (hi << 8) | lo
    
    pygame.init()

    window_size = w, h = 1200, 800
    screen = pygame.display.set_mode(window_size)
    pygame.display.set_caption(f"Pytoynes - {rom_path}")
    
    memory_view_rect = pygame.Rect(780, 0, 400, 300)
    status_bits_rect = pygame.Rect(780, 310, 128, 64)
    pc_rect = pygame.Rect(780, 374, 128, 32)
    register_rect = pygame.Rect(780, 406, 128, 64)
    fps_rect = pygame.Rect(780, 470, 128, 32)
    # Using 3x scale for PPU screen (256*3=768, 240*3=720)
    ppu_screen_rect = pygame.Rect(0, 0, 768, 720)
    pattern_table_0_rect = pygame.Rect(780, 510, 200, 200)
    pattern_table_1_rect = pygame.Rect(990, 510, 200, 200)
    
    font = pygame.font.SysFont(None, 16)
    clock = pygame.time.Clock()
    frame_count = 0
    debug_mode = False
    emu_fps = 0.0
    last_emu_fps_time = pygame.time.get_ticks()
    last_ppu_frame_count = 0
    total_cpu_cycles = 0

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

    running = True
    while running:
        # 1. Handle Events
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.unicode == 'd':
                    print(f'0x0002: {bus.ram[0x0002]:04x}, 0x0003: {bus.ram[0x0003]:04x}')
                elif e.unicode == 'q':
                    running = False
                elif e.key == pygame.K_TAB:
                    debug_mode = not debug_mode
                if e.key in key_map:
                    bus.controllers[0].set_button(key_map[e.key], True)
            elif e.type == pygame.KEYUP:
                if e.key in key_map:
                    bus.controllers[0].set_button(key_map[e.key], False)

        # 2. Run Emulation for one frame
        # NTSC: ~29780 cycles per frame, sync PPU every ~scanline (113 CPU cycles)
        cycles_this_frame = 0
        while cycles_this_frame < 29780:
            batch_cycles = 0
            while batch_cycles < 113:
                cycles = cpu.clock()
                batch_cycles += cycles
                total_cpu_cycles += cycles
            cycles_this_frame += batch_cycles

            bus.ppu.run_to(total_cpu_cycles * 3)

            if bus.ppu.nmi:
                bus.ppu.nmi = False
                cpu.nmi()

        # 3. Render
        now = pygame.time.get_ticks()
        elapsed_ms = now - last_emu_fps_time
        if elapsed_ms >= 1000:
            emu_fps = (bus.ppu.frame_count - last_ppu_frame_count) / (elapsed_ms / 1000.0)
            last_ppu_frame_count = bus.ppu.frame_count
            last_emu_fps_time = now

        screen.fill((0, 0, 0))
        if debug_mode:
            if frame_count % 10 == 0:
                draw_memory_view(bus, memory_view_rect, 0x0000, screen, font)
                draw_pattern_table(bus, 0, pattern_table_0_rect, screen)
                draw_pattern_table(bus, 1, pattern_table_1_rect, screen)
            
            draw_status_bits(cpu, status_bits_rect, screen, font)
            draw_program_counter(cpu, pc_rect, screen, font)
            draw_registers(cpu, register_rect, screen, font)
            draw_fps(clock, bus.ppu.frame_count, fps_rect, screen, font, emu_fps)
        
        draw_ppu_screen(bus, ppu_screen_rect, screen)
        pygame.display.flip()
        clock.tick(60)
        frame_count += 1

    pygame.quit()

if __name__ == '__main__':
    main()
