
mod inner {
    pub struct X();
    pub struct Y();
}

mod z {
    use super::inner::{self, X};

    fn f() {
        let y = inner::Y();
    }
}

