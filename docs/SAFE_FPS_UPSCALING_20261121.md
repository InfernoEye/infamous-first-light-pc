# Safe FPS + upscaling iteration (21 November 2026)

**Last known playable source:** [`95e0595`](https://github.com/InfernoEye/infamous-first-light-pc/commit/95e05955024a6649896d859d7caf221da5515c34), merged by PR #1. This branch is *optional* and must never replace the playable baseline before testing. The prior GPU resets happened under renderer v2; avoid adding profiling, speculative fault-draw bypasses, or changing GPU resource binding.

## Checkpoints

1. **Checkpoint A — 900p resolution:** add `900p` to the launcher, Python patcher, graphics options and shared C++ resolution parser, plus tests. It resolves to **1600 × 900 at 16:9**, or **2136 × 900 at 21:9** using the existing aspect conversion. All existing resolutions remain selectable.
2. **Checkpoint B — opt-in Balanced+ preset:** `render_resolution=900p`, `fsr1=1`, `rcas=1`. Existing **Quality** (native), **Balanced** (800p), and **Performance** (720p) presets are untouched. None of the presets change async shaders, readbacks, frame pacing or the renderer.

At 16:9, 900p renders **1.44 million pixels instead of 2.0736 million** at native 1080p (30.6% fewer input pixels). At 21:9, 2136 × 900 reduces game render pixels by about 30.5% from 2560 × 1080. The existing FSR1 spatial upscaler reconstructs the display image, followed by optional RCAS sharpening. This is **not FSR3**, temporal upscaling or generated frames. Image quality and actual FPS gains depend on whether the game is GPU-bound; the game may remain CPU-, readback-, or shader-limited.

## Keep the working version safe

- Leave PR #1 and its merged `main` baseline unchanged.
- When testing this optional branch, use a **separate worktree**, or switch branches with a clean working tree.
- Preserve the exact existing `data/` directory and saved games, including `data/user/`. The port already backs up saves on launch. Do not delete existing caches.
- Keep the **successful isolated shader cache** selected via `ISS_PIPELINE_CACHE_ROOT`. Using a *different empty* root for each experimental build avoids mixing compiled shaders with the stable configuration.
- If the GPU faults again, stop. Return to the original worktree/commit and its previously working cache root. No further renderer-v2 resets are needed to prove a patch failed.

## Suggested one-setting-at-a-time comparison

First confirm the unchanged stable build still launches with its saved settings and cache. Then, in a separate worktree containing this branch, use the same gameplay scene and choose **Balanced+ — 900p + FSR** in the launcher. Leave other advanced options as they were in the stable working run. Check the startup log for an applied resolution patch (1600 × 900 or the expected aspect-converted dimensions); if patch matching fails, the game will remain at native resolution and any FPS comparison would be invalid.

Look for perceptible smoothness and stable gameplay, not just menu FPS. A 60 FPS engine cap cannot be raised by setting a higher present limit alone. If visual quality is worse than expected or performance unchanged, revert to **Quality** without changing renderer code.

## Test coverage

The branch extends regression tests for resolution acceptance, 900p render-size calculations and preservation of readback/async/fps settings by preset selection. These are source/unit tests, not confirmation of driver or hardware stability.

**No new v2 GPU/Vulkan code paths are introduced.**
