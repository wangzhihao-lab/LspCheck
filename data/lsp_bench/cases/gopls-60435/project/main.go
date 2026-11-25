package main

import (
	"net/http"
	"net/http/httptest"
)

func main() {
	http.CanonicalHeaderKey("")
	httptest.NewRecorder()
}
