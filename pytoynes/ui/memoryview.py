import pygame
from pytoynes.bus import Bus
from pytoynes.mos6502 import MOS6502

TEXT_COLOR = (255, 255, 255)

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
    # Pattern table is 16x16 tiles, each tile is 8x8 pixels
    # Total size 128x128 pixels
    ppu = bus.ppu
    
    # Simple palette for visualization
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
    
    # Scale if necessary or just blit
    scaled_surf = pygame.transform.scale(temp_surf, (rect.width, rect.height))
    dst_surf.blit(scaled_surf, (rect.x, rect.y))

# NES RGB Palette (Approximate)
NES_PALETTE = [
    (0x7C, 0x7C, 0x7C), (0x00, 0x00, 0xFC), (0x00, 0x00, 0xBC), (0x44, 0x28, 0xBC),
    (0x94, 0x00, 0x84), (0xA8, 0x00, 0x20), (0xA8, 0x10, 0x00), (0x88, 0x14, 0x00),
    (0x50, 0x30, 0x00), (0x00, 0x78, 0x00), (0x00, 0x68, 0x00), (0x00, 0x58, 0x00),
    (0x00, 0x40, 0x58), (0x00, 0x00, 0x00), (0x00, 0x00, 0x00), (0x00, 0x00, 0x00),
    (0xBC, 0xBC, 0xBC), (0x00, 0x78, 0xF8), (0x00, 0x58, 0xF8), (0x68, 0x44, 0xFC),
    (0xD8, 0x00, 0xCC), (0xE4, 0x00, 0x58), (0xF8, 0x38, 0x00), (0xE4, 0x5C, 0x10),
    (0xAC, 0x7C, 0x00), (0x00, 0xB8, 0x00), (0x00, 0xA8, 0x00), (0x00, 0xA8, 0x44),
    (0x00, 0x88, 0x88), (0x00, 0x00, 0x00), (0x00, 0x00, 0x00), (0x00, 0x00, 0x00),
    (0xF8, 0xF8, 0xF8), (0x3C, 0xBC, 0xFC), (0x68, 0x88, 0xFC), (0x98, 0x78, 0xF8),
    (0xF8, 0x78, 0xF8), (0xF8, 0x58, 0x98), (0xF8, 0x78, 0x58), (0xFC, 0xA0, 0x44),
    (0xF8, 0xB8, 0x00), (0xB8, 0xF8, 0x18), (0x58, 0xD8, 0x54), (0x58, 0xF8, 0x98),
    (0x00, 0xE8, 0xD8), (0x78, 0x78, 0x78), (0x00, 0x00, 0x00), (0x00, 0x00, 0x00),
    (0xFC, 0xFC, 0xFC), (0xA4, 0xE4, 0xFC), (0xB8, 0xB8, 0xF8), (0xD8, 0xB8, 0xF8),
    (0xF8, 0xB8, 0xF8), (0xF8, 0xA4, 0xC0), (0xF0, 0xD0, 0xB0), (0xFE, 0xE0, 0xA4),
    (0xFB, 0xE4, 0x88), (0xD8, 0xF8, 0x78), (0xB8, 0xF8, 0xB8), (0xB8, 0xF8, 0xD8),
    (0x00, 0xFC, 0xFC), (0xF8, 0xD8, 0xF8), (0x00, 0x00, 0x00), (0x00, 0x00, 0x00)
]

def draw_ppu_screen(bus: Bus, rect: pygame.Rect, dst_surf: pygame.Surface):
    ppu = bus.ppu
    temp_surf = pygame.Surface((256, 240))
    
    for y in range(240):
        for x in range(256):
            color_idx = ppu.pixels[y * 256 + x]
            # color_idx is 0-63
            temp_surf.set_at((x, y), NES_PALETTE[color_idx & 0x3F])
            
    scaled_surf = pygame.transform.scale(temp_surf, (rect.width, rect.height))
    dst_surf.blit(scaled_surf, (rect.x, rect.y))
