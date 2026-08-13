package synaptic

import (
 "crypto/sha256"
 "math"
)

const N = 12

type Core struct { Values [N]float64; Step uint64; Weights [N][N]float64 }

func New(context string) Core { return Core{Values: vector(context)} }

func vector(text string) [N]float64 {
 d := sha256.Sum256([]byte("0:" + text)); var out [N]float64
 for i := 0; i < N; i++ { raw := uint16(d[2*i])<<8 | uint16(d[2*i+1]); out[i] = float64(raw)/65535*2-1 }
 return out
}

func (c *Core) Advance(input string) [N]float64 {
 before := c.Values; stim := vector(input); var bias [N]float64
 for j:=0;j<N;j++ { sum:=0.0; for i:=0;i<N;i++ { sum += before[i]*c.Weights[i][j] }; bias[j]=math.Tanh(sum/N) }
 var next [N]float64; phase:=float64(c.Step+1)*0.37
 for i:=0;i<N;i++ { left:=before[(i+N-1)%N]; right:=before[(i+1)%N]; rec:=math.Sin(phase+float64(i)*math.Pi/6)*(left-right)*0.18; next[i]=math.Tanh(0.82*before[i]+0.33*stim[i]+0.25*bias[i]+rec) }
 for i:=0;i<N;i++ { for j:=0;j<N;j++ { w:=0.995*c.Weights[i][j]+0.04*before[i]*next[j]; c.Weights[i][j]=math.Max(-1,math.Min(1,w)) } }
 c.Values=next; c.Step++; return next
}
