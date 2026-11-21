#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Summarize renderer-v2 ISS_DEEP_LOG CSV files. Does not need game files.

python scripts/profile_renderer_v2.py data/profiling/renderer-v2-*.csv
"""
import argparse
import csv
from pathlib import Path

PHASES = {
    'graphics_pipeline': 'Graphics pipeline',
    'compute_pipeline': 'Compute pipeline',
    'resources': 'Resource binding (nested scopes)',
    'buffers': 'Buffer binding',
    'textures': 'Texture binding',
    'vertices': 'Vertex preparation',
    'indices': 'Index preparation',
    'render_targets': 'Render targets',
    'dynamic_state': 'Dynamic GPU state',
    'obtain_buffer': 'Command buffer acquisition',
    'sync_memory': 'GPU/guest memory sync',
    'draw': 'Draw (nested scopes)',
    'dispatch': 'Compute dispatch',
}


def profile_csv(path, skip=2):
    path = Path(path)
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not {'interval_ms', 'flips'}.issubset(reader.fieldnames):
            raise ValueError(f'{path}: not an ISS_DEEP_LOG CSV')
        rows = []
        for line, row in enumerate(reader, 2):
            try:
                duration = float(row['interval_ms'])
                flips = int(row['flips'])
                if duration <= 0 or flips < 0:
                    continue
                values = {'interval_ms': duration, 'flips': flips}
                for phase in PHASES:
                    values[phase] = float(row.get(phase + '_ms') or 0)
                for field in ('queue_reads', 'queue_fallbacks'):
                    values[field] = int(row.get(field) or 0)
                rows.append(values)
            except (TypeError, ValueError) as exc:
                raise ValueError(f'{path}: bad sample at line {line}: {exc}') from exc
    # Zero-flip windows are the strongest hitch signal; never exclude their
    # wall time from overall FPS (the old analyzer did exactly that).
    usable = rows[skip:]
    flips = sum(r['flips'] for r in usable)
    if not usable or not flips:
        return {'path': str(path), 'samples': 0, 'warning': 'No timed frames after warmup'}
    wall = sum(r['interval_ms'] for r in usable)
    elapsed_ms = sum(r['interval_ms'] for r in rows[:skip])
    windows = []
    for r in usable:
        windows.append((elapsed_ms / 1000, 1000 * r['flips'] / r['interval_ms']))
        elapsed_ms += r['interval_ms']
    slowest = sorted(windows, key=lambda pair: (pair[1], pair[0]))[:5]
    phases_recorded = any(r[phase] > 0 for r in usable for phase in PHASES)
    phases = sorted(
        [{'name': name, 'ms_per_frame': sum(r[name] for r in usable) / flips,
          'ms_per_second': 1000 * sum(r[name] for r in usable) / wall}
         for name in PHASES], key=lambda x: -x['ms_per_frame'])
    return {'path': str(path), 'samples': len(usable), 'frames': flips,
            'fps': 1000 * flips / wall, 'phases': phases,
            'cpu_phases_recorded': phases_recorded, 'slowest_windows': slowest,
            'queue_reads': sum(r['queue_reads'] for r in usable),
            'queue_fallbacks': sum(r['queue_fallbacks'] for r in usable)}


def render(profile):
    if not profile['samples']:
        return profile['path'] + ': ' + profile['warning']
    result = [
        profile['path'],
        f"{profile['frames']} frames, {profile['samples']} samples, {profile['fps']:.1f} FPS",
        'Slowest one-second windows (approximate time since capture began):',
    ]
    result.extend(
        f"  {second:6.1f}s: {fps:5.1f} FPS" for second, fps in profile['slowest_windows']
    )
    if profile['cpu_phases_recorded']:
        result.append('CPU phase time per presented frame (nested categories may overlap):')
        result.extend(
            f"  {entry['ms_per_frame']:8.3f} ms/frame  "
            f"{entry['ms_per_second']:8.1f} ms/s   {PHASES[entry['name']]}"
            for entry in profile['phases'] if entry['ms_per_frame'] >= 0.001
        )
    else:
        result.append('Detailed CPU scopes are OFF (low-impact mode); no CPU phase timings captured.')
    result.append(f"Readback queue: {profile['queue_reads']} reads; "
                  f"{profile['queue_fallbacks']} fallbacks")
    result.append('NOTE: one-second samples can reveal stalls but not individual frame times.')
    if profile['cpu_phases_recorded']:
        result.append('CPU phase times overlap and are not GPU pass times.')
    return '\n'.join(result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', nargs='+', type=Path)
    parser.add_argument('--skip', type=int, default=2,
                        help='One-second warmup samples to exclude (default 2)')
    args = parser.parse_args(argv)
    if args.skip < 0:
        parser.error('--skip must be >= 0')
    for path in args.csv:
        try:
            print(render(profile_csv(path, args.skip)), '\n')
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
