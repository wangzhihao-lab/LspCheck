from typing import Literal

a: Literal[
    "a\nb"
] = """a
b"""

print(repr(a))
