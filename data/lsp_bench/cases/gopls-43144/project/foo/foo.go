package foo

import "foo.mod/bar"

const Foo = 42

type T int
type Interface interface{ M() }

func _() {
	_ = bar.Blah
}
