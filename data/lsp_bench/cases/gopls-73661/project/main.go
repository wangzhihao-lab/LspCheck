package main

import "fmt"

type ssa []string
type ssb []string

var a ssa = ssa{"a", "b", "c"}

func main() {
	var b ssb = append([]string{}, a...)

	fmt.Println(b)
}
