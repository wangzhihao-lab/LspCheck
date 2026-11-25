fn called_function() {}

fn higher_order_function(_: impl FnOnce()) {}

fn main() {
    higher_order_function(ca /* cursor */);
}
