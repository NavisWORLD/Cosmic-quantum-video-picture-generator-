use crate::{CstState, HebbianAssociator, DIMENSIONS};

#[derive(Clone, Debug)]
pub struct SynapticCore {
    pub state: CstState,
    pub associator: HebbianAssociator,
}

impl SynapticCore {
    pub fn from_context(context: &str) -> Self {
        Self {
            state: CstState::from_context(context),
            associator: HebbianAssociator::default(),
        }
    }

    pub fn advance(&mut self, input: &str, learn: bool) -> [f64; DIMENSIONS] {
        let before = self.state.clone();
        let bias = self.associator.project(&before);
        let after = before.step(input, Some(bias));
        if learn {
            self.associator.update(&before, &after);
        }
        self.state = after;
        self.state.values
    }

    pub fn projection(&self) -> [f64; DIMENSIONS] {
        self.associator.project(&self.state)
    }
}
