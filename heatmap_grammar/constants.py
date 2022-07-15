from typing import Any


class Sentinel:
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return self.name


# TODO: migrate to @dataclass(kw_only=True)?
required: Any = Sentinel('required')
unset: Any = Sentinel('unset')