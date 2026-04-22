from setuptools import setup
from Cython.Build import cythonize
import numpy as np

setup(
    ext_modules=cythonize([
        "pytoynes/bus.pyx",
        "pytoynes/mos6502.pyx",
        "pytoynes/ppu.pyx",
    ], compiler_directives={
        'boundscheck': False,
        'wraparound': False,
        'cdivision': True,
    }),
    include_dirs=[np.get_include()],
)
