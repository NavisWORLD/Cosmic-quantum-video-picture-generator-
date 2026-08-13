use cosmos_quantum_media_core::{mix_seed, plan_timeline, CstState, HebbianAssociator};

fn main() {
    let mut state = CstState::from_context("a continuous expedition through an ocean planet");
    let mut hebbian = HebbianAssociator::default();
    let plan = plan_timeline(60.0, 8.0, 0.5).expect("timeline");

    for chunk in &plan {
        let seed_text = format!("{}:{}", chunk.index, chunk.narrative_progress);
        let (seed, _) = mix_seed("cosmos-media-v1", &[seed_text.as_bytes()]);
        let before = state.clone();
        let bias = hebbian.project(&before);
        state = before.step(&format!("chunk:{} seed:{}", chunk.index, seed), Some(bias));
        hebbian.update(&before, &state);
    }

    println!("planned {} chunks", plan.len());
    println!("final state hash {}", state.hash_hex());
}
