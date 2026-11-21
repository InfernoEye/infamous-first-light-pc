// SPDX-License-Identifier: GPL-2.0-or-later
// Compile and run with a single shell line (no line-continuation backslashes):
// c++ -std=c++20 -O2 -Wall -Wextra -Werror -Iport/gpu_v2/gpu port/tests/test_v2_compute_pipeline_memo.cpp -o /tmp/first-light-compute-test && /tmp/first-light-compute-test
#include <cassert>
#include <cstdint>
#include <memory>
#include <random>
#include <unordered_map>
#include <vector>

#include "compute_pipeline_memo.h"

namespace {
struct ComputeKey {
    std::uint64_t value;
    friend bool operator==(const ComputeKey&, const ComputeKey&) = default;
};
struct Pipeline {
    std::uint64_t identity;
};
struct Owner {
    std::unordered_map<std::uint64_t, std::unique_ptr<Pipeline>> pipelines;
    iss::pipeline_memo::LastKey<ComputeKey, Pipeline> memo;
    unsigned map_lookups{};

    // The production code performs this lookup after computing an exact key.
    const Pipeline* Lookup(ComputeKey key) {
        if (const auto* hit = memo.Find(key)) return hit;
        ++map_lookups;
        const auto [entry, created] = pipelines.try_emplace(key.value);
        if (created) entry->second = std::make_unique<Pipeline>(
            Pipeline{key.value + 0x100000000ULL * owner_id});
        const auto* pipeline = entry->second.get();
        memo.Remember(key, pipeline);
        return pipeline;
    }

    void ReplaceShader() {
        // Invalidate before a shader replacement can destroy cached pipelines.
        memo.Invalidate();
        pipelines.clear();
    }
    unsigned owner_id{};
};
} // namespace

int main() {
    Owner graphics{}, asc{};
    graphics.owner_id = 1;
    asc.owner_id = 2;
    const Pipeline* gp = graphics.Lookup({7});
    const Pipeline* cp = asc.Lookup({7});
    assert(gp != cp);
    assert(gp->identity == 0x100000007ULL);
    assert(cp->identity == 0x200000007ULL);
    assert(graphics.Lookup({7}) == gp && asc.Lookup({7}) == cp);
    assert(graphics.map_lookups == 1 && asc.map_lookups == 1);

    // A key miss goes through the owning map. A same-key hit skips it.
    assert(graphics.Lookup({8})->identity == 0x100000008ULL);
    assert(graphics.Lookup({7}) == gp);
    assert(graphics.map_lookups == 3);
    graphics.ReplaceShader();
    assert(graphics.memo.Find({7}) == nullptr);
    const auto* replacement = graphics.Lookup({7});
    assert(replacement->identity == 0x100000007ULL);
    assert(graphics.map_lookups == 4);
    assert(asc.Lookup({7}) == cp); // graphics invalidation cannot affect ASC
    assert(asc.map_lookups == 1);

    // Compare exact outputs to a separate ordinary map for 100,000 dispatches
    // with short same-key runs, alternating owners and random keys.
    std::mt19937_64 rng{0xC0A57ULL};
    std::unordered_map<std::uint64_t, std::uint64_t> reference[2];
    Owner owners[2];
    owners[0].owner_id = 1;
    owners[1].owner_id = 2;
    std::uint64_t last_key = 0;
    for (unsigned i = 0; i < 100000; ++i) {
        const unsigned index = static_cast<unsigned>(rng() % 2);
        const std::uint64_t key =
            (i % 5 == 0) ? (last_key = rng() % 2048) : last_key;
        auto& owner = owners[index];
        if (i % 1501 == 0) {
            owner.ReplaceShader();
            reference[index].clear();
        }
        const std::uint64_t expected =
            reference[index].try_emplace(key, key + 0x100000000ULL * owner.owner_id)
                .first->second;
        assert(owner.Lookup({key})->identity == expected);
    }
    // Sanity-check hot-key repetition actually bypasses the map.
    for (unsigned i = 0; i < 100; ++i)
        assert(owners[0].Lookup({123456})->identity == 0x10001E240ULL);
    const unsigned lookups = owners[0].map_lookups;
    for (unsigned i = 0; i < 1000; ++i) (void)owners[0].Lookup({123456});
    assert(owners[0].map_lookups == lookups);
}
