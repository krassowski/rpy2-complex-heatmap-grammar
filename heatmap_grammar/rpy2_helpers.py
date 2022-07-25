from warnings import warn
from rpy2.robjects import pandas2ri, default_converter, conversion
from rpy2.robjects.conversion import localconverter
from rpy2.rinterface import SexpClosure, SexpExtPtr, parse
from rpy2.rinterface_lib.sexp import baseenv
from rpy2.rinterface import LangSexpVector
from collections import defaultdict
from typing import Callable
import inspect
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


def find_first(nodes, of_type):
    candidates = [
        node
        for node in nodes
        if isinstance(node, of_type)
    ]
    return candidates[0]


def rternalize_with_signature(function: Callable) -> SexpClosure:
    """rternalize but preserve function call signature."""
    assert callable(function)
    rpy_fun = SexpExtPtr.from_pyobject(function)

    signature = inspect.signature(function)
    params = defaultdict(list)
    for name, param in signature.parameters.items():
        params[param.kind].append(name)

    # any *args or **kwargs?
    has_var_params = (
        params[inspect.Parameter.VAR_POSITIONAL]
        or params[inspect.Parameter.VAR_KEYWORD]
    )

    params_r_sig = [
        *params[inspect.Parameter.POSITIONAL_ONLY],
        *params[inspect.Parameter.POSITIONAL_OR_KEYWORD],
        *params[inspect.Parameter.KEYWORD_ONLY]
    ]
    if has_var_params:
        params_r_sig.append('...')
    r_func_args = ', '.join(params_r_sig)

    arguments_code = ''

    # always pass positional-only arguments, let Python throw error if missing
    if params[inspect.Parameter.POSITIONAL_ONLY]:
        positionals = ', '.join(params[inspect.Parameter.POSITIONAL_ONLY])
        arguments_code += """
        RPY2_ARGUMENTS <- base::c(RPY2_ARGUMENTS, base::list(%s))
        """ % positionals

    # treat all params which might be default as potentially missing
    # (regardless of whether they are default or not as we cannot
    # reflect the Python signature in R 1-1, so instead let's allow
    # Python itself to raise an exception if user passed wrong args).
    possibly_default = [
        *params[inspect.Parameter.POSITIONAL_OR_KEYWORD],
        *params[inspect.Parameter.KEYWORD_ONLY]
    ]

    for param in possibly_default:
        arguments_code += f"""
        if (!base::missing({param})) {{
            RPY2_ARGUMENTS[['{param}']] <- {param}
        }}
        """

    if has_var_params:
        arguments_code += """
        RPY2_ARGUMENTS <- base::c(
            RPY2_ARGUMENTS,
            ...
        )
        """

    template = parse(f"""
    function({r_func_args}) {{
        RPY2_ARGUMENTS <- base::list(
           ".Python",
           RPY2_FUN_PLACEHOLDER
        )

        {arguments_code}

        do.call(
           .External,
           RPY2_ARGUMENTS
        );
    }}
    """)

    function_definition = find_first(template, of_type=LangSexpVector)
    function_body = find_first(function_definition, of_type=LangSexpVector)

    list_assignment = find_first(function_body, of_type=LangSexpVector)

    args_list = find_first(list_assignment, of_type=LangSexpVector)

    assert str(args_list[2]) == 'RPY2_FUN_PLACEHOLDER'
    args_list[2] = rpy_fun

    res = baseenv['eval'](template)
    res.__nested_sexp__ = rpy_fun.__sexp__
    return res
