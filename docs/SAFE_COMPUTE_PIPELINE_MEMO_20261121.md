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
