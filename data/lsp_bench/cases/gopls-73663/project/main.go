package main

import "fmt"

func main() {
	var s = []string{"a", "b", "c"}
	var i uint32 = 1

	s = append(s[:i], s[i+1:]...)

	fmt.Println(s) // [a c]
}
