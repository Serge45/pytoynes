import pygame
import numpy as np
from pytoynes.bus import Bus
from pytoynes.mos6502 import MOS6502

TEXT_COLOR = (255, 255, 255)

# NES RGB Palette (Standard High-Fidelity)
NES_PALETTE = np.array([
    [0x66,0x66,0x66], [0x00,0x2A,0x88], [0x14,0x12,0xA7], [0x3B,0x00,0xA4],
    [0x5C,0x00,0x7E], [0x6E,0x00,0x40], [0x6C,0x06,0x00], [0x56,0x1D,0x00],
    [0x33,0x35,0x00], [0x0B,0x48,0x00], [0x00,0x52,0x00], [0x00,0x4F,0x08],
    [0x00,0x40,0x4D], [0x00,0x00,0x00], [0x00,0x00,0x00], [0x00,0x00,0x00],
    [0xAD,0xAD,0xAD], [0x15,0x5F,0xD9], [0x42,0x40,0xFF], [0x75,0x27,0xFE],
    [0xA0,0x1A,0xCC], [0xB7,0x1E,0x7B], [0xB5,0x31,0x20], [0x99,0x4E,0x00],
    [0x6B,0x6D,0x00], [0x38,0x87,0x00], [0x0C,0x93,0x00], [0x00,0x8F,0x32],
    [0x00,0x7C,0x8D], [0x00,0x00,0x00], [0x00,0x00,0x00], [0x00,0x00,0x00],
    [0xFF,0xFE,0xFF], [0x64,0xB0,0xFF], [0x92,0x90,0xFF], [0xC6,0x76,0xFF],
    [0xF3,0x6A,0xFF], [0xFE,0x6E,0xCC], [0xFE,0x81,0x70], [0xEA,0x9E,0x22],
    [0xBC,0xBE,0x00], [0x88,0xD8,0x00], [0x5C,0xE4,0x30], [0x45,0xE0,0x82],
    [0x48,0xCD,0xDE], [0x4F,0x4F,0x4F], [0x00,0x00,0x00], [0x00,0x00,0x00],
    [0xFF,0xFE,0xFF], [0xC0,0xDF,0xFF], [0xD3,0xD2,0xFF], [0xE8,0xC8,0xFF],
    [0xFB,0xC2,0xFF], [0xFE,0xC4,0xEA], [0xFE,0xCC,0xC5], [0xF7,0xD8,0xA5],
    [0xE4,0xE5,0x94], [0xCF,0xEF,0x96], [0xBD,0xF4,0xAB], [0xB3,0xF3,0xCC],
    [0xB5,0xEB,0xF2], [0xB8,0xB8,0xB8], [0x00,0x00,0x00], [0x00,0x00,0x00]
], dtype=np.uint8)

def draw_memory_view(bus: Bus, rect: pygame.Rect, start_mem_addr: int, dst_surf: pygame.Surface, font: pygame.font.Font):
    step_height = 16
    num_rows = rect.height // step_height

    for i in range(num_rows):
        addr = start_mem_addr + i * 16
        if addr >= len(bus.ram): break
        
        # Render a whole row at once: "ADDR: 00 11 22 33 44 55 66 77 88 99 AA BB CC DD EE FF"
        row_data = bus.ram[addr:addr+16]
        hex_data = " ".join([f"{b:02X}" for b in row_data])
        row_str = f"{addr:04X}: {hex_data}"
        
        text_surf = font.render(row_str, False, TEXT_COLOR)
        dst_surf.blit(text_surf, (rect.x, rect.y + i * step_height))

def draw_status_bits(cpu: MOS6502, rect: pygame.Rect, dst_surf: pygame.Surface, font: pygame.font.Font):
    step_width = rect.width // len(cpu.status)
    step_height = 16

    for i, (status, val) in enumerate(cpu.status.items()):
        label_surf = font.render(status.name, False, TEXT_COLOR)
        val_surf = font.render(str(val), False, TEXT_COLOR)
        dst_surf.blit(label_surf, (rect.x + i * step_width, rect.y))
        dst_surf.blit(val_surf, (rect.x + i * step_width, rect.y + step_height))
        
