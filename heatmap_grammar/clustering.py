from typing import Callable
from inspect import signature
from pandas import DataFrame
from rpy2.rinterface import rternalize

from .rpy2_helpers import py2rpy, rpy2py
from .r import base, stats


def clustering_distance(func: Callable[[DataFrame], DataFrame]):
    expected_params = [
        param
        for param in signature(func).parameters.values()
        if param.default is param.empty
    ]
    if len(expected_params) > 2:
        raise ValueError(
            f'Cannot create clustering distance for {func}:'
            ' as it expects more than two arguments.'
        )
    if len(expected_params) == 0:
        raise ValueError(
            f'Cannot create clustering distance for {func}:'
            ' as it does not take any arguments.'
        )
    if len(expected_params) == 1:
        @rternalize
        def wrapper(r_data_matrix):
            py_data_df = rpy2py(base.as_data_frame(r_data_matrix)).T
            py_distance_df = func(py_data_df)
            return stats.as_dist(py2rpy(py_distance_df))
    else:
        raise ValueError('Two-parameter functions not currently supported')
        # TODO: figure out a way for rpy2 to properly
        # translate signature so that proper dispatch happens in R
        assert len(expected_params) == 2

        @rternalize
        def wrapper(x, y):
            py_x = rpy2py(x)
            py_y = rpy2py(y)
            py_distance = func(py_x, py_y)
            return float(py_distance)

    return wrapper


@clustering_distance
def inverse_abs_correlation(data: DataFrame):
    corr = data.corr()
    corr = corr.loc[data.columns, data.columns]
    abs_corr = corr.abs().fillna(0)
    return 1 - abs_corr
