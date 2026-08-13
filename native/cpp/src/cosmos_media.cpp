#include "cosmos_media.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <stdexcept>

namespace cosmos_media {
namespace {

constexpr std::uint64_t kFnvOffset = 1469598103934665603ULL;
constexpr std::uint64_t kFnvPrime = 1099511628211ULL;
constexpr double kPi = 3.141592653589793238462643383279502884;

std::uint64_t fnv1a_bytes(const unsigned char* data, std::size_t size, std::uint64_t seed = kFnvOffset) {
    std::uint64_t hash = seed;
    for (std::size_t i = 0; i < size; ++i) {
        hash ^= static_cast<std::uint64_t>(data[i]);
        hash *= kFnvPrime;
    }
    return hash;
}

std::uint64_t fnv1a(std::string_view text, std::uint64_t seed = kFnvOffset) {
    return fnv1a_bytes(reinterpret_cast<const unsigned char*>(text.data()), text.size(), seed);
}

std::uint64_t splitmix64(std::uint64_t& x) {
    x += 0x9e3779b97f4a7c15ULL;
    std::uint64_t z = x;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

Vector12 stable_unit_values(std::string_view text) {
    Vector12 out{};
    std::uint64_t seed = fnv1a(text);
    for (std::size_t i = 0; i < kDimensions; ++i) {
        auto value = splitmix64(seed);
        const double unit = static_cast<double>(value >> 11) / static_cast<double>(1ULL << 53);
        out[i] = unit * 2.0 - 1.0;
    }
    return out;
}

}  // namespace

CstState CstState::from_context(std::string_view context) {
    CstState state;
    state.values = stable_unit_values(context);
    return state;
}

CstState CstState::step(std::string_view stimulus, const Vector12* association_bias) const {
    const auto stim = stable_unit_values(stimulus);
    Vector12 bias{};
    if (association_bias != nullptr) {
        bias = *association_bias;
    }

    constexpr double omega = 0.37;
    constexpr double damping = 0.82;
    constexpr double gate = 0.33;
    const double phase = static_cast<double>(step_index + 1) * omega;

    CstState next;
    next.step_index = step_index + 1;
    for (std::size_t i = 0; i < kDimensions; ++i) {
        const double left = values[(i + kDimensions - 1) % kDimensions];
        const double right = values[(i + 1) % kDimensions];
        const double coupled = left - right;
        const double recurrent = std::sin(phase + static_cast<double>(i) * (kPi / 6.0)) * coupled * 0.18;
        const double drive = stim[i] * gate + bias[i] * 0.25;
        next.values[i] = std::tanh(damping * values[i] + drive + recurrent);
    }
    return next;
}

std::uint64_t CstState::stable_hash64() const {
    std::uint64_t hash = kFnvOffset;
    for (double value : values) {
        unsigned char bytes[sizeof(double)];
        std::memcpy(bytes, &value, sizeof(double));
        hash = fnv1a_bytes(bytes, sizeof(double), hash);
    }
    unsigned char step_bytes[sizeof(step_index)];
    std::memcpy(step_bytes, &step_index, sizeof(step_index));
    return fnv1a_bytes(step_bytes, sizeof(step_index), hash);
}

void HebbianAssociator::update(const CstState& before, const CstState& after) {
    for (std::size_t i = 0; i < kDimensions; ++i) {
        for (std::size_t j = 0; j < kDimensions; ++j) {
            const double candidate = weights[i][j] * decay
                + learning_rate * before.values[i] * after.values[j];
            weights[i][j] = std::clamp(candidate, -1.0, 1.0);
        }
    }
}

Vector12 HebbianAssociator::project(const CstState& state) const {
    Vector12 out{};
    for (std::size_t j = 0; j < kDimensions; ++j) {
        double sum = 0.0;
        for (std::size_t i = 0; i < kDimensions; ++i) {
            sum += state.values[i] * weights[i][j];
        }
        out[j] = std::tanh(sum / static_cast<double>(kDimensions));
    }
    return out;
}

std::vector<ChunkPlan> plan_timeline(double duration, double chunk_seconds, double overlap_seconds) {
    if (!std::isfinite(duration) || duration <= 0.0) {
        throw std::invalid_argument("duration must be a positive finite number");
    }
    if (!std::isfinite(chunk_seconds) || chunk_seconds <= 0.0) {
        throw std::invalid_argument("chunk_seconds must be a positive finite number");
    }
    if (!std::isfinite(overlap_seconds) || overlap_seconds < 0.0 || overlap_seconds >= chunk_seconds) {
        throw std::invalid_argument("overlap_seconds must be >= 0 and smaller than chunk_seconds");
    }

    const auto count = static_cast<std::size_t>(std::ceil(duration / chunk_seconds));
    std::vector<ChunkPlan> out;
    out.reserve(count);
    for (std::size_t index = 0; index < count; ++index) {
        const double start = static_cast<double>(index) * chunk_seconds;
        const double length = std::min(chunk_seconds, duration - start);
        out.push_back(ChunkPlan{
            index,
            start,
            length,
            index == 0 ? 0.0 : std::min(overlap_seconds, length / 2.0),
            index + 1 == count ? 0.0 : std::min(overlap_seconds, length / 2.0),
            (start + length / 2.0) / duration,
        });
    }
    return out;
}

std::uint64_t mix_seed64(std::string_view name_space, const std::vector<std::string_view>& parts) {
    std::uint64_t hash = fnv1a(name_space);
    const unsigned char zero = 0;
    hash = fnv1a_bytes(&zero, 1, hash);
    for (auto part : parts) {
        const std::uint64_t length = static_cast<std::uint64_t>(part.size());
        unsigned char length_bytes[sizeof(length)];
        std::memcpy(length_bytes, &length, sizeof(length));
        hash = fnv1a_bytes(length_bytes, sizeof(length), hash);
        hash = fnv1a(part, hash);
    }
    return hash & 0x7fff'ffff'ffff'ffffULL;
}

}  // namespace cosmos_media
