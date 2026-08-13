package cosmos.sdk;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

public final class CosmosSynaptic {
  public static final int N=12;
  public final double[] values=new double[N];
  public final double[][] weights=new double[N][N];
  public long step=0;
  public CosmosSynaptic(String context){ double[] v=vector(context); System.arraycopy(v,0,values,0,N); }
  static double[] vector(String text){ try { byte[] d=MessageDigest.getInstance("SHA-256").digest(("0:"+text).getBytes(StandardCharsets.UTF_8)); double[] o=new double[N]; for(int i=0;i<N;i++){ int raw=((d[2*i]&255)<<8)|(d[2*i+1]&255); o[i]=((double)raw/65535.0)*2.0-1.0; } return o; } catch(Exception e){ throw new RuntimeException(e); } }
  public double[] project(){ double[] o=new double[N]; for(int j=0;j<N;j++){ double s=0; for(int i=0;i<N;i++) s+=values[i]*weights[i][j]; o[j]=Math.tanh(s/N); } return o; }
  public double[] advance(String input){ double[] before=values.clone(), stim=vector(input), bias=project(), next=new double[N]; double phase=(step+1)*0.37; for(int i=0;i<N;i++){ double rec=Math.sin(phase+i*Math.PI/6.0)*(before[(i+N-1)%N]-before[(i+1)%N])*0.18; next[i]=Math.tanh(0.82*before[i]+0.33*stim[i]+0.25*bias[i]+rec); } for(int i=0;i<N;i++) for(int j=0;j<N;j++) weights[i][j]=Math.max(-1,Math.min(1,0.995*weights[i][j]+0.04*before[i]*next[j])); System.arraycopy(next,0,values,0,N); step++; return next.clone(); }
}
