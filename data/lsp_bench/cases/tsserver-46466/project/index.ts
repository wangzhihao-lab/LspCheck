const test = <T>(x: T): string => {
    await new Promise((resolve) => resolve(true))
    return "hello"
}
