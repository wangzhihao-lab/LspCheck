const enum E {
	v
}

const enum ES {
	v = "str"
}

const e: E = 0;
const es: ES = "str"; // suggested by the completion service, results in error
