import time
import pygame
from pygame._sdl2.video import Window as SDLWindow, Renderer, Texture
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
    bus.ppu.ppu_mask = 0x1E

    cpu.reset()
    lo = bus.read(0xFFFC)
    hi = bus.read(0xFFFD)
    cpu.pc = (hi << 8) | lo

    pygame.init()

    screen = pygame.display.set_mode((768, 720))
    pygame.display.set_caption(f"Pytoynes - {rom_path}")
    ppu_screen_rect = pygame.Rect(0, 0, 768, 720)

    # Debug window rects (relative to debug surface)
    dbg_memory_rect = pygame.Rect(10, 10, 400, 300)
    dbg_status_rect = pygame.Rect(10, 320, 400, 64)
    dbg_pc_rect = pygame.Rect(10, 384, 400, 32)
    dbg_reg_rect = pygame.Rect(10, 416, 400, 64)
    dbg_fps_rect = pygame.Rect(10, 480, 400, 32)
    dbg_pt0_rect = pygame.Rect(10, 520, 200, 200)
    dbg_pt1_rect = pygame.Rect(210, 520, 200, 200)

    font = pygame.font.SysFont(None, 16)
    clock = pygame.time.Clock()
    frame_count = 0
    debug_mode = False
    emu_fps = 0.0
    last_emu_fps_time = pygame.time.get_ticks()
    last_ppu_frame_count = 0
    total_cpu_cycles = 0

    debug_window = None
    debug_renderer = None
    debug_surf = None

    def open_debug_window():
        nonlocal debug_window, debug_renderer, debug_surf
        debug_window = SDLWindow('Debug - Pytoynes', (420, 740))
        debug_renderer = Renderer(debug_window)
        debug_surf = pygame.Surface((420, 740))

    def close_debug_window():
        nonlocal debug_window, debug_renderer, debug_surf, debug_mode
        if debug_window:
            debug_window.destroy()
        debug_window = None
        debug_renderer = None
        debug_surf = None
        debug_mode = False

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
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.WINDOWCLOSE:
                if debug_window:
                    close_debug_window()
            elif e.type == pygame.KEYDOWN:
                if e.unicode == 'd':
                    print(f'0x0002: {bus.ram[0x0002]:04x}, 0x0003: {bus.ram[0x0003]:04x}')
                elif e.unicode == 'q':
                    running = False
                elif e.key == pygame.K_TAB:
                    debug_mode = not debug_mode
                    if debug_mode:
                        open_debug_window()
                    else:
                        close_debug_window()
                if e.key in key_map:
                    bus.controllers[0].set_button(key_map[e.key], True)
            elif e.type == pygame.KEYUP:
                if e.key in key_map:
                    bus.controllers[0].set_button(key_map[e.key], False)

        # Run emulation for one frame
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

        # Render main window
        now = pygame.time.get_ticks()
        elapsed_ms = now - last_emu_fps_time
        if elapsed_ms >= 1000:
            emu_fps = (bus.ppu.frame_count - last_ppu_frame_count) / (elapsed_ms / 1000.0)
            last_ppu_frame_count = bus.ppu.frame_count
            last_emu_fps_time = now

        screen.fill((0, 0, 0))
        draw_ppu_screen(bus, ppu_screen_rect, screen)
        pygame.display.flip()

        # Render debug window (update every 10 frames to avoid flicker)
        if debug_mode and debug_window and frame_count % 10 == 0:
            debug_surf.fill((0, 0, 0))
            draw_memory_view(bus, dbg_memory_rect, 0x0000, debug_surf, font)
            draw_pattern_table(bus, 0, dbg_pt0_rect, debug_surf)
            draw_pattern_table(bus, 1, dbg_pt1_rect, debug_surf)
            draw_status_bits(cpu, dbg_status_rect, debug_surf, font)
            draw_program_counter(cpu, dbg_pc_rect, debug_surf, font)
            draw_registers(cpu, dbg_reg_rect, debug_surf, font)
            draw_fps(clock, bus.ppu.frame_count, dbg_fps_rect, debug_surf, font, emu_fps)

            debug_tex = Texture.from_surface(debug_renderer, debug_surf)
            debug_renderer.clear()
            debug_tex.draw()
            debug_renderer.present()

        clock.tick(60)
        frame_count += 1

    close_debug_window()
    pygame.quit()

if __name__ == '__main__':
    main()
