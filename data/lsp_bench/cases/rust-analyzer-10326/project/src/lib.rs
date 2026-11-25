trait A<T: ?Sized> {
    fn a(&self) -> &T;
}
trait B {}

impl<'a, T: B> A<dyn 'a + B> for T {} // <-- not all trait items implemented, missing: `a` …
