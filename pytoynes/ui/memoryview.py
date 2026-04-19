import pygame
import numpy as np
from pytoynes.bus import Bus
from pytoynes.mos6502 import MOS6502

TEXT_COLOR = (255, 255, 255)

# NES RGB Palette (Approximate)
NES_PALETTE = np.array([
    [124, 124, 124], [0, 0, 252], [0, 0, 188], [68, 40, 188],
    [148, 0, 132], [168, 0, 32], [168, 16, 0], [136, 20, 0],
    [80, 48, 0], [0, 120, 0], [0, 104, 0], [0, 88, 0],
    [0, 64, 88], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [188, 188, 188], [0, 120, 248], [0, 88, 248], [104, 68, 252],
    [216, 0, 204], [228, 0, 88], [248, 56, 0], [228, 92, 16],
    [172, 124, 0], [0, 184, 0], [0, 168, 0], [0, 168, 68],
    [0, 136, 136], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [248, 248, 248], [60, 188, 252], [104, 136, 252], [152, 120, 248],
    [248, 120, 248], [248, 88, 152], [248, 120, 88], [252, 160, 68],
    [248, 184, 0], [184, 248, 24], [88, 216, 84], [88, 248, 152],
    [0, 232, 216], [120, 120, 120], [0, 0, 0], [0, 0, 0],
    [252, 252, 252], [164, 228, 252], [184, 184, 248], [216, 184, 248],
    [248, 184, 248], [248, 164, 192], [240, 208, 176], [254, 224, 164],
    [251, 228, 136], [216, 248, 120], [184, 248, 184], [184, 248, 216],
    [0, 252, 252], [248, 216, 248], [0, 0, 0], [0, 0, 0]
], dtype=np.uint8)

def draw_memory_view(bus: Bus, rect: pygame.Rect, start_mem_addr: int, dst_surf: pygame.Surface, font: pygame.font.Font):
    step_width = rect.width // 16
    step_height = 16

    for i in range(rect.height // step_height):
        for j in range(16):
            val_str = hex(bus.ram[j + start_mem_addr + i * 16])
            text_surf = font.render(val_str, False, TEXT_COLOR)
            dst_surf.blit(text_surf, (j * step_width, i * step_height))

def draw_status_bits(cpu: MOS6502, rect: pygame.Rect, dst_surf: pygame.Surface, font: pygame.font.Font):
    step_width = rect.width // len(cpu.status)
    step_height = 16

    for i, (status, val) in enumerate(cpu.status.items()):
        label_surf = font.render(status.name, False, TEXT_COLOR)
        val_surf = font.render(str(val), False, TEXT_COLOR)
        dst_surf.blit(label_surf, (rect.x + i * step_width, rect.y))
        dst_surf.blit(val_surf, (rect.x + i * step_width, rect.y + step_height))
        
def draw_program_counter(cpu: MOS6502, rect: pygame.Rect, dst_surf: pygame.Surface, font: pygame.font.Font):
    pc = cpu.opcode
    inst_name = cpu.opcode_to_instruction[pc].name if pc is not None else 'None'
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
    
    colors = [
        (0, 0, 0),
        (85, 85, 85),
        (170, 170, 170),
        (255, 255, 255)
    ]
    
    temp_surf = pygame.Surface((128, 128))
    
    for tile_y in range(16):
        for tile_x in range(16):
            tile_idx = tile_y * 16 + tile_x
            for py in range(8):
                for px in range(8):
                    pixel_val = ppu.get_pattern_pixel(table_idx, tile_idx, px, py)
                    temp_surf.set_at((tile_x * 8 + px, tile_y * 8 + py), colors[pixel_val])
    
    scaled_surf = pygame.transform.scale(temp_surf, (rect.width, rect.height))
    dst_surf.blit(scaled_surf, (rect.x, rect.y))

def draw_ppu_screen(bus: Bus, rect: pygame.Rect, dst_surf: pygame.Surface):
    # Optimized rendering using surfarray
    ppu_pixels = np.array(bus.ppu.pixels).reshape((240, 256))
    
    # Map pixel indices to RGB values
    rgb_surf = NES_PALETTE[ppu_pixels]
    
    # Create surface from RGB array
    temp_surf = pygame.surfarray.make_surface(np.transpose(rgb_surf, (1, 0, 2)))
    
    scaled_surf = pygame.transform.scale(temp_surf, (rect.width, rect.height))
    dst_surf.blit(scaled_surf, (rect.x, rect.y))
