from typing import Union, Literal
from .constants import required

Side = Union[Literal['top', 'bottom', 'left', 'right']]


def isinstance_permissive(obj, cls):
    """isinstance but permissive for IPython reloading where object
    hierarhies may diverge and need to check by name; does not check full mro.
    """
    return isinstance(obj, cls) or any([
        class_.__name__ == cls.__name__
        for class_ in obj.__class__.mro()
    ])


def check_required(obj):
    for k, v in vars(obj).items():
        if v is required:
            raise ValueError(f'Missing required argument: {k}')