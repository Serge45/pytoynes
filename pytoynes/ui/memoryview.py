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