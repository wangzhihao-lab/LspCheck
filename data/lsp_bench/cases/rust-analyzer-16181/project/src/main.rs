mod m {
    pub mod x {
        pub struct A;
        pub struct B;
    }
    pub mod y {
        pub struct C;
    }
}

use m::{
    x::{A, B},
    y::C,
};

fn main() {
    B;
}
