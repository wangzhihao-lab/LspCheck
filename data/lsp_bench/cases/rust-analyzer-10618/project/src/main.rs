use std::rc::Rc;

struct Struct {
    field: String
}

type Data = Rc<Struct>;

fn main() {
    let data = Data {};
}
