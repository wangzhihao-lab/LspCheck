struct Outer<T>(T);
struct Inner {
    field: u32
}

fn stuff(Outer(Inn)) {
}
