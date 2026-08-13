#include "cosmos_synaptic.hpp"

int main() {
  cosmos_sdk::SynapticCore core("ci");
  core.advance("next");
  return core.state().step_index == 1 ? 0 : 1;
}
