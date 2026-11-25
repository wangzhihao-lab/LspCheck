//go:build go1.25

package tools

import "sync"

func _() {
	var s Server
	s.wg.Add(1)
	go func() {
		print()
		s.wg.Done()
	}()
}

type Server struct {
	wg sync.WaitGroup
}
