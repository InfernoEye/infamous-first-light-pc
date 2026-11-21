// SPDX-License-Identifier: GPL-2.0-or-later
// Standalone: c++ -std=c++20 -O2 -Iport/gpu_v2/gpu port/tests/test_v2_readback_intersections.cpp -o /tmp/readback-intersections-test
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <random>
#include <utility>
#include <vector>

#include "readback_intersections.h"

using Address = std::uint64_t;
using Interval = std::pair<Address, Address>;
using Intervals = std::vector<Interval>;

// Reference: the original O(copies * dirty_ranges) FinishReadback loop.
static Intervals OriginalIntersections(const Intervals& pages, Address copy_start,
                                        Address copy_end) {
    Intervals found;
    for (const auto& [start, end] : pages) {
        const Address lo = std::max(copy_start, start);
        const Address hi = std::min(copy_end, end);
        if (lo < hi) {
            found.emplace_back(lo, hi);
        }
    }
    return found;
}

static Intervals OptimizedIntersections(const Intervals& pages, Address copy_start,
                                         Address copy_end) {
    Intervals found;
    iss::readback::ForEachCopyIntersection(pages, copy_start, copy_end,
                                           [&](Address start, Address end) {
                                               found.emplace_back(start, end);
                                           });
    return found;
}

static void Check(const Intervals& pages, Address start, Address end) {
    assert(OriginalIntersections(pages, start, end) ==
           OptimizedIntersections(pages, start, end));
}

int main() {
    const Intervals empty;
    Check(empty, 0, 1024);
    Check({{0, 16}}, 16, 20);           // touching end: no overlap
    Check({{16, 32}}, 0, 16);           // touching start: no overlap
    Check({{16, 32}}, 16, 32);          // full copy
    Check({{16, 32}}, 17, 31);          // partial copy
    Check({{16, 32}}, 16, 16);          // empty copy
    Check({{0, 8}, {16, 24}, {64, 80}}, 6, 65); // scattered pages
    Check({{0, 16}, {16, 32}}, 8, 24);  // adjacent dirty regions
    Check({{0, 4}, {12, 16}, {1024, 2048}}, 2048, 4096);
    Check({{0, 4}, {12, 16}, {1024, 2048}}, 4096, 8192);

    // Repeat against the original algorithm with varied sizes and gaps.
    std::mt19937_64 rng{0xD157CAFEu};
    for (unsigned trial = 0; trial < 3000; ++trial) {
        Intervals pages;
        Address at = rng() % 64;
        const unsigned count = rng() % 128;
        for (unsigned i = 0; i < count; ++i) {
            at += rng() % 1024;
            const Address end = at + 1 + (rng() % 512);
            pages.emplace_back(at, end);
            at = end;
        }
        for (unsigned copy = 0; copy < 25; ++copy) {
            const Address start = rng() % (at + 4096);
            const Address size = rng() % 4096;
            Check(pages, start, start + size);
        }
    }
}
