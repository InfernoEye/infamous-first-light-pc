# inFAMOUS First Light — native PC port

[![license](https://img.shields.io/badge/license-GPL--2.0-blue)](LICENSE)
[![platform](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white)](#playing)
[![C++](https://img.shields.io/badge/C%2B%2B-23-00599C?logo=cplusplus&logoColor=white)](port/gpu)
[![C](https://img.shields.io/badge/C-11-A8B9CC?logo=c&logoColor=black)](port/src)
[![Vulkan](https://img.shields.io/badge/Vulkan-1.3-AC162C?logo=vulkan&logoColor=white)](port/gpu)
[![Qt](https://img.shields.io/badge/Qt%20Quick-PySide6-41CD52?logo=qt&logoColor=white)](launcher)
[![release](https://img.shields.io/github/v/release/VantageEX/infamous-first-light-pc?include_prereleases&label=release)](https://github.com/VantageEX/infamous-first-light-pc/releases)
[![downloads](https://img.shields.io/github/downloads/VantageEX/infamous-first-light-pc/total?label=downloads)](https://github.com/VantageEX/infamous-first-light-pc/releases)
[![status](https://img.shields.io/badge/status-early%20preview-orange)](#status)

An unofficial native Windows port of **inFAMOUS First Light** (PS4). The game's own x86-64 code runs directly on the PC's processor, a reimplemented PS4 runtime stands in for the console's system libraries, and the graphics are translated to Vulkan. It is not a general-purpose emulator.

> **You need your own copy of the game**, dumped from your own PS4. No game files, firmware, keys or Sony assets are part of this repository or its releases.

[Русская версия ниже](#русский)

| | |
|---|---|
| ![Fetch using her neon power in the city at night, 42 FPS on renderer v2](docs/screenshots/gameplay-city.jpg) | ![Fetch's neon dash close up, with the performance overlay, 41 FPS](docs/screenshots/gameplay-neon-dash.jpg) |

![The launcher: the game's own art, Play, the newest save to continue and the settings](docs/screenshots/launcher.jpg)

### ▶ Gameplay video

[![inFAMOUS First Light PC Port — Native Gameplay part 2 (YouTube)](https://img.youtube.com/vi/ISWGOfrwtqA/maxresdefault.jpg)](https://youtu.be/ISWGOfrwtqA)

<sub>Ryzen + RTX 4070 SUPER, 1080p. The launcher shows the art of the player's own game files.</sub>

## Status

**Early, playable.** The game boots, reaches the menus and gameplay, saves, and plays through the first missions; Fetch's neon powers, the dash trail, lights and particles render.

| | |
|---|---|
| Tested dump | CUSA00897 (EU), base game 1.00 |
| Frame rate | about 35–45 FPS with renderer v2 (the default), 15–25 with the classic one, on a Ryzen + RTX 4070 SUPER; goal: a steady 30 FPS on mid-range PCs |
| Known issues | the first start prepares and compiles shaders (2–3 minutes once); GPU readbacks cost frame rate (work in progress); the classic renderer flashes yellow for a moment while a save loads; some lights pulse in the boat cutscene |

### Renderer v2 native-RCAS compatibility fallback (RADV GPU hang investigation)

Renderer v2 restores its previous **direct native-size present** behavior by default:
at a 1:1 game-image-to-output size, it skips the newly added RCAS-only compute
pass even when `rcas=1` is saved in `tlg.ini`. FSR 1 and RCAS still work together
for actual upscaling (both dimensions must grow). To test the experimental
native-size RCAS pass deliberately, set `ISS_V2_NATIVE_RCAS=1` in the launch
environment. The game logs `V2_RCAS_NATIVE_OFF` once when the fallback applies.

**This is a narrow rollback, not a verified fix for the GPUVM fault.** The
observed RADV crash occurred after an indexed game draw (VS `04e70448`,
PS `258acc2b`) at 2560×1080. Whether the extra native RCAS dispatch
contributed is unknown; a 16:9/1920×1080 control capture is still needed.
The classic renderer and native 16:9 settings are unaffected.

### Isolating the repeated RX 6900 XT / RADV Continue GPU fault

Two 2026-11-21 attempts on the *same* renderer-v2 build and settings behaved
differently: a long playable run was followed by a Continue world-load hang.
The later 07:30 (profiling ON) and 07:31 (profiling OFF) runs both stopped at
the same GPU blackbox checkpoint (VS `04e70448`, PS `258acc2b`, indexed
draw with 3789 indices); the latter reported GPUVM read fault `0x00410000`.
The checkpoint is recorded **before** a draw; it does not prove that exact
draw is faulty. Native-size RCAS rollback has not resolved the issue.

To **isolate the suspected draw without modifying game files**, an opt-in
diagnostic switch `ISS_DIAG_SKIP_FAULT_DRAW=1` skips *only* indexed draws
with that exact shader pair and 3789 indices. The log prints
`GPU_FAULT_DRAW_BYPASS` when a draw is skipped. This intentionally alters
the image and must **not** be enabled for normal gameplay or benchmarks.
A successful Continue would narrow the bug to this draw/its resources; a
remaining hang would point to other work or a prior command. This switch
is OFF by default. For safety test first at 16:9 / 1920×1080 with profiling
OFF; if GPU resets persist, stop testing and use the classic renderer.

### Profiling a 15 FPS renderer-v2 session

**Advanced → Profile renderer v2 (low impact)** is optional and only works with
renderer v2. It writes a new `data/profiling/renderer-v2-*.csv` with one-second samples of
presented FPS and readback-queue activity. It deliberately does **not** enable expensive
per-draw CPU instrumentation or command-buffer statistics: on an AMD RX 6900 XT with RADV,
the old profiling mode coincided with reproducible GPU hangs / device loss when choosing
Continue. The lightweight mode is safer, but the root cause has not yet been resolved or
retested. Capture normal FPS with profiling OFF first.

**Repeatable two-run test:** choose a save and stand still in the same scene. Record 30–60 s
with **Quality (native 1080p)** and then 30–60 s with **Performance (720p + FSR 1)**.
Keep renderer v2, display mode, FPS limit and gameplay location unchanged. On each run,
enable profiling only while taking the timing sample, turn it off afterward, then compare
the logs under `data/logs`. Analyze the CSV files with:

```bash
python scripts/profile_renderer_v2.py data/profiling/renderer-v2-1080p.csv data/profiling/renderer-v2-720p.csv
```

Substitute the actual generated CSV paths (on PowerShell, filenames can be given individually).
The analyzer prints FPS including zero-frame stalls, the slowest one-second windows,
and readback activity. In normal lightweight mode CPU phase times are **not** captured.
Advanced diagnostics can explicitly opt into `ISS_DEEP_PROFILE=1` to collect CPU scope
timings, but that heavy mode is experimental and **may trigger a GPU fault** on RADV.
CPU scopes overlap and are not GPU timestamps; do not sum them as independent costs. If lowering the
resolution changes FPS little, the CPU/command processor/readback path is more likely
than a simple pixel shader cost. For more evidence, share both timing CSVs and a sanitized
launcher performance report; inspect them before posting publicly.

### Player-selectable graphics and FPS diagnostics

The launcher has an optional **Graphics preset** picker with **Quality** (native 1080p,
FSR 1 available and RCAS on), **Balanced** (800p + FSR 1 + RCAS), and **Performance**
(720p + FSR 1; RCAS off to save a postprocessing pass). Players can still change
individual settings; the preset then displays **Custom**. There is also a manual 480p
render option for extremely limited GPUs. No preset changes GPU readback precision,
shader compilation, the selected renderer or frame pacing.

The renderer v2 FSR pass avoids running EASU at 1:1 input/output resolution when
only sharpening is needed. Native-size RCAS now performs just one compute pass
instead of reconstructing the already-native image first. This reduces one GPU
dispatch and intermediate-image dependency in this case; it **does not guarantee
an FPS increase** when game emulation, CPU synchronization or readbacks dominate.

If the port stays near 15 FPS, use the **Performance** preset and test the same
scene at 1080p and 720p. A significant gain suggests GPU/pixel cost; little
change suggests a CPU/command-processing/readback bottleneck. The default
`TLG_FRAME_STATS=1` logs frame statistics every 5 seconds on First Light.
For comparisons, keep renderer v2, game location, display mode and other
settings constant. Collect the launcher Log → Create report to diagnose
the real bottleneck. Do **not** disable `TLG_READBACKS` or enable unsafe
`ISS_NATIVE_PASSES` just for FPS: those paths can break neon, exposure,
decals or other important effects on First Light.

### Graphics quality and stability

**FSR 1 now works from the launcher on renderer v2.** The renderer previously read its own
`BB_FSR1` setting (off by default) rather than `fsr1` from `tlg.ini`. It now reads the shared
FSR 1 and RCAS settings, including sharpening strength, on every frame. The in-game Image tab
(Insert / R3+L2) shows the actual game image and window resolution and whether FSR 1 is active.

**For FSR 1 upscaling:** choose **720p or 800p internal resolution**, enable **FSR 1**, and
use **borderless or fullscreen** on a higher-resolution monitor. For example, 720p → 1440p
runs EASU reconstruction and optional RCAS. With a 1080p internal image on a 1080p screen,
there is nothing to upscale: RCAS can sharpen the native image, but FSR 1 does not invent detail.

**For real higher-quality image detail:** the launcher offers **1440p, 1800p and 4K internal
rendering**. These change the game's actual render size using a signature-checked patch; they
are more expensive than FSR 1 scaling. 4K now maps to 3840×2160 instead of being ignored.
Higher internal resolutions can also downsample to a smaller display for supersampling.
Check the log for `Patches: render resolution ...` to confirm the size patch applied; it safely
skips game builds whose code doesn't match. High-resolution render modes are experimental
until tested with your game version and GPU.

To avoid missing objects and unsafe readback shortcuts, new installs default to background
shader compilation and stale GPU readbacks off. Existing `tlg.ini` preferences are preserved.

## Playing

1. Download the [latest release](https://github.com/VantageEX/infamous-first-light-pc/releases/latest) and unzip it anywhere you can write to (not Program Files).
2. Start **inFAMOUS First Light.exe** and pick your game folder (the one with `eboot.bin` and `sce_sys`).
3. Press **Play**. F10 shows the performance overlay, F9 the keys and mouse buttons held (for recordings and streams); Insert (or R3 + L2) opens the in-game menu.

From v0.3.2 the launcher checks for a new release when it starts and installs it with one click; your saves and settings stay.

**Steam, Playnite, a shortcut:** `"inFAMOUS First Light.exe" --play` starts the game straight away with the launcher's settings, without its window (in Steam: add a non-Steam game, then Properties → Launch options: `--play`). If the game fails, the launcher opens on its log.

**Ultrawide (experimental):** launcher → Display → Picture shape: 21:9, 32:9 or "As the screen". The view widens at the sides and the HUD moves to the edges; the movies stay 16:9 with bars at the sides. The render size keeps the chosen resolution's height (at most 4K's pixel count). Environment variables for testing: `TLG_RENDER_SIZE=2560x1080` sets the size directly, `TLG_MOVIE_FIT=0` stretches the movies as before.

Requirements: Windows 10/11 64-bit, a Vulkan 1.3 GPU, a CPU with AVX (Intel CPUs work: the AMD-only instructions the game uses are emulated).

**Dumping your game:** on your own PS4 with GoldHEN, dump the game (and its update, if any) with a homebrew dumper such as Itemzflow, and copy the folder to the PC.

### Controls

Xbox, PlayStation and other controllers work, and so does the keyboard. The touchpad and the motion sensor are simulated on controllers without them:

| In game | Xbox / other controller | Keyboard |
|---|---|---|
| Press the touchpad | View | Tab / Backspace |
| Touchpad swipe | hold View + right stick | hold Tab + arrows |
| Graffiti: controller on its side | L3 + R3 (sensor mode on/off) | hold T or G |
| Graffiti: shake / spray / aim | A / R2 / left stick | Y / F / arrows |

## Reporting performance

Reports from many different PCs are what the optimisation needs:

1. Play 10–15 minutes (the city, running, dashes, a fight). Test builds (with a `TEST_BUILD` file) log extra performance statistics.
2. In the launcher open **Log → Create report**: it writes a zip in `data/reports` (logs and the PC's specs, no personal paths).
3. Open a **[performance report](https://github.com/VantageEX/infamous-first-light-pc/issues/new?template=performance_report.yml)**, fill in the form and drag the zip into it. Crashes and glitches go to a **[bug report](https://github.com/VantageEX/infamous-first-light-pc/issues/new?template=bug_report.yml)**.

Never attach game files.

## Building

In an **MSYS2 CLANG64** shell:

```bash
pacman -S --needed git patch \
  mingw-w64-clang-x86_64-{toolchain,cmake,ninja,pkgconf,python} \
  mingw-w64-clang-x86_64-{vulkan-headers,vulkan-loader,vulkan-memory-allocator,glslang} \
  mingw-w64-clang-x86_64-{sdl3,fmt,boost,robin-map,xxhash,ffmpeg,zydis} \
  mingw-w64-clang-x86_64-{spirv-tools,spirv-headers,spirv-cross}
git clone --recursive <this repository> && cd <repository>
cd port && ISS_LTO=OFF TLG_RENDERER_V2=1 bash build.sh && cd ..
```

The launcher (PySide6): `py -m venv .venv`, `.venv\Scripts\pip install PySide6-Essentials pillow iced-x86`, then `launcher\start.bat`. A release folder: `bash dev/package.sh` (`TEST=1` for a test build). `bash dev/export_public.sh` shows exactly what a push publishes.

| Folder | What it holds |
|---|---|
| `port/` | The core: loader, PS4 runtime (`src/`), Vulkan renderers (`gpu/` classic, `gpu_v2/` renderer v2, `gpu_v3/` renderer v3, experimental), game preparation scripts |
| `launcher/` | The launcher (PySide6 + Qt Quick) |
| `dev/` | Packaging, RenderDoc capture, debugging aids |
| `docs/iss_pc/` | The documentation of the project the core comes from |

## Credits and license

This port is a fork of [**iss_pc**](https://github.com/HayatoG/iss_pc) by **HayatoG**, the native PC port of inFAMOUS Second Son; its core (runtime, loader, GPU translation and many fixes) is the foundation of this project. The GPU translation comes from [**shadPS4**](https://github.com/shadps4-emu/shadPS4); iss_pc also credits [tlg_pc](https://github.com/HayatoG/tlg_pc), [gr2_pc](https://github.com/HayatoG/gr2_pc), [gow3_pc](https://github.com/FelipePrado0/gow3_pc), [bloodborne_pc](https://github.com/deadinside28/bloodborne_pc), [ShadowOfTheColossus-PC](https://github.com/AjncSystem/ShadowOfTheColossus-PC) and the other projects listed in [docs/iss_pc](docs/iss_pc/README.md). Renderer v2 (`port/gpu_v2`, by way of iss_pc) is **Castlesea**'s renderer from [infamous-second-son-pc-port](https://github.com/Castlesea/infamous-second-son-pc-port), on **weshayoub92**'s [shadPS4-perf](https://github.com/weshayoub92/shadPS4-perf). Renderer v3 (`port/gpu_v3`, experimental) is **axylpup**'s multithreaded Second Son build of shadPS4 ([second-son](https://github.com/axylpup/shadPS4/tree/second-son), release `second-son-v1.1.1`). ATRAC9 audio via [LibAtrac9](https://github.com/Thealexbarney/LibAtrac9).

Licensed under **GPL-2.0**, like the projects it builds on ([LICENSE](LICENSE)).

Where Windows' Segoe UI is missing (Linux, the Steam Deck) the launcher and the in-game menus use [Open Sans](https://github.com/googlefonts/opensans) (SIL Open Font License 1.1, [port/fonts/OFL-OpenSans.txt](port/fonts/OFL-OpenSans.txt)) and a subset of Microsoft's [Fluent UI System Icons](https://github.com/microsoft/fluentui-system-icons) (MIT, [port/fonts/LICENSE-FluentSystemIcons.txt](port/fonts/LICENSE-FluentSystemIcons.txt)).

*inFAMOUS* is a trademark of Sony Interactive Entertainment. This project is not affiliated with Sony Interactive Entertainment or Sucker Punch Productions.

---

<a id="русский"></a>

# inFAMOUS First Light — нативный порт на ПК

Неофициальный нативный порт **inFAMOUS First Light** (PS4) на Windows. Собственный x86-64 код игры выполняется прямо на процессоре ПК, системные библиотеки консоли заменены переписанной средой выполнения, а графика переводится на Vulkan. Это не универсальный эмулятор.

> **Нужна ваша собственная копия игры**, снятая с вашей PS4. Ни файлов игры, ни прошивки, ни ключей, ни материалов Sony в репозитории и релизах нет.

Скриншоты — [в начале страницы](#infamous-first-light--native-pc-port): неоновая сила Проныры в ночном городе, неоновый рывок с оверлеем производительности и лаунчер. **▶ [Видео геймплея на YouTube](https://youtu.be/ISWGOfrwtqA)**.

## Состояние

**Ранняя версия, игра проходится.** Игра запускается, доходит до меню и геймплея, сохраняется, проходятся первые миссии. Неоновые способности Проныры, след рывка, свет и частицы отображаются.

| | |
|---|---|
| Проверенный дамп | CUSA00897 (EU), базовая игра 1.00 |
| FPS | около 35–45 на рендере v2 (по умолчанию), 15–25 на обычном, Ryzen + RTX 4070 SUPER; цель — стабильные 30 FPS на средних ПК |
| Известные проблемы | первый запуск готовит и компилирует шейдеры (2–3 минуты, один раз); чтение данных с видеокарты стоит FPS (в работе); на обычном рендере при загрузке сохранения на мгновение мелькает жёлтый; в катсцене с лодкой мигают некоторые огни |

## Как играть

1. Скачайте [последний релиз](https://github.com/VantageEX/infamous-first-light-pc/releases/latest) и распакуйте в любую папку, куда можно писать (не в Program Files).
2. Запустите **inFAMOUS First Light.exe** и выберите папку с игрой (в ней `eboot.bin` и `sce_sys`).
3. Нажмите **«Играть»**. F10 показывает оверлей производительности, F9 — нажатые клавиши и кнопки мыши (для записи и стримов), Insert (или R3 + L2) открывает меню в игре.

Начиная с v0.3.2 лаунчер при запуске проверяет новые релизы и ставит их в один клик; сохранения и настройки остаются.

**Steam, Playnite, ярлык:** `"inFAMOUS First Light.exe" --play` сразу запускает игру с настройками лаунчера, без его окна (в Steam: «Добавить стороннюю игру», затем Свойства → Параметры запуска: `--play`). Если игра завершится с ошибкой, откроется лаунчер с журналом.

**Ultrawide (экспериментально):** лаунчер → Экран → «Форма кадра»: 21:9, 32:9 или «Как у экрана». Обзор расширяется по бокам, интерфейс уходит к краям; ролики остаются 16:9 с полосами по бокам. Размер рендера берёт высоту выбранного разрешения (не больше пикселей 4K). Переменные окружения для проверки: `TLG_RENDER_SIZE=2560x1080` задаёт размер напрямую, `TLG_MOVIE_FIT=0` растягивает ролики, как раньше.

Нужно: Windows 10/11 64-бит, видеокарта с Vulkan 1.3, процессор с AVX (процессоры Intel тоже подходят: инструкции AMD, которые использует игра, эмулируются).

**Как снять дамп:** на своей PS4 с GoldHEN снимите игру (и обновление, если есть) homebrew-дампером, например Itemzflow, и скопируйте папку на ПК.

### Управление

Работают геймпады Xbox, PlayStation и другие, а также клавиатура. Тачпад и датчик движения эмулируются на геймпадах без них:

| В игре | Xbox / другой геймпад | Клавиатура |
|---|---|---|
| Нажать тачпад | View | Tab / Backspace |
| Свайп по тачпаду | зажать View + правый стик | зажать Tab + стрелки |
| Граффити: геймпад на боку | L3 + R3 (режим датчика вкл/выкл) | зажать T или G |
| Граффити: встряхнуть / распылять / целиться | A / R2 / левый стик | Y / F / стрелки |

## Отчёты о производительности

Для оптимизации нужны отчёты с как можно большего числа разных ПК:

1. Поиграйте 10–15 минут (город, бег, рывки, бой). Сборки для замеров (с файлом `TEST_BUILD`) пишут дополнительную статистику производительности.
2. В лаунчере откройте **«Журнал» → «Собрать отчёт»**: в папке `data/reports` появится архив (логи и характеристики ПК, без личных путей).
3. Откройте **[отчёт о производительности](https://github.com/VantageEX/infamous-first-light-pc/issues/new?template=performance_report.yml)**, заполните форму и перетащите в неё архив. Вылеты и графические ошибки — в **[сообщение об ошибке](https://github.com/VantageEX/infamous-first-light-pc/issues/new?template=bug_report.yml)**.

Файлы игры не прикладывайте.

## Сборка из исходников

Шаги выше, в разделе [Building](#building): MSYS2 CLANG64, `bash build.sh` в `port/`, лаунчер через `launcher\start.bat`, пакет через `bash dev/package.sh`.

## Авторы и лицензия

Этот порт — форк [**iss_pc**](https://github.com/HayatoG/iss_pc) от **HayatoG**, нативного порта inFAMOUS Second Son; его ядро (среда выполнения, загрузчик, перевод графики и множество исправлений) — основа этого проекта. Перевод графики взят из [**shadPS4**](https://github.com/shadps4-emu/shadPS4); остальные проекты, на которых построен iss_pc, перечислены в [docs/iss_pc](docs/iss_pc/README.md). Рендер v2 (`port/gpu_v2`, через iss_pc) — рендер **Castlesea** из [infamous-second-son-pc-port](https://github.com/Castlesea/infamous-second-son-pc-port) на основе [shadPS4-perf](https://github.com/weshayoub92/shadPS4-perf) от **weshayoub92**. Рендер v3 (`port/gpu_v3`, экспериментальный) — многопоточная сборка shadPS4 для Second Son от **axylpup** ([second-son](https://github.com/axylpup/shadPS4/tree/second-son), релиз `second-son-v1.1.1`).

Лицензия **GPL-2.0**, как у проектов, на которых он основан ([LICENSE](LICENSE)).

Там, где нет шрифта Windows Segoe UI (Linux, Steam Deck), лаунчер и меню в игре используют [Open Sans](https://github.com/googlefonts/opensans) (SIL Open Font License 1.1, [port/fonts/OFL-OpenSans.txt](port/fonts/OFL-OpenSans.txt)) и часть иконок Microsoft [Fluent UI System Icons](https://github.com/microsoft/fluentui-system-icons) (MIT, [port/fonts/LICENSE-FluentSystemIcons.txt](port/fonts/LICENSE-FluentSystemIcons.txt)).

*inFAMOUS* — товарный знак Sony Interactive Entertainment. Проект не связан с Sony Interactive Entertainment и Sucker Punch Productions.
