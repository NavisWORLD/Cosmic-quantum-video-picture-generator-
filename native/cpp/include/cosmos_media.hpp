#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace cosmos_media {

constexpr std::size_t kDimensions = 12;
using Vector12 = std::array<double, kDimensions>;

struct CstState {
    Vector12 values{};
    std::uint64_t step_index{0};

    static CstState from_context(std::string_view context);
    CstState step(std::string_view stimulus, const Vector12* association_bias = nullptr) const;
    std::uint64_t stable_hash64() const;
};

struct HebbianAssociator {
    double learning_rate{0.04};
    double decay{0.995};
    std::array<Vector12, kDimensions> weights{};

    void update(const CstState& before, const CstState& after);
    Vector12 project(const CstState& state) const;
};

struct ChunkPlan {
    std::size_t index{};
    double start{};
    double duration{};
    double overlap_before{};
    double overlap_after{};
    double narrative_progress{};
};

std::vector<ChunkPlan> plan_timeline(
    double duration,
    double chunk_seconds = 8.0,
    double overlap_seconds = 0.5
);

std::uint64_t mix_seed64(
    std::string_view name_space,
    const std::vector<std::string_view>& parts
);

}  // namespace cosmos_media
