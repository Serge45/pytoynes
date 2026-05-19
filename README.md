# Pytoynes

A Nintendo Entertainment System (NES) emulator written in Python, with optional Cython acceleration for full-speed emulation.

Emulates the MOS 6502 CPU and NES PPU with cycle-accurate timing. Includes a Pygame-based UI with debug overlays for registers, memory, and pattern tables.

## Features

- **Full 6502 CPU Emulation**: Support for all official and common undocumented opcodes.
- **PPU (Picture Processing Unit)**: Background and sprite rendering, scrolling, and sprite-0 hit detection.
- **Multiple Mappers Support**: 
    - **Mapper 000 (NROM)**: Standard early cartridges.
    - **Mapper 001 (MMC1)**: Advanced switching used in *The Legend of Zelda*, *Metroid*.
    - **Mapper 002 (UNROM)**: PRG switching used in *Contra*, *Castlevania*.
    - **Mapper 003 (CNROM)**: CHR switching used in *Gradius*.
    - **Mapper 004 (MMC3)**: IRQ counter and fine-grained switching used in *Super Mario Bros. 3*, *Kirby's Adventure*.
- **Hardware Interrupts**: Support for NMI (VBlank) and Mapper-generated IRQs.
- **Dynamic Mirroring**: Support for Horizontal, Vertical, and One-Screen mirroring modes.
- **Controller Input**: Keyboard-mapped NES controller.
- **Debug View**: Live register, memory, and pattern table visualization.
- **Cross-Platform**: Runs on Windows, macOS, and Linux.

## Requirements

- Python 3.10+
- Pygame
- NumPy
- Cython (required for compiled extensions)
- A C compiler (GCC, Clang, or MSVC)

## Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Serge45/pytoynes.git
   cd pytoynes
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   # OR
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Build Cython Extensions (Recommended)

Building the extensions is required for full-speed emulation (60+ FPS).

```bash
python setup.py build_ext --inplace
```

*Note: Pre-compiled binaries are intentionally excluded from the repository to ensure cross-platform compatibility. You must build them locally for your specific architecture (e.g., x86_64, ARM64).*

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

## License

This project is for educational purposes.
