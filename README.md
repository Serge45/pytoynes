# Pytoynes

A Nintendo Entertainment System (NES) emulator written in Python, with optional Cython acceleration for full-speed emulation.

Emulates the MOS 6502 CPU and NES PPU with cycle-accurate timing. Includes a Pygame-based UI with debug overlays for registers, memory, and pattern tables.

## Features

- Full 6502 CPU emulation (all official + common undocumented opcodes)
- PPU with background and sprite rendering, scrolling, sprite-0 hit detection
- Mapper 000 (NROM) support
- Controller input (keyboard-mapped)
- Debug view with live register/memory/pattern table display
- Cython extensions for 3x speedup over pure Python

## Requirements

- Python 3.10+
- Pygame
- NumPy
- Cython (optional, for compiled extensions)
- A C compiler (gcc/clang, required for Cython build)

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install pygame numpy cython
```

### Build Cython Extensions (recommended)

```bash
python setup.py build_ext --inplace
```

Without the Cython build, the emulator runs in pure Python at ~40 FPS. With Cython, it reaches ~120 FPS.

## Usage

```bash
# Run with the bundled test ROM
python app.py

# Run with a specific ROM file
python app.py /path/to/rom.nes
```

### Controls

| Key | Action |
|-----|--------|
| Arrow keys | D-pad |
| Z | A button |
| X | B button |
| Shift (Right) | Select |
| Enter | Start |
| Tab | Toggle debug view |
| D | Print debug memory to console |
| Q | Quit |

## Testing

```bash
python -m unittest discover test
```

Tests validate CPU instruction correctness against the `nestest.nes` reference log (5000+ instructions compared cycle-by-cycle).

## Project Structure

```
app.py                Main loop: emulation + Pygame rendering
setup.py              Cython build configuration

pytoynes/
  mos6502.py          MOS 6502 CPU (pure Python fallback)
  mos6502.pyx/.pxd    Cython-compiled CPU
  bus.py              System bus (pure Python fallback)
  bus.pyx/.pxd        Cython-compiled bus
  ppu.py              PPU (pure Python fallback)
  ppu.pyx/.pxd        Cython-compiled PPU
  cartridge.py        iNES ROM loader
  rom.py              iNES file parser
  mapper.py           Mapper base + Mapper000 (NROM)
  controller.py       NES controller (shift register)
  ui/memoryview.py    Debug overlay rendering

test/
  test_cpu.py         CPU instruction unit tests
  test_rom.py         ROM loading + nestest integration tests
```

## Mapper Support

Currently only Mapper 000 (NROM) is implemented. This covers many early NES titles including Donkey Kong, Ice Climber, and Balloon Fight. New mappers can be added by subclassing `Mapper` in `mapper.py`.

## License

This project is for educational purposes.
