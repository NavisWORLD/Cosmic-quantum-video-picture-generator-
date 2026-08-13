#include "cosmos_media.hpp"

#include <iostream>
#include <string>
#include <vector>

int main() {
    using namespace cosmos_media;

    auto state = CstState::from_context("a continuous expedition through an ocean planet");
    HebbianAssociator hebbian;
    const auto plan = plan_timeline(60.0, 8.0, 0.5);

    for (const auto& chunk : plan) {
        const std::string index = std::to_string(chunk.index);
        const std::string progress = std::to_string(chunk.narrative_progress);
        const auto seed = mix_seed64("cosmos-media-v1", {index, progress});
        const auto before = state;
        const auto bias = hebbian.project(before);
        const std::string stimulus = "chunk=" + index + " seed=" + std::to_string(seed);
        state = before.step(stimulus, &bias);
        hebbian.update(before, state);
    }

    std::cout << "planned " << plan.size() << " chunks\n";
    std::cout << "final state hash64 " << state.stable_hash64() << "\n";
    return 0;
}
