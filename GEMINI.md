# GEMINI.md - Pytoynes Project Context

## Project Overview
**Pytoynes** is a Nintendo Entertainment System (NES) emulator implemented in Python. It focuses on emulating the MOS 6502 CPU and supporting the iNES ROM format. The project includes a graphical user interface for visualizing memory and CPU state during execution.

### Key Technologies
- **Language:** Python 3
- **Graphics/UI:** [Pygame](https://www.pygame.org/)
- **Testing:** Python's built-in `unittest` framework

## Architecture & Components
- `app.py`: The main entry point. Initializes the CPU, Bus, and UI, then starts the emulation loop.
- `pytoynes/`:
    - `mos6502.py`: Implementation of the MOS 6502 CPU, including all standard opcodes and addressing modes.
    - `bus.py`: The system bus that handles memory mapping and communication between the CPU and other components (RAM, Cartridge).
    - `rom.py`: Logic for parsing iNES (`.nes`) files.
    - `cartridge.py`: Abstraction for the game cartridge, including PRG-ROM and CHR-ROM handling.
    - `mapper.py`: Base class for NES mappers (which handle bank switching).
    - `ppu.py`: Implementation of the Picture Processing Unit (PPU).
    - `ui/memoryview.py`: Pygame-based visualization of memory, registers, and program counter.
- `pytoynes/assets/`:
    - `nestest.nes`: A widely used test ROM for verifying 6502 CPU implementation correctness.
    - `ref_ans.txt`: A reference execution log for `nestest.nes` used for cycle-by-cycle debugging.

## Building and Running

### Prerequisites
- Python 3.x
- Pygame (`pip install pygame`)

### Running the Emulator
To start the emulator with the default test ROM:
```bash
python app.py
```

### Key Controls (in-app)
- `q`: Quit the application.
- `d`: Debug print specific memory addresses to the console.

## Testing
The project uses `unittest` for verifying component behavior.

### Running Tests
To run all tests in the `test/` directory:
```bash
python -m unittest discover test
```

### Test Files
- `test/test_cpu.py`: Unit tests for individual CPU instructions.
- `test/test_rom.py`: Tests for ROM loading and parsing.

## Development Conventions
- **Instruction Implementation:** The CPU (`mos6502.py`) uses a table-driven approach where each opcode is mapped to a `compute` function and an `address` mode function.
- **Testing:** New CPU instructions should be accompanied by a test case in `test_cpu.py`.
- **Debugging:** `nestest.nes` and `ref_ans.txt` are the primary tools for ensuring CPU accuracy.

## Development Plan: PPU Support

The current goal is to implement the Picture Processing Unit (PPU). This requires updates to the CPU, Bus, and Cartridge to support PPU register mapping and CHR-ROM access.

### 1. CPU Improvements
- [x] **Fix Reset Vector:** Ensure Stack Pointer (SP) is correctly initialized to `0xFD` and other registers are cleared.
- [ ] **Verify NMI/IRQ/Reset Logic:** Ensure interrupt vectors are read from correct memory locations (`0xFFFA`, `0xFFFC`, `0xFFFE`).
- [ ] **Cycle Accuracy:** Refine cycle counting for complex instructions and page-crossing addressing modes.

### 2. Bus & Memory Mapping
- [x] **PPU Register Mapping:** Implement access to PPU registers at `0x2000-0x3FFF` (mirrored every 8 bytes).
- [x] **OAM DMA:** Implement Direct Memory Access for Object Attribute Memory at `0x4014`.
- [x] **Bus Refactoring:** Allow the Bus to communicate with the PPU once it's implemented.

### 3. Cartridge & Mappers
- [x] **PPU Read/Write:** Add `ppu_read` and `ppu_write` methods to `Cartridge`.
- [x] **CHR Memory Handling:** Ensure `chr_rom_data` (or CHR-RAM) is accessible via the Mapper.
- [x] **Mapper Updates:** Implement PPU address mapping in `Mapper000`.

### 4. PPU Implementation (Core)
- [x] **Internal Memory:** Implement Pattern Tables, Name Tables, Attribute Tables, and Palettes.
- [x] **Registers:** Implement `PPUCTRL`, `PPUMASK`, `PPUSTATUS`, `OAMADDR`, `OAMDATA`, `PPUSCROLL`, `PPUADDR`, `PPUDATA`.
- [x] **Rendering Pipeline:** Implement background and sprite rendering (scanline-based and vectorized NumPy fast-path).
- [x] **Timing:** Synchronize PPU cycles with CPU cycles (3 PPU cycles per 1 CPU cycle for NTSC).
- [x] **Interrupts:** Trigger NMI on VBlank if enabled in `PPUCTRL`.

### 5. Validation
- [x] **CPU Accuracy:** Verified with automated `nestest.nes` validation (first 8991 instructions).
- [ ] **PPU Test ROMs:** Utilize specialized PPU test ROMs (e.g., `vbl_nmi_timing`, `palette_test`).
- [x] **Visual Verification:** Verify correct rendering of backgrounds and sprites in `app.py`.

## Technical Notes: Architecture & Performance
- **Cython/Python Hybrid:** The core components (`mos6502`, `ppu`, `bus`) are implemented in both `.py` (for ease of testing) and `.pyx` (for performance via Cython).
- **Mapper Interface:** All memory accesses are routed through the `Cartridge` and `Mapper` classes. This ensures compatibility with complex NES mappers at the cost of slight Python overhead when calling methods from Cython.
- **Rendering:** The PPU uses NumPy for vectorized scanline rendering, which is significantly faster than pixel-by-pixel Python loops.
