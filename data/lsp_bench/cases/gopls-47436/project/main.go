package p

import "embed"

const (
	Hello = "world"
)

//go:embed main.go *.txt
var myFS embed.FS
