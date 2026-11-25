package main

import "fmt"


func (f *Form) SetFocus(index int) *Form {
	if index < 0 {
		f.focusedElement = 0
	} else if index >= len(f.items)+len(f.buttons) {
		f.focusedElement = len(f.items) + len(f.buttons)
	} else {
		f.focusedElement = index
	}
	if f.changed != nil {
		f.changed(f.focusedElement)
	}
	return f
}

type Form struct {
	items          []string
	buttons        []string
	focusedElement int
	changed        func(index int)
}

func main() {
	// Create a new Form instance
	form := &Form{
		items:   []string{"Item 1", "Item 2", "Item 3"},
		buttons: []string{"Submit", "Cancel"},
		changed: func(index int) {
			fmt.Printf("Focused element changed to index: %d\n", index)
		},
	}

	// Set focus to different elements
	form.SetFocus(0)  // Focus on first item
	form.SetFocus(3)  // Focus on first button
	form.SetFocus(5)  // Attempt to focus beyond the last element
	form.SetFocus(-1) // Focus on the first element
}
