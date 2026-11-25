export function uppercaseAll(stringsPromise: Promise<string[]>) {
  return stringsPromise.then(function* (strings) {
    for (const string of strings) {
      yield string.toUpperCase();
    }
  });
}
