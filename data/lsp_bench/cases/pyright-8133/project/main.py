import attrs
@attrs.define
class Foo:
    a: bool = attrs.field(default=False, validator=attrs.validators.instance_of(bool))
