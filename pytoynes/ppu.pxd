# cython: language_level=3
cimport numpy as np

cdef class PPU:
    cdef public int ppu_ctrl, ppu_mask, ppu_status, oam_addr, oam_data
    cdef public int v, t, fine_x, w
    cdef public int ppu_data_buffer
    cdef public int scanline, cycle, frame_count
    cdef public long long total_cycles
    cdef public bint nmi, is_odd_frame, sprite_zero_hit_possible
    cdef public int mirror_mode

    cdef public unsigned char[:] vram, palette_vram, oam_vram
    cdef public unsigned char[:] _chr_memory
    cdef public object pixels  # numpy array

    cdef public int bg_next_tile_id, bg_next_tile_attrib
    cdef public int bg_next_tile_lsb, bg_next_tile_msb
    cdef public int bg_shifter_tile_lo, bg_shifter_tile_hi
    cdef public int bg_shifter_attrib_lo, bg_shifter_attrib_hi

    cdef public unsigned char[:] secondary_oam
    cdef public int sprite_count
    cdef public unsigned char[:] sprite_shifter_pattern_lo, sprite_shifter_pattern_hi
    cdef public unsigned char[:] sprite_attribs, sprite_x_counters

    cdef public object _bg_pixels, _bg_palettes
    cdef public object _fg_pixels, _fg_palettes, _fg_priorities, _sprite0_possible

    cdef public object cartridge

    cpdef int cpu_read(self, int addr)
    cpdef void cpu_write(self, int addr, int data)
    cpdef int ppu_read(self, int addr)
    cpdef void ppu_write(self, int addr, int data)
    cpdef void run_to(self, long long target_total_cycles)
    cpdef void clock(self)
    cpdef void connect_cartridge(self, object cartridge)

    cdef void _render_scanline_fast(self)
    cpdef void _render_pixel(self)
    cpdef void _update_shifters(self)
    cdef void _load_shifters(self)
    cdef void _increment_scroll_x(self)
    cdef void _increment_scroll_y(self)
    cdef void _reset_scroll_x(self)
    cdef void _reset_scroll_y(self)
    cdef void _fetch_nt(self)
    cdef void _fetch_at(self)
    cdef void _fetch_pt_lo(self)
    cdef void _fetch_pt_hi(self)
    cdef void _evaluate_sprites(self)
    cdef void _fetch_sprite_data(self)
    cdef inline int _map_nt_addr(self, int addr)
