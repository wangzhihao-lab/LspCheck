package main

func check() bool {
	nums := []int{1, 2, 3}
	for _, num := range nums {
		if isEven(num) {
			return true
		}
	}
	return false
}

func isEven(num int, opt ...any) bool {
	return num/2 == 0
}
