from typing import Any


class Sentinel:
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return (
            hasattr(other, 'name')
            and
            (self.name == other.name)
            and
            (
                self.__class__.__name__
                ==
                other.__class__.__name__
            )
        )

    def __repr__(self):
        return self.name


# TODO: migrate to @dataclass(kw_only=True)?
required: Any = Sentinel('required')
unset: Any = Sentinel('unset')