from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


def _load_benchmark_module():
    module_path = Path(__file__).resolve().parents[1] / "performance_tests" / "benchmark_open_speed.py"
    spec = importlib.util.spec_from_file_location("benchmark_open_speed", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load benchmark_open_speed.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BenchmarkOpenSpeedTests(unittest.TestCase):
    def test_generate_benchmark_file_creates_requested_size(self) -> None:
        benchmark = _load_benchmark_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "test_1mb.md"
            benchmark.generate_benchmark_file(path, 1)

            self.assertTrue(path.exists())
            self.assertGreaterEqual(path.stat().st_size, 1024 * 1024)
            self.assertIn("# Benchmark document", path.read_text(encoding="utf-8").splitlines()[0])


if __name__ == "__main__":
    unittest.main()
