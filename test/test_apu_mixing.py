import unittest
import numpy as np
from pytoynes.apu import APU

class TestAPUMixing(unittest.TestCase):
    def setUp(self):
        self.apu = APU()

    def test_pulse_mixing_precision(self):
        """Verify that Pulse mixing matches the exact non-linear formula."""
        # Exact NES formula: pulse_out = 95.88 / ((8128.0 / (pulse1 + pulse2)) + 100.0)
        
        # Test Case: Both pulses at max volume (15 + 15 = 30)
        pulse_sum = 30
        expected_pulse_out = 95.88 / ((8128.0 / pulse_sum) + 100.0)
        
        # Inject values (we need to bypass the envelope logic for a raw test)
        # In our implementation, raw_sample is DUTY (0 or 1) * volume (0-15)
        # So we can just set up the state such that raw_sample1=15, raw_sample2=15.
        
        # Mocking raw samples isn't easy without modifying APU, so we test the result
        # of the calculation logic in a controlled way if possible, or verify 
        # the implementation directly by running it.
        
        # Instead of mocking internal private state, let's verify a known output.
        # When pulse1=15 and pulse2=15, pulse_out should be ~0.258
        self.apu.pulse1_enabled = True
        self.apu.pulse1_lc_value = 10
        self.apu.pulse1_timer_reload = 100 # > 8
        self.apu.pulse1_env_const = True
        self.apu.pulse1_env_vol_period = 15 # Max vol
        self.apu.pulse1_duty_mode = 2 # 50% duty
        self.apu.pulse1_duty_step = 1 # A "high" step in duty 2
        
        self.apu.pulse2_enabled = True
        self.apu.pulse2_lc_value = 10
        self.apu.pulse2_timer_reload = 100
        self.apu.pulse2_env_const = True
        self.apu.pulse2_env_vol_period = 15
        self.apu.pulse2_duty_mode = 2
        self.apu.pulse2_duty_step = 1
        
        # Run clock until a sample is generated
        # resample ratio is ~40.58 cycles.
        for _ in range(50):
            self.apu.clock()
            
        self.assertGreater(self.apu.audio_ptr, 0)
        sample = self.apu.audio_buffer[0] + 0.1 # Remove the -0.1 DC offset shift
        
        # The sample should contain mostly pulse_out since TND is 0
        # Expected: ~0.258
        self.assertAlmostEqual(sample, expected_pulse_out, places=4)

    def test_tnd_mixing_precision(self):
        """Verify that TND mixing matches the exact non-linear formula."""
        # Exact NES formula: tnd_out = 159.79 / (1 / (tri/8227 + noise/12241 + dmc/22638) + 100)
        
        tri = 15
        noise = 0
        dmc = 0
        tnd_denom = (tri / 8227.0) + (noise / 12241.0) + (dmc / 22638.0)
        expected_tnd_out = 159.79 / ((1.0 / tnd_denom) + 100.0)
        
        self.apu.triangle_enabled = True
        self.apu.tri_lc_value = 10
        self.apu.tri_linear_value = 10
        self.apu.tri_timer_reload = 1000 # Large reload to stop stepping
        self.apu.tri_timer_value = 1000
        self.apu.tri_step = 0 # TRI_TABLE[0] is 15
        
        # Keep pulses and others disabled
        self.apu.pulse1_enabled = False
        self.apu.pulse2_enabled = False
        self.apu.noise_enabled = False
        self.apu.dmc_direct_load = 0
        
        for _ in range(50):
            self.apu.clock()
            
        sample = self.apu.audio_buffer[0] + 0.1
        self.assertAlmostEqual(sample, expected_tnd_out, places=4)

if __name__ == '__main__':
    unittest.main()
