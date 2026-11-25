package tools

import "fmt"

type S struct{ Bytes []byte }

var _ = struct{ A S }{
	A: S{
		Bytes: []byte(
			fmt.Sprintf("%d", 0),
		),
	},
}
