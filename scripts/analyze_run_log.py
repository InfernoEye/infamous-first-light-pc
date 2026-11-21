#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Find potential hitch causes in a renderer-v2 launcher run log.

Usage:
    python3 scripts/analyze_run_log.py data/logs/run-*.log

Counts compilation *messages* and expensive upload operations, not per-frame
stalls. Correlate candidate times with actual frame-time profiles and gameplay.
"""
import argparse
import re
from collections import Counter
from pathlib import Path

STAMP = re.compile(r'^\[\s*(\d+(?:\.\d+)?)\]')
UPLOAD = re.compile(r'Large upload:.*?\bcopied=(\d+).*?\belapsed_ms=(\d+(?:\.\d+)?)')
PRESENT = re.compile(r'PRESENT_ACQUIRE .*?\bfence_max_ms=(\d+(?:\.\d+)?)')


def analyze(lines, interval=15):
    if interval <= 0:
        raise ValueError('interval must be positive')
    graphics = Counter()
    shaders = Counter()
    uploads = []
    present_max = 0.0
    elapsed = 0.0
    for line in lines:
        time = STAMP.match(line)
        if time is None:
            continue
        second = float(time.group(1))
        elapsed = max(elapsed, second)
        bucket = int(second // interval) * interval
        if 'GetGraphicsPipeline: Compiling graphics pipeline' in line:
            graphics[bucket] += 1
        if 'CompileModule: Compiling ' in line:
            shaders[bucket] += 1
        if 'SynchronizeMemory: Large upload:' in line:
            match = UPLOAD.search(line)
            if match:
                uploads.append((second, int(match.group(1)), float(match.group(2))))
        present = PRESENT.search(line)
        if present:
            present_max = max(present_max, float(present.group(1)))
    return dict(duration=elapsed, interval=interval, graphics=graphics, shaders=shaders,
                uploads=uploads, present_max=present_max)


def summarize(result, top=6):
    graphics = result['graphics']
    shaders = result['shaders']
    interval = result['interval']
    output = [
        f"Observed session: {result['duration']:.0f}s",
        f"Graphics pipeline compilation messages: {sum(graphics.values())}",
        f"Shader module compilation messages: {sum(shaders.values())}",
        f"Large upload operations: {len(result['uploads'])}",
        "Most active compilation windows (not exact frame-time measurements):",
    ]
    active = sorted(set(graphics) | set(shaders),
                    key=lambda x: (-graphics[x] - shaders[x], x))[:top]
    for start in active:
        output.append(f"  {start:5d}-{start + interval:5d}s: "
                      f"{graphics[start]} graphics pipelines, {shaders[start]} shader modules")
    if not active:
        output.append('  No compilation messages were recorded')
    output.append('Longest logged uploads:')
    for second, copied, elapsed in sorted(result['uploads'],
                                           key=lambda x: -x[2])[:top]:
        output.append(f'  {second:7.2f}s: {elapsed:7.1f} ms, {copied / (1024**2):.1f} MiB copied')
    if not result['uploads']:
        output.append('  No large uploads were recorded')
    if result['present_max']:
        output.append(f"Maximum reported present-acquire fence wait: {result['present_max']:.3f} ms")
    output.append('Compilation events and uploads are hitch candidates, not proof of a frame stall.')
    output.append('Use the opt-in renderer-v2 profiling CSV to correlate CPU costs with FPS.')
    return '\n'.join(output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('logs', type=Path, nargs='+', help='Launcher run-*.log files')
    parser.add_argument('--interval', type=int, default=15, help='Histogram interval in seconds')
    parser.add_argument('--top', type=int, default=6, help='Maximum items per section')
    args = parser.parse_args(argv)
    if args.interval <= 0 or args.top < 1:
        parser.error('--interval and --top must be positive')
    for path in args.logs:
        try:
            with path.open(encoding='utf-8', errors='replace') as stream:
                result = analyze(stream, args.interval)
            print(path, '\n' + summarize(result, args.top), '\n')
        except OSError as exc:
            parser.error(str(exc))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
