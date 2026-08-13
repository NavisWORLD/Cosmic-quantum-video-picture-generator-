export declare class SynapticCore {
  values: number[];
  step: number;
  weights: number[][];
  constructor(context?: string);
  project(): number[];
  advance(input: string): number[];
  snapshot(): {
    protocol: 'cosmos.synaptic.v1';
    dimensions: 12;
    step_index: number;
    values: number[];
    weights: number[][];
  };
}
