package main

import (
	"fmt"
)

// Define an interface
type FruitInfo interface {
	GetName() string
	GetWeight() int
}

// Define a concrete type
type Fruit struct {
	Name   string
	Weight int
}

// Fruit implements the FruitInfo interface
func (f Fruit) GetName() string {
	return f.Name
}

func (f Fruit) GetWeight() int {
	return f.Weight
}

// Simulate a function to get fruits
func GetFruits() []Fruit {
	return []Fruit{
		{Name: "apple", Weight: 100},
		{Name: "banana", Weight: 200},
		{Name: "orange", Weight: 150},
	}
}

func IterateFruits(
	fruits []Fruit,
	cb func(FruitInfo) bool,
) {
	for _, fruit := range fruits {
		if cb(fruit) { // Here it works because Fruit implements the FruitInfo interface
			break
		}
	}
}

func main() {
	// Define a callback function
	cb := func(f FruitInfo) bool {
		fmt.Printf("Processing fruit: Name=%s, Weight=%d grams\n", f.GetName(), f.GetWeight())
		// Stop iterating when a fruit with a weight of 200 grams or more is found
		return f.GetWeight() >= 200
	}

	IterateFruits(GetFruits(), cb)
}
