mod ast { pub mod make { pub mod ext { pub fn foo() {} } } }
fn main() {
    make::ext::foo;
}
