#include "../include/cosmos_synaptic.h"
#include "../../cpp/include/cosmos_media.hpp"
#include <algorithm>
#include <new>
#include <string_view>

struct CosmosSynapticHandle {
  cosmos_media::CstState state;
  cosmos_media::HebbianAssociator associations;
};

static CosmosSynapticHandle* ptr(cosmos_synaptic_handle h) {
  return static_cast<CosmosSynapticHandle*>(h);
}

extern "C" cosmos_synaptic_handle cosmos_synaptic_create(const char* context) {
  try {
    auto* h = new CosmosSynapticHandle{};
    h->state = cosmos_media::CstState::from_context(context ? std::string_view(context) : std::string_view{});
    return h;
  } catch (...) {
    return nullptr;
  }
}

extern "C" void cosmos_synaptic_destroy(cosmos_synaptic_handle handle) { delete ptr(handle); }

extern "C" int cosmos_synaptic_advance(cosmos_synaptic_handle handle, const char* input, double out_values[12]) {
  if (!handle || !input || !out_values) return 0;
  auto* h = ptr(handle);
  const auto before = h->state;
  const auto bias = h->associations.project(before);
  const auto after = before.step(std::string_view(input), &bias);
  h->associations.update(before, after);
  h->state = after;
  std::copy(h->state.values.begin(), h->state.values.end(), out_values);
  return 1;
}

extern "C" int cosmos_synaptic_project(cosmos_synaptic_handle handle, double out_values[12]) {
  if (!handle || !out_values) return 0;
  const auto values = ptr(handle)->associations.project(ptr(handle)->state);
  std::copy(values.begin(), values.end(), out_values);
  return 1;
}

extern "C" uint64_t cosmos_synaptic_step_index(cosmos_synaptic_handle handle) {
  return handle ? ptr(handle)->state.step_index : 0;
}

extern "C" int cosmos_synaptic_values(cosmos_synaptic_handle handle, double out_values[12]) {
  if (!handle || !out_values) return 0;
  const auto& values = ptr(handle)->state.values;
  std::copy(values.begin(), values.end(), out_values);
  return 1;
}
