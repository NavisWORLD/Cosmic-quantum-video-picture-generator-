use sha2::{Digest, Sha256};
use std::f64::consts::PI;

pub const DIMENSIONS: usize = 12;

#[derive(Clone, Debug, PartialEq)]
pub struct CstState {
    pub values: [f64; DIMENSIONS],
    pub step_index: u64,
}

impl Default for CstState {
    fn default() -> Self {
        Self {
            values: [0.0; DIMENSIONS],
            step_index: 0,
        }
    }
}

impl CstState {
    pub fn from_context(context: &str) -> Self {
        Self {
            values: stable_unit_values(context),
            step_index: 0,
        }
    }

    pub fn step(&self, stimulus: &str, association_bias: Option<[f64; DIMENSIONS]>) -> Self {
        let stim = stable_unit_values(stimulus);
        let bias = association_bias.unwrap_or([0.0; DIMENSIONS]);
        let omega = 0.37_f64;
        let damping = 0.82_f64;
        let gate = 0.33_f64;
        let phase = (self.step_index + 1) as f64 * omega;
        let mut next = [0.0; DIMENSIONS];
        for i in 0..DIMENSIONS {
            let left = self.values[(i + DIMENSIONS - 1) % DIMENSIONS];
            let right = self.values[(i + 1) % DIMENSIONS];
            let coupled = left - right;
            let recurrent = (phase + i as f64 * (PI / 6.0)).sin() * coupled * 0.18;
            let drive = stim[i] * gate + bias[i] * 0.25;
            next[i] = (damping * self.values[i] + drive + recurrent).tanh();
        }
        Self {
            values: next,
            step_index: self.step_index + 1,
        }
    }

    pub fn hash_hex(&self) -> String {
        let mut h = Sha256::new();
        for v in self.values {
            h.update(format!("{v:.9}").as_bytes());
            h.update([0]);
        }
        h.update(self.step_index.to_be_bytes());
        format!("{:x}", h.finalize())
    }
}

#[derive(Clone, Debug)]
pub struct HebbianAssociator {
    pub learning_rate: f64,
    pub decay: f64,
    pub weights: [[f64; DIMENSIONS]; DIMENSIONS],
}

impl Default for HebbianAssociator {
    fn default() -> Self {
        Self {
            learning_rate: 0.04,
            decay: 0.995,
            weights: [[0.0; DIMENSIONS]; DIMENSIONS],
        }
    }
}

impl HebbianAssociator {
    pub fn update(&mut self, before: &CstState, after: &CstState) {
        for i in 0..DIMENSIONS {
            for j in 0..DIMENSIONS {
                let w = self.weights[i][j] * self.decay
                    + self.learning_rate * before.values[i] * after.values[j];
                self.weights[i][j] = w.clamp(-1.0, 1.0);
            }
        }
    }

    pub fn project(&self, state: &CstState) -> [f64; DIMENSIONS] {
        let mut out = [0.0; DIMENSIONS];
        for j in 0..DIMENSIONS {
            let mut sum = 0.0;
            for i in 0..DIMENSIONS {
                sum += state.values[i] * self.weights[i][j];
            }
            out[j] = (sum / DIMENSIONS as f64).tanh();
        }
        out
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ChunkPlan {
    pub index: usize,
    pub start: f64,
    pub duration: f64,
    pub overlap_before: f64,
    pub overlap_after: f64,
    pub narrative_progress: f64,
}

pub fn plan_timeline(
    duration: f64,
    chunk_seconds: f64,
    overlap_seconds: f64,
) -> Result<Vec<ChunkPlan>, String> {
    if !duration.is_finite() || duration <= 0.0 {
        return Err("duration must be a positive finite number".into());
    }
    if !chunk_seconds.is_finite() || chunk_seconds <= 0.0 {
        return Err("chunk_seconds must be a positive finite number".into());
    }
    if overlap_seconds < 0.0 || overlap_seconds >= chunk_seconds {
        return Err("overlap_seconds must be >= 0 and smaller than chunk_seconds".into());
    }
    let count = (duration / chunk_seconds).ceil() as usize;
    let mut out = Vec::with_capacity(count);
    for index in 0..count {
        let start = index as f64 * chunk_seconds;
        let length = (duration - start).min(chunk_seconds);
        out.push(ChunkPlan {
            index,
            start,
            duration: length,
            overlap_before: if index == 0 { 0.0 } else { overlap_seconds.min(length / 2.0) },
            overlap_after: if index + 1 == count { 0.0 } else { overlap_seconds.min(length / 2.0) },
            narrative_progress: (start + length / 2.0) / duration,
        });
    }
    Ok(out)
}

pub fn mix_seed(namespace: &str, parts: &[&[u8]]) -> (u64, String) {
    let mut h = Sha256::new();
    h.update(namespace.as_bytes());
    h.update([0]);
    for part in parts {
        h.update((part.len() as u64).to_be_bytes());
        h.update(part);
    }
    let digest = h.finalize();
    let mut first = [0_u8; 8];
    first.copy_from_slice(&digest[..8]);
    let seed = u64::from_be_bytes(first) & 0x7fff_ffff_ffff_ffff;
    (seed, format!("{:x}", digest))
}

fn stable_unit_values(text: &str) -> [f64; DIMENSIONS] {
    let mut out = [0.0; DIMENSIONS];
    let mut written = 0;
    let mut counter = 0_u64;
    while written < DIMENSIONS {
        let mut h = Sha256::new();
        h.update(format!("{counter}:{text}").as_bytes());
        let digest = h.finalize();
        for pair in digest.chunks_exact(2) {
            if written == DIMENSIONS {
                break;
            }
            let raw = u16::from_be_bytes([pair[0], pair[1]]) as f64;
            out[written] = (raw / 65535.0) * 2.0 - 1.0;
            written += 1;
        }
        counter += 1;
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hour_plan_has_450_chunks() {
        let chunks = plan_timeline(3600.0, 8.0, 0.5).unwrap();
        assert_eq!(chunks.len(), 450);
        assert_eq!(chunks[449].start, 3592.0);
    }

    #[test]
    fn state_stays_bounded() {
        let mut state = CstState::from_context("cosmos");
        for _ in 0..100 {
            state = state.step("continue", None);
        }
        assert!(state.values.iter().all(|v| *v >= -1.0 && *v <= 1.0));
    }

    #[test]
    fn seed_is_stable() {
        let a = mix_seed("ns", &[b"a", b"b"]);
        let b = mix_seed("ns", &[b"a", b"b"]);
        assert_eq!(a, b);
    }
}
