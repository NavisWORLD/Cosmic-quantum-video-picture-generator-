#include "cosmos_media.hpp"

#include <cassert>
#include <cmath>
#include <iostream>

int main() {
    using namespace cosmos_media;

    const auto plan = plan_timeline(3600.0, 8.0, 0.5);
    assert(plan.size() == 450);
    assert(std::abs(plan.back().start - 3592.0) < 1e-9);

    auto state = CstState::from_context("cosmos");
    for (int i = 0; i < 100; ++i) {
        state = state.step("continue");
    }
    for (double value : state.values) {
        assert(value >= -1.0 && value <= 1.0);
    }

    const auto first = mix_seed64("ns", {"a", "b"});
    const auto second = mix_seed64("ns", {"a", "b"});
    const auto changed = mix_seed64("ns", {"a", "c"});
    assert(first == second);
    assert(first != changed);

    std::cout << "COSMOS C++ core tests passed\n";
    return 0;
}
