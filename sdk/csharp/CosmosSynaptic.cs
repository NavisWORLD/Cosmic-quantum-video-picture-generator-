using System;
using System.Security.Cryptography;
using System.Text;

namespace Cosmos.Sdk;

public sealed class SynapticCore {
    public const int N=12;
    public double[] Values { get; } = new double[N];
    public double[,] Weights { get; } = new double[N,N];
    public long Step { get; private set; }
    public SynapticCore(string context="") { Array.Copy(Vector(context),Values,N); }
    static double[] Vector(string text){ var d=SHA256.HashData(Encoding.UTF8.GetBytes("0:"+text)); var o=new double[N]; for(int i=0;i<N;i++){ int raw=(d[2*i]<<8)|d[2*i+1]; o[i]=((double)raw/65535.0)*2.0-1.0; } return o; }
    public double[] Project(){ var o=new double[N]; for(int j=0;j<N;j++){ double s=0; for(int i=0;i<N;i++) s+=Values[i]*Weights[i,j]; o[j]=Math.Tanh(s/N); } return o; }
    public double[] Advance(string input){ var before=(double[])Values.Clone(); var stim=Vector(input); var bias=Project(); var next=new double[N]; double phase=(Step+1)*0.37; for(int i=0;i<N;i++){ double rec=Math.Sin(phase+i*Math.PI/6.0)*(before[(i+N-1)%N]-before[(i+1)%N])*0.18; next[i]=Math.Tanh(0.82*before[i]+0.33*stim[i]+0.25*bias[i]+rec); } for(int i=0;i<N;i++) for(int j=0;j<N;j++) Weights[i,j]=Math.Max(-1,Math.Min(1,0.995*Weights[i,j]+0.04*before[i]*next[j])); Array.Copy(next,Values,N); Step++; return (double[])next.Clone(); }
}
