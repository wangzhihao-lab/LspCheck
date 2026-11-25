package bar_test

import (
	"foo.mod/bar"
	"foo.mod/foo"
)

type Mer struct{}
func (Mer) M() {}

func _() {
	_ = bar.Blah
	_ = foo.Foo
}
