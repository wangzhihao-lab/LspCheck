function identity<T>(self: T) {
 
  // To reproduce the bug, Quick Fix > Add missing function declaration
  runEvilSideEffect(self)

  return self;
}
