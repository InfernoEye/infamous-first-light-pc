# Renderer-v2 readback optimization: CPU completion bookkeeping only

**Parent baseline:** `safe-fps-upscaling-20261121` (PR #2), built and launched successfully by the user. The confirmed gameplay baseline is `95e0595` on `main` (merged PR #1). This experiment is **not merged into either** and is optional.

## What the existing code does

`BufferCache::FinishReadback` obtains GPU-dirty page intervals with
`MemoryTracker::ForEachDownloadRange<false>`, invalidates the download buffer,
and writes only intersections of (a) bytes already copied from GPU and
(b) pages still requiring GPU data into guest memory.

Before this branch, **each GPU copy** rescanned **every** dirty-page interval
(`O(copies * dirty_intervals)`). `RegionManager::ForEachModifiedRange`
iterates page words in ascending address order, and `MemoryTracker::IteratePages`
visits manager regions in ascending address order, producing sorted,
non-overlapping intervals.

## Safe change

A new bounded `iss::readback::ForEachCopyIntersection` helper:
- Keeps the original linear scan for **0–4 dirty intervals**, preserving the common case.
- For **5 or more intervals**, uses `std::lower_bound` to jump to the
  first dirty interval which could overlap a particular copy, then visits only
  potentially overlapping intervals.
- Invokes the exact same `TryWriteBacking` callback for the exact same
  intersection bytes in their original order.

It does **not** change readback enabled state, copied byte ranges, Vulkan
commands, queue submission, timeline waits, dirty flags, protection, write
ordering, asynchronous readbacks, fault handling, or any graphics setting.
It should reduce CPU bookkeeping for fragmented readbacks, but **may not
increase FPS** in GPU-, shader-, or waiting-on-GPU-bound scenes.

## Validation

The standalone C++ differential test
`port/tests/test_v2_readback_intersections.cpp` compares the old and
optimized overlap algorithms with 10 explicit edge cases and **75,000
seeded randomized cases**. It was compiled with `c++ -std=c++20 -O2
-Wall -Wextra -Werror` and **passed** in an isolated Linux container.

An illustrative standalone synthetic throughput microbenchmark (no Vulkan,
not a real First Light trace) showed lower CPU iteration time for fragmented
sets with 16, 64, or 256 dirty ranges. Small sets were comparable after
restoring the original linear path. These timings are **not FPS results** or
a claim of a net gameplay speedup. Full v2 compilation, integration tests,
and user gameplay validation are still pending.

## Conservative testing

Do **not** switch the user's stable or PR #2 worktree to this unvalidated
branch. If comparing later, create a third worktree and a new isolated
shader-cache root; keep the original save directory and existing settings
backed up. Do not turn on `ISS_STALE_READBACK`, relax readback sites,
bypass waits, skip shaders, or otherwise trade visual correctness for speed.

For a basic CPU-only source test after checking out this branch:

```bash
c++ -std=c++20 -O2 -Wall -Wextra -Werror \
  -Iport/gpu_v2/gpu port/tests/test_v2_readback_intersections.cpp \
  -o /tmp/first-light-readback-test
/tmp/first-light-readback-test
```

**Stop here until basic build/tests are confirmed.** If there is no measurable
benefit, drop this entire experiment without affecting either working branch.
