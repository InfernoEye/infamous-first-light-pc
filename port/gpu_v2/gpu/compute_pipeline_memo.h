// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

namespace iss::pipeline_memo {

// An exact-key shortcut for a pipeline already owned by the caller's map.
// It never creates or changes a pipeline; the owner invalidates it before
// removing or replacing entries (e.g. when replacing a shader module).
template <typename Key, typename Pipeline>
class LastKey {
public:
    [[nodiscard]] const Pipeline* Find(const Key& key) const noexcept {
        return last_pipeline && last_key == key ? last_pipeline : nullptr;
    }

    void Remember(const Key& key, const Pipeline* pipeline) noexcept {
        last_key = key;
        last_pipeline = pipeline;
    }

    void Invalidate() noexcept { last_pipeline = nullptr; }

private:
    Key last_key{};
    const Pipeline* last_pipeline{};
};

} // namespace iss::pipeline_memo
