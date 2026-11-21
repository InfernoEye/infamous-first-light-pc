# Experimental exact-key compute pipeline memo (21 November 2026)

## Baseline and scope

This experiment branches from `5e0b85f1c66ce2b7047c2d1caf9a6b1ffb30571b`
(**merged PR #3**) and leaves its working readback and FSR upscaling
changes untouched. It is not a new renderer or shader algorithm.

For compute dispatches, `PipelineCache::GetComputePipeline` already
calculates the exact shader specialization key. The graphics path has a
similar last-key shortcut; compute always probes its pipeline map.
This patch **optionally** remembers the last exact compute key and
pointer **within each command processor owner** (graphics and ASC
compute have separate maps, scratch and memo entries). Matching keys
return the same map-owned pipeline pointer; key misses still use the
original `try_emplace` map path. When shader replacement invalidates
pipelines, both memos are cleared **before** any map entry is removed.

**The optimization is OFF by default.** Enable only for an A/B test:

```bash
ISS_COMPUTE_PIPELINE_MEMO=1
```

Unset the variable, or give it any value other than `1`, to use the
original lookup. The flag is sampled at first compute lookup in a
process, so fully quit the game between OFF and ON tests. It does not
change Vulkan commands, queue waits, readbacks, GPU bindings, pipeline
compilation, module specialization, the scene image, or settings.

## Local validation (CPU only)

The stand-alone test `port/tests/test_v2_compute_pipeline_memo.cpp`
checks exact-key lookups, per-owner isolation, invalidation before
shader replacement, and **100,000 seeded mixed-owner dispatches**
against an unoptimized map. The test compiled and passed in a Linux
container using `c++ -std=c++20 -O2 -Wall -Wextra -Werror`.
The full renderer build and in-game comparison remain untested.

An illustrative one-million-lookup microbenchmark against
`std::unordered_map` (not the production `tsl::robin_map`) in the
same environment measured:

| Distribution | Plain map | Memo |
| --- | ---: | ---: |
| Same key repeatedly | 4.53 ns | 1.07 ns |
| Uniform random among 2048 keys | 3.56 ns | 3.53 ns |
| Strictly alternating two keys | 3.43 ns | 3.49 ns |

These timings are only evidence of the **possible lookup tradeoff**;
they are not FPS or frametime measurements and cannot guarantee
improvement on your RX 6900 XT. The slight alternating-key overhead is
why this patch is **never enabled automatically**. Do not merge on
the basis of synthetic benchmark numbers.

## Linux: first-time build in a separate worktree

A new Git worktree does not contain the compiled `port/out/` artifacts or
the previously provided Vulkan Memory Allocator (`vk_mem_alloc.h`) header.
If CMake stops at `Could not find VMA_INCLUDE_DIR`, copy the header from a
working sibling worktree into this one; never change the stable checkout.

```bash
cd ~/infamous-first-light-compute/port
mkdir -p out/deps/vma
# Check available sibling builds first:
find ~/infamous-first-light-readback/port/out/deps \
     ~/infamous-first-light-fps/port/out/deps \
     ~/infamous-first-light-pc/port/out/deps \
     /usr/include -name vk_mem_alloc.h -type f 2>/dev/null
# Copy the header from any existing path above to out/deps/vma/vk_mem_alloc.h.
cmake -S gpu -B out/gpu -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DTLG_LTO=OFF -DTLG_PGO=off -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ -DVMA_INCLUDE_DIR="$PWD/out/deps/vma"
cmake -S gpu_v2 -B out/gpu_v2 -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DVMA_INCLUDE_DIR="$PWD/out/deps/vma" \
  -DCMAKE_CXX_STANDARD_LIBRARIES="-ltbb"
ISS_LTO=OFF TLG_RENDERER_V2=1 bash build.sh
```

The CMake `CMP0167` Boost policy warning is informational, unrelated to
missing VMA. Check `out/tlg-probe` and `out/tlg-probe-v2` exist before launch.

## Safe testing and rollback

Keep the working `main` or PR #3 worktree completely untouched.
Create an optional **new worktree** from this experimental branch,
build independently, and use a **new** `ISS_PIPELINE_CACHE_ROOT`.
Keep existing saved games and the readback mode unchanged.
Compare OFF and ON by restarting the same experimental executable with
identical 900p FSR and game settings, in the same gameplay area.

If you notice any crash, missing effects, image change, stuttering, or
worse frametimes, remove the env variable and return immediately to
the known working build. The fact that this is an exact-key
shortcut does not establish GPU-driver stability.
