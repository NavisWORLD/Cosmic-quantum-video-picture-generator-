import { createHash } from 'node:crypto';

const N = 12;
const vec = (text) => {
  const d = createHash('sha256').update(`0:${text}`, 'utf8').digest();
  return Array.from({length:N}, (_,i) => ((((d[2*i]<<8)|d[2*i+1])/65535)*2)-1);
};

export class SynapticCore {
  constructor(context='') { this.values=vec(context); this.step=0; this.weights=Array.from({length:N},()=>Array(N).fill(0)); }
  project() { return Array.from({length:N},(_,j)=>Math.tanh(this.values.reduce((s,v,i)=>s+v*this.weights[i][j],0)/N)); }
  advance(input) {
    const before=[...this.values], stim=vec(input), bias=this.project(), phase=(this.step+1)*0.37;
    const next=before.map((v,i)=>Math.tanh(0.82*v+0.33*stim[i]+0.25*bias[i]+0.18*Math.sin(phase+i*Math.PI/6)*(before[(i+N-1)%N]-before[(i+1)%N])));
    for(let i=0;i<N;i++) for(let j=0;j<N;j++) this.weights[i][j]=Math.max(-1,Math.min(1,0.995*this.weights[i][j]+0.04*before[i]*next[j]));
    this.values=next; this.step++; return [...next];
  }
  snapshot() { return {protocol:'cosmos.synaptic.v1',dimensions:N,step_index:this.step,values:[...this.values],weights:this.weights.map(r=>[...r])}; }
}
