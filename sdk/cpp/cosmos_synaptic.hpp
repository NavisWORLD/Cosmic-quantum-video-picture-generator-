#pragma once
#include "../../native/cpp/include/cosmos_media.hpp"

namespace cosmos_sdk {

class SynapticCore {
 public:
  explicit SynapticCore(std::string_view context)
      : state_(cosmos_media::CstState::from_context(context)) {}

  cosmos_media::Vector12 advance(std::string_view input) {
    const auto before = state_;
    const auto bias = associations_.project(before);
    const auto after = before.step(input, &bias);
    associations_.update(before, after);
    state_ = after;
    return state_.values;
  }

  cosmos_media::Vector12 project() const { return associations_.project(state_); }
  const cosmos_media::CstState& state() const { return state_; }
  const cosmos_media::HebbianAssociator& associations() const { return associations_; }

 private:
  cosmos_media::CstState state_;
  cosmos_media::HebbianAssociator associations_;
};

}  // namespace cosmos_sdk
