foo = None
bar = False
for _ in []:
    if not bar:
        continue
    if foo:
        reveal_type(foo) # reveal_type says int, vscode says Never
    baz = int(foo)
    foo = baz
    baz.asdf()
