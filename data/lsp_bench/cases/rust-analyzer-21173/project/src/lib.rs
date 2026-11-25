pub trait Tr {
    type Assoc;

    fn f(&self, handle: Self::Assoc);
}

pub struct ConstGeneric<const N: usize>;

impl<const N: usize> Tr for &ConstGeneric<N> {
    type Assoc = AssocTy;

    fn f(&self, a: Self::Assoc) {
        a.x
        
    }
}

pub struct AssocTy {
    x: (),
}
