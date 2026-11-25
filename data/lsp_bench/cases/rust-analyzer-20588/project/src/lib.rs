unsafe fn f() -> i32 {
    0
}

fn g() -> i32 {
    f() + 1
}

// => unsafe { f() } + 1
