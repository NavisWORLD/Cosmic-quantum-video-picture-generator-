#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void* cosmos_synaptic_handle;

cosmos_synaptic_handle cosmos_synaptic_create(const char* context);
void cosmos_synaptic_destroy(cosmos_synaptic_handle handle);
int cosmos_synaptic_advance(cosmos_synaptic_handle handle, const char* input, double out_values[12]);
int cosmos_synaptic_project(cosmos_synaptic_handle handle, double out_values[12]);
uint64_t cosmos_synaptic_step_index(cosmos_synaptic_handle handle);
int cosmos_synaptic_values(cosmos_synaptic_handle handle, double out_values[12]);

#ifdef __cplusplus
}
#endif
