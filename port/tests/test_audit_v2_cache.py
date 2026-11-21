"""Regression tests for the read-only renderer-v2 GPU cache auditor."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts' / 'audit_v2_cache.py'
spec = importlib.util.spec_from_file_location('audit_v2_cache', SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class CacheAuditorTests(unittest.TestCase):
    def test_log_comparison_does_not_infer_cache_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            a = base / 'good.log'
            b = base / 'bad.log'
            header = ('Renderer: 2 · settings: aspect=21:9, async_shaders=0\n'
                      '[1.1] Build: 2a2947e92141+dirty (built today)\n')
            a.write_text(header + 'CACHE_PREFETCH files=49701 mb=597.7\n'
                         'Vulkan driver cache: 64840336 bytes accepted for this device\n'
                         'Preloaded 17000 pipelines\n'
                         'GPU_PRESENT frame=11112 reused=0\n'
                         'Cache dumped\nLauncher: The game exited (code 130).\n')
            b.write_text(header + 'CACHE_PREFETCH files=54235 mb=643.4\n'
                         'Vulkan driver cache: 66142808 bytes accepted for this device\n'
                         'Preloaded 23000 pipelines\n'
                         'radv: GPUVM fault detected at address 0x00410000.\n'
                         'GPU_BLACKBOX DEVICE LOST\nLauncher: The game exited (code 3).\n')
            report = audit.compare_logs(audit.log_snapshot(a), audit.log_snapshot(b))
            self.assertTrue(report['same_compiled_build'])
            self.assertTrue(report['same_listed_settings'])
            self.assertEqual(report['prefetch_files_added'], 4534)
            self.assertEqual(report['driver_cache_bytes_added'], 1302472)
            self.assertIn('not proof', report['interpretation'])
            self.assertEqual(audit.log_snapshot(b)['gpu_vm_fault'], '0x00410000')

    def test_cache_audit_does_not_modify_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = root / 'CUSA00575'
            cache.mkdir()
            good = cache / '0x0000000004e70448_0.spv'
            bad = cache / 'bad.spv'
            good.write_bytes(audit.SPV_MAGIC + bytes(16))
            bad.write_bytes(b'bad')
            before = [(p.name, p.read_bytes()) for p in sorted(cache.iterdir())]
            result = audit.cache_inventory(root)
            self.assertEqual(result['cache_file_count'], 2)
            self.assertEqual(result['invalid_spirv_candidates'], ['bad.spv'])
            self.assertIn(good.name, result['target_shader_named_files'])
            self.assertFalse(result['driver_cache_present'])
            after = [(p.name, p.read_bytes()) for p in sorted(cache.iterdir())]
            self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