def draw_program_counter(cpu: MOS6502, rect: pygame.Rect, dst_surf: pygame.Surface, font: pygame.font.Font):
    op = cpu.opcode
    entry = cpu.opcode_table[op] if op is not None else None
    inst_name = entry[0] if entry else 'None'
    inst_name_surf = font.render(f'PC: {inst_name}', False, TEXT_COLOR)
    dst_surf.blit(inst_name_surf, (rect.x, rect.y))

def draw_registers(cpu: MOS6502, rect: pygame.Rect, dst_surf: pygame.Surface, font: pygame.font.Font):
    labels = ('A', 'X', 'Y',)
    registers = (cpu.a, cpu.x, cpu.y,)
    w = rect.width // len(labels)
    h = rect.height

    for i, (label, register) in enumerate(zip(labels, registers)):
        surf = font.render(f'{label}: {register:02X}', False, TEXT_COLOR)
        dst_surf.blit(surf, (rect.x + i * w, rect.y))

def draw_pattern_table(bus: Bus, table_idx: int, rect: pygame.Rect, dst_surf: pygame.Surface):
    ppu = bus.ppu
    
    # Simple grayscale colors for the 4 possible values
    colors = np.array([
        [0, 0, 0],
        [85, 85, 85],
        [170, 170, 170],
        [255, 255, 255]
    ], dtype=np.uint8)
    
    # Create 128x128 array for the pattern table
    pixels = np.zeros((128, 128), dtype=np.uint8)
    
    for tile_y in range(16):
        for tile_x in range(16):
            tile_idx = tile_y * 16 + tile_x
            base_addr = table_idx * 0x1000 + tile_idx * 16
            
            # Fetch 8x8 tile data
            for py in range(8):
                low_byte = ppu.ppu_read(base_addr + py)
                high_byte = ppu.ppu_read(base_addr + py + 8)
                
                # Vectorized bit extraction for 8 pixels at once?
                # For now just keep the loop but optimized
                for px in range(8):
                    bit_pos = 7 - px
                    pixel_val = (((high_byte >> bit_pos) & 0x01) << 1) | ((low_byte >> bit_pos) & 0x01)
                    pixels[tile_y * 8 + py, tile_x * 8 + px] = pixel_val
    
    # Map pixel values to RGB colors
    rgb_array = colors[pixels]
    
    # Create surface from RGB array
    temp_surf = pygame.surfarray.make_surface(rgb_array.transpose(1, 0, 2))
    pygame.transform.scale(temp_surf, (rect.width, rect.height), dst_surf.subsurface(rect))

def draw_ppu_screen(bus: Bus, rect: pygame.Rect, dst_surf: pygame.Surface):
    # Map pixel indices to RGB values using vectorized NumPy indexing
    rgb_data = NES_PALETTE[bus.ppu.pixels]
    
    # Create surface from RGB array
    # transpose(1, 0, 2) is needed because pygame surfarray uses (width, height)
    temp_surf = pygame.surfarray.make_surface(rgb_data.transpose(1, 0, 2))
    
    # Fast scaling and blitting
    scaled_surf = pygame.transform.scale(temp_surf, (rect.width, rect.height))
    dst_surf.blit(scaled_surf, (rect.x, rect.y))

def draw_fps(clock: pygame.time.Clock, ppu_frames: int, rect: pygame.Rect, dst_surf: pygame.Surface, font: pygame.font.Font, emu_fps: float = 0.0):
    fps_surf = font.render(f'EmuFPS: {emu_fps:.1f} (Frames: {ppu_frames})', False, (255, 255, 0))
    dst_surf.blit(fps_surf, (rect.x, rect.y))

def draw_apu_waveform(bus: Bus, rect: pygame.Rect, dst_surf: pygame.Surface):
    apu = bus.apu
    samples = np.frombuffer(apu.pulse1_samples, dtype=np.uint8)
    ptr = apu.sample_ptr
    
    # Re-order ring buffer
    ordered_samples = np.concatenate((samples[ptr:], samples[:ptr]))
    
    pygame.draw.rect(dst_surf, (50, 50, 50), rect) # Background
    
    points = []
    w = rect.width
    h = rect.height
    y_center = rect.y + h // 2
    y_scale = h // 4
    
    for i in range(256):
        x = rect.x + (i * w) // 256
        y = y_center - (1 if ordered_samples[i] else -1) * y_scale
        points.append((x, y))
        
    if len(points) > 1:
        pygame.draw.lines(dst_surf, (0, 255, 0), False, points, 2)
