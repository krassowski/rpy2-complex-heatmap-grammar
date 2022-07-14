from warnings import warn
from rpy2.robjects import pandas2ri, default_converter, conversion
from rpy2.robjects.conversion import localconverter
from .r import base


def r_dict(p_dict: dict, value_type: type = None):
    if value_type is not None:
        p_dict = {
            k: value_type(v)
            for k, v in p_dict.items()
        }
    else:
        types = {type(v) for v in p_dict.values()}
        if len(types) > 1:
            warn(
                f'The values of Python dict include multiple types: {types}'
                ' which may result in an R vector of a type other than expected;'
                ' pass `value_type` to coerce the values to the given type.'
            )
    return base.c(**{
        str(k): v
        for k, v in p_dict.items()
    })


def rpy2py(x):
    with localconverter(default_converter + pandas2ri.converter):
        return conversion.rpy2py(x)


def py2rpy(x):
    with localconverter(default_converter + pandas2ri.converter):
        return conversion.py2rpy(x)