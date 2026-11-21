# SPDX-License-Identifier: GPL-2.0-or-later
"""Launcher settings (launcher.json) and the core's tlg.ini, both in the data folder."""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Packaged (PyInstaller onedir): <dist>/inFAMOUS First Light.exe beside <dist>/port and <dist>/data.
# Developing: the repository holds port/ and data/.
FROZEN = getattr(sys, 'frozen', False)
REPO = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parents[2]
PORT = REPO / 'port'
# A TEST_BUILD file beside the executable (or in the repository root) makes a build for testers:
# extra core statistics in the log and the report reminder in the interface.
TEST_BUILD = (REPO / 'TEST_BUILD').is_file()
VERSION_FILE = REPO / 'VERSION'


def writable(folder):
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / '.write-test'
        probe.write_bytes(b'')
        probe.unlink()
        return True
    except OSError:
        return False


def data_dir():
    """FL_DATA_DIR, else data/ beside the launcher executable (packaged) or in the repository.
    A package unzipped where it cannot write (Program Files) keeps its data in
    %LOCALAPPDATA%/inFAMOUS First Light PC instead (Linux: ~/.local/share)."""
    if os.environ.get('FL_DATA_DIR'):
        return Path(os.environ['FL_DATA_DIR'])
    beside = REPO / 'data'
    if not FROZEN or writable(beside):
        return beside
    if os.name == 'nt':
        local = os.environ.get('LOCALAPPDATA')
    else:
        local = os.environ.get('XDG_DATA_HOME') or str(Path.home() / '.local' / 'share')
    return Path(local) / 'inFAMOUS First Light PC' if local else beside


# tlg.ini keys the core reads at start (port/gpu/shim/tlg_settings.cpp) and their defaults.
# Resolution and engine frame rate patches exist only for Second Son, so they are left out.
CORE_DEFAULTS = {
    'display_mode': 'windowed',   # windowed / borderless / fullscreen
    'vsync': '1',
    'fps_limit': '60',            # 30, 60, 120, 240 or 0 (unlimited)
    # First Light's FSR 3 temporal inputs are not calibrated yet; prefer stable spatial scaling.
    'fsr1': '1',
    'rcas': '1',
    'show_fps': '0',
    # Unready pipelines can cause briefly missing meshes and grey flashes.
    'async_shaders': '0',
    'deferred_readback': '1',
    # First Light needs accurate readbacks for neon and exposure.
    'stale_readback': '0',
    'render_resolution': 'native',   # the game's render size (run.py: the engine's size patch)
    'aspect': '16:9',                 # the picture's shape: 16:9, 21:9, 32:9 or auto (the screen's)
}
DISPLAY_MODES = ('windowed', 'borderless', 'fullscreen')
FPS_LIMITS = ('30', '60', '120', '240', '0')
# Offered render resolutions; tlg.ini may hold any of graphics_options.py RESOLUTIONS (kept as
# they are, and shown while chosen).
RENDER_RESOLUTIONS = ('native', '1440p', '1800p', '4K', '800p', '720p', '480p')
ASPECTS = ('16:9', '21:9', '32:9', 'auto')
ALL_RENDER_RESOLUTIONS = ('native', '480p', '720p', '800p', '1440p', '1800p', '4K')

# Optional convenience presets, not hidden quality locks. All other options remain editable.
# Quality keeps the new-install defaults; Balanced / Performance reduce actual scene pixels.
GRAPHICS_PRESETS = {
    'quality': {'render_resolution': 'native', 'fsr1': '1', 'rcas': '1'},
    'balanced': {'render_resolution': '800p', 'fsr1': '1', 'rcas': '1'},
    'performance': {'render_resolution': '720p', 'fsr1': '1', 'rcas': '0'},
}


def graphics_preset(core):
    """The current selection, or custom if the player changed any of its fields."""
    for name, values in GRAPHICS_PRESETS.items():
        if all(core.get(key) == value for key, value in values.items()):
            return name
    return 'custom'


def apply_graphics_preset(core, name):
    """Change only render size and scaling; never touch readbacks, shaders or frame limits."""
    values = GRAPHICS_PRESETS.get(name)
    if values is None:
        return False
    core.update(values)
    return True


LAUNCHER_DEFAULTS = {
    'game_dir': '',
    'game_language': 'auto',
    'ui_language': 'auto',
    'extra_env': '',   # KEY=VALUE lines for testing core switches
    'renderer': '2',   # 2: renderer v2 (port/gpu_v2) when built, else 1: the core's own renderer
    'profile_performance': False,  # opt-in: renderer v2 timing CSV, may reduce FPS
}



def performance_profile_env(folder, renderer, stamp=None):
    """Opt-in renderer v2 timing capture. No guest memory, shaders or addresses are dumped.

    Always keep these diagnostics out of the game's folder and out of the source tree.
    The suffix has microseconds so two launches in the same second cannot collide.
    """
    if renderer != '2':
        return {}
    destination = (Path(folder).resolve() / 'profiling')
    destination.mkdir(parents=True, exist_ok=True)
    stamp = stamp or datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    # A test/caller-supplied stamp must not inject a directory separator.
    if not stamp.isascii() or not stamp.replace('-', '').isdigit():
        raise ValueError('Invalid profile session timestamp')
    return {
        'ISS_DEEP_PROFILE': '1',
        'ISS_DEEP_LOG': str(destination / f'renderer-v2-{stamp}.csv'),
        'TLG_FRAME_STATS': '1',
        'TLG_DCB_STATS': '1',
    }


def _read_ini(path):
    values = {}
    try:
        lines = Path(path).read_text(encoding='utf-8').splitlines()
    except OSError:
        return values
    for line in lines:
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip()
    return values


def _write_ini(path, updates):
    """Rewrites the keys in `updates`, appends the missing ones and keeps every other line (the
    in-game menu writes the same file)."""
    path = Path(path)
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except OSError:
        lines = ['# inFAMOUS First Light settings (launcher and in-game menu)']
    done, out = set(), []
    for line in lines:
        key = line.split('=', 1)[0].strip() if '=' in line and not line.lstrip().startswith('#') else None
        if key in updates:
            out.append(f'{key}={updates[key]}')
            done.add(key)
        else:
            out.append(line)
    out += [f'{key}={value}' for key, value in updates.items() if key not in done]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(out) + '\n', encoding='utf-8')


class Settings:
    def __init__(self, folder=None):
        self.folder = Path(folder or data_dir())
        self.launcher_path = self.folder / 'launcher.json'
        self.ini_path = self.folder / 'tlg.ini'
        self.launcher = dict(LAUNCHER_DEFAULTS)
        try:
            stored = json.loads(self.launcher_path.read_text(encoding='utf-8'))
            self.launcher.update({k: v for k, v in stored.items() if k in LAUNCHER_DEFAULTS})
        except (OSError, ValueError):
            pass
        ini = _read_ini(self.ini_path)
        self.core = {key: ini.get(key, value) for key, value in CORE_DEFAULTS.items()}
        if self.core['display_mode'].lower() not in DISPLAY_MODES:
            self.core['display_mode'] = CORE_DEFAULTS['display_mode']
        if self.core['fps_limit'] not in FPS_LIMITS:
            self.core['fps_limit'] = CORE_DEFAULTS['fps_limit']
        if self.core['render_resolution'] not in ALL_RENDER_RESOLUTIONS:
            self.core['render_resolution'] = CORE_DEFAULTS['render_resolution']
        if self.core['aspect'] not in ASPECTS:
            self.core['aspect'] = CORE_DEFAULTS['aspect']

    def save(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        self.launcher_path.write_text(json.dumps(self.launcher, indent=2, ensure_ascii=False), encoding='utf-8')
        _write_ini(self.ini_path, self.core)


# Core switches that run.py takes from tlg.ini (scripts/graphics_options.py) and so would override
# the same variable in the environment: the launcher writes them to tlg.ini instead.
# (async_shaders has its own checkbox.)
INI_SWITCHES = {'TLG_DEFERRED_READBACK': 'deferred_readback', 'TLG_STALE_READBACK': 'stale_readback'}


def consume_ini_switches(core, extra):
    """Apply only explicit advanced overrides; preserve values saved by the in-game menu.

    run.py reads normal readback settings from tlg.ini, not from extra env.
    Defaulting missing advanced keys here silently overwrote existing settings.
    """
    for variable, key in INI_SWITCHES.items():
        if variable in extra:
            core[key] = '0' if extra.pop(variable) == '0' else '1'


def parse_env(text):
    """{KEY: value} from KEY=VALUE lines; blank lines and # comments are skipped."""
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            if key.strip():
                values[key.strip()] = value.strip()
    return values
