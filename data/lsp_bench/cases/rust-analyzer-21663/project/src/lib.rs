#![feature(allocator_api)]
use std::alloc::Allocator;
struct Foo;
unsafe impl Allocator for Foo {}
