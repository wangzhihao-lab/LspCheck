use std::sync::{Arc, Mutex};
fn need(x: Arc<Mutex<dyn FnMut(i32) -> i32>>) {
    todo!()
}
fn main() {
    let callback = |x| x;
    let mut callback = need(Arc::new(Mutex::new(callback)));
}
