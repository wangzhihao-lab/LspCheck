fn foo() {}
fn baz(_: impl FnOnce()) {}
fn bar() {
    baz(|| fo);
}
