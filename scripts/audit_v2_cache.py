#!/usr/bin/env python3
"""Read-only renderer-v2 cache regression audit. Never launches or modifies the game."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import zipfile

SPV_MAGIC = b'\x03\x02\x23\x07'
TYPES = {'.spv', '.meta', '.key', '.bin'}
FAULT_SHADERS = ('04e70448', '258acc2b')


def log_snapshot(path: Path) -> dict:
    content = path.read_text(encoding='utf-8', errors='replace')

    def find(pattern):
        match = re.search(pattern, content, re.MULTILINE)
        return match.groups() if match else None

    build = find(r'\bBuild:\s+(\S+)')
    settings = find(r'^Renderer:\s+\d+\s+·\s+settings:\s+(.+)$')
    prefetch = find(r'CACHE_PREFETCH\s+files=(\d+)\s+mb=([0-9.]+)')
    driver = find(r'Vulkan driver cache:\s+(\d+) bytes accepted')
    preloaded = find(r'Preloaded (\d+) pipelines')
    frames = re.findall(r'GPU_PRESENT frame=(\d+)', content)
    exit_code = find(r'Launcher: The game exited \(code (\d+)\)')
    vmfault = find(r'GPUVM fault detected at address (0x[0-9a-fA-F]+)')
    return {
        'file': path.name,
        'build': build[0] if build else None,
        'settings': settings[0] if settings else None,
        'prefetch_files': int(prefetch[0]) if prefetch else None,
        'prefetch_mb': float(prefetch[1]) if prefetch else None,
        'driver_cache_bytes': int(driver[0]) if driver else None,
        'preloaded_pipelines': int(preloaded[0]) if preloaded else None,
        'last_reported_present_frame': int(frames[-1]) if frames else None,
        'cache_dumped': 'Cache dumped' in content,
        'gpu_stall': 'GPU_BLACKBOX GPU parada' in content,
        'gpu_vm_fault': vmfault[0] if vmfault else None,
        'device_lost': 'DEVICE LOST' in content,
        'exit_code': int(exit_code[0]) if exit_code else None,
    }


def compare_logs(before: dict, after: dict) -> dict:
    def delta(field):
        old, new = before[field], after[field]
        return new - old if old is not None and new is not None else None

    added_mb = delta('prefetch_mb')
    return {
        'same_compiled_build': before['build'] == after['build'],
        'same_listed_settings': before['settings'] == after['settings'],
        'prefetch_files_added': delta('prefetch_files'),
        'prefetch_mb_added': round(added_mb, 3) if added_mb is not None else None,
        'driver_cache_bytes_added': delta('driver_cache_bytes'),
        'preloaded_pipelines_added': delta('preloaded_pipelines'),
        'interpretation': ('The cache inventory changed between sessions. This is correlation, '
                           'not proof of corruption or causation.'),
    }


def cache_inventory(root: Path, serial: str = 'CUSA00575') -> dict:
    """Only stat/read cache files; never create, rename, remove, or recompile anything."""
    cache = root / serial
    archive = root / (serial + '.zip')
    driver = root / (serial + '.vkcache')
    counts = Counter()
    total = 0
    bad_spv = []
    suspect_files = []
    if cache.is_dir():
        for path in cache.iterdir():
            if not path.is_file():
                continue
            info = path.stat()
            counts[path.suffix.lower()] += 1
            total += info.st_size
            if path.suffix.lower() == '.spv':
                with path.open('rb') as handle:
                    magic = handle.read(4)
                if info.st_size < 20 or info.st_size % 4 or magic != SPV_MAGIC:
                    if len(bad_spv) < 20:
                        bad_spv.append(path.name)
            if any(shader in path.name.lower() for shader in FAULT_SHADERS):
                if len(suspect_files) < 30:
                    suspect_files.append(path.name)
    archive_info = None
    if archive.is_file():
        try:
            with zipfile.ZipFile(archive) as zf:
                archive_info = {'entries': len(zf.infolist()), 'bytes': archive.stat().st_size}
        except (OSError, zipfile.BadZipFile):
            archive_info = {'error': 'archive unreadable'}
    return {
        'cache_root': str(root),
        'game_serial': serial,
        'cache_dir_present': cache.is_dir(),
        'cache_file_counts_by_extension': dict(sorted(counts.items())),
        'cache_file_count': sum(counts.values()),
        'cache_bytes': total,
        'invalid_spirv_candidates': bad_spv,
        'target_shader_named_files': suspect_files,
        'archive': archive_info,
        'driver_cache_present': driver.is_file(),
        'driver_cache_bytes': driver.stat().st_size if driver.is_file() else None,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('playable_log', type=Path, nargs='?',
                        help='Optional log from a playable session')
    parser.add_argument('failing_log', type=Path, nargs='?',
                        help='Optional log from the first failing session')
    parser.add_argument('--cache-root', type=Path,
                        help='Existing v2 GPU cache root, e.g. data/user/gpu-14')
    parser.add_argument('--serial', default='CUSA00575')
    args = parser.parse_args(argv)
    if (args.playable_log is None) != (args.failing_log is None):
        parser.error('Provide both logs for comparison, or neither for a cache-only audit.')
    if args.playable_log is None and args.cache_root is None:
        parser.error('Provide two logs and/or --cache-root.')

    report = {}
    if args.playable_log is not None:
        before, after = log_snapshot(args.playable_log), log_snapshot(args.failing_log)
        report.update({'playable': before, 'failing': after,
                       'comparison': compare_logs(before, after)})
    if args.cache_root is not None:
        report['current_cache'] = cache_inventory(args.cache_root, args.serial)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
