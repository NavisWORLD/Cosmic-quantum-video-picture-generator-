use cosmos_quantum_media_core::{CstState, HebbianAssociator, DIMENSIONS};

#[derive(Clone, Debug)]
pub struct SynapticCore {
    pub state: CstState,
    pub associations: HebbianAssociator,
}

impl SynapticCore {
    pub fn new(context: &str) -> Self {
        Self { state: CstState::from_context(context), associations: HebbianAssociator::default() }
    }

    pub fn advance(&mut self, input: &str) -> [f64; DIMENSIONS] {
        let before = self.state.clone();
        let bias = self.associations.project(&before);
        let after = before.step(input, Some(bias));
        self.associations.update(&before, &after);
        self.state = after;
        self.state.values
    }

    pub fn project(&self) -> [f64; DIMENSIONS] {
        self.associations.project(&self.state)
    }
}
