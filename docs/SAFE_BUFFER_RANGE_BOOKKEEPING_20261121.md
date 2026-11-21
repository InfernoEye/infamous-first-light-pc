# Renderer-v2 CPU read-access bookkeeping — PR #5 experiment

**Baseline:** merged PR #4, commit `0cf4674e5a8344d8d61ae0d1da526eae112e4a8b` on `main`. PR #5 lives on a separate branch. It does not modify the working installation or the confirmed renderer-v2 readback/FidelityFX settings.

## Why examine this

`Runtime::LazyReadList::Overlaps` checks CPU-side buffer read-access
ranges before writing to a Vulkan buffer. Originally it always called
`Merge()`, even when there were **zero** pending reads and `Merge()` would
immediately return. This can occur repeatedly during the default
`ISS_LAZY_READ_RANGES=0` path.

With the existing `ISS_LAZY_READ_RANGES=1` experiment, `Merge()`
coalesces newly recorded buffer read ranges with an already sorted list
of ranges. For **one pending interval**, the old algorithm copied all
existing ranges to a vector, sorted them, cleared the list, and built
the same union again, even though `IntervalList::Add` can insert and
coalesce exactly one interval directly.

## Exact changes

1. `Overlaps` calls `Merge()` only if the pending vector is nonempty.
   Previously `Merge()` itself checked this condition immediately and
   returned; all query results are unchanged.
2. If there is exactly one pending range, `MergePendingReadRanges` uses
   `IntervalList::Add` directly; the existing full sort-and-coalesce
   algorithm remains for two or more pending ranges.

The resulting sorted interval union and **every `Overlaps` result**
are identical. No Vulkan barrier is added, removed, or reordered.
No GPU queue scheduling, shader compilation, shader data, readback,
guest memory, framebuffer, graphics preset, or image quality is changed.

The `ISS_LAZY_READ_RANGES` setting itself is **not** changed or enabled
by this PR. This is CPU-only codepath cleanup.

## Verification

A standalone differential test lives in
`port/tests/test_v2_buffer_access_merge.cpp`. It compares the old
merge logic against the new helper for adjacency, containment, disjoint
ranges, a seeded run of **130,000 mixed add/query operations**, and
**1,000 randomized unsorted batches**.

A local Linux C++20 build of the merge helper and 130,000 synthetic
operations passed. **This does not substitute for the full standalone
repo test, a full Linux renderer build or actual gameplay testing**.

Compile the repository test from the experimental worktree root:

```bash
c++ -std=c++20 -O2 -Wall -Wextra -Werror -Iport/gpu_v2/gpu port/tests/test_v2_buffer_access_merge.cpp -o /tmp/first-light-buffer-ranges-test && /tmp/first-light-buffer-ranges-test && echo "Range tests passed"
```

## Game A/B and rollback

Use a separate `git worktree`, copied VMA header, existing Linux
CMake/oneTBB flags and a **separate pipeline cache root** as in the PR #4
test workflow. Compare the same scene with your existing working
settings, ideally after warming shaders. The new path that avoids the
empty Merge call is used with the **normal default** settings.
Do **not** change `ISS_LAZY_READ_RANGES` for the first comparison.
The new single-range merge only affects a game run explicitly using
`ISS_LAZY_READ_RANGES=1`; that earlier experimental setting remains
disabled unless intentionally tested in isolation.

Any drop in FPS, frametime stability, graphics correctness or GPU
stability is a stop signal. Return to the merged `main` build and
leave this PR unmerged. No performance gain is claimed without
user gameplay evidence.
