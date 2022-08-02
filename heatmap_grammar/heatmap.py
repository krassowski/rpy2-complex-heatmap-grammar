from __future__ import annotations
from copy import copy
from dataclasses import dataclass, field
from typing import (
    Any, Callable,
    Optional, Union, Iterable
)


from pandas.api.types import is_numeric_dtype
from pandas import DataFrame, Series
from rpy2.rinterface import NULL

from .annotations import ColumnAnnotation
from .constants import unset, required
from .dendrograms import Dendrogram, RowDendrogram, ColumnDendrogram
from .plot import Plot, PlotComponent, Theme
from .rpy2_helpers import py2rpy
from .r import (
    complex_heatmap,
    base,
    grid
)
from .scales import Scale, scale_fill_gradient_n, scale_fill_random
from .utils import Side, isinstance_permissive
from .guides import guide_colorbar, GuidesCollection
from .unit import Unit


@dataclass
class HeatmapTheme(Theme):
    heatmap_legend_side: Side = 'right'
    annotation_legend_side: Side = 'right'
    annotation_legend_list: list = field(default_factory=list)
    merge_legend: bool = True
    main_heatmap: str = unset
    row_km: int = unset
    column_km: int = unset


def vector_or_null(data: Union[None, Iterable]):
    return base.c(*data) if data is not None else NULL


def default_heatmap_scales(dtypes):
    if len(dtypes) != 1:
        return {}
    dtype = dtypes[0]
    if is_numeric_dtype(dtype):
        return {
            'fill': scale_fill_gradient_n(
                colors=['blue', 'white', 'red'],
                guide=guide_colorbar(direction='vertical')
            )
        }
    else:
        return {
            'fill': scale_fill_random()
        }


def default_dendrograms():
    return {
        'row': RowDendrogram(),
        'column': ColumnDendrogram()
    }


def new_heatmap_id(i=[0]):
    i[0] += 1
    return f'heatmap{i[0]}'


@dataclass
class Heatmap(PlotComponent):
    data: DataFrame | Series = field(default=required, repr=False)
    weight: Optional[Callable[[DataFrame], Series]] = None
    border: bool | str = False
    top_annotation: 'ColumnAnnotation' | None = None
    height: Unit = unset
    width: Unit = unset
    row_gap: Unit = unset
    column_gap: Unit = unset
    title: str = ''
    name: str = field(default_factory=new_heatmap_id)
    cluster_rows: bool = unset
    cluster_columns: bool = unset
    show_row_names: bool = unset
    show_column_names: bool = unset
    clustering_distance_columns: str = "euclidean"
    clustering_method_columns: str = "complete"
    clustering_distance_rows: str = "euclidean"
    clustering_method_rows: str = "complete"
    row_names: Any = grid.gpar(fontsize=8)
    column_title: Any = grid.gpar()
    column_labels: Iterable | dict = unset
    column_order: list = unset
    row_order: list = unset
    row_labels: Iterable | dict = unset
    layer_fun: Callable = unset
    scales: dict[str, Scale] = field(default_factory=dict, init=False)
    dendrograms: dict[str, Dendrogram] = field(default_factory=default_dendrograms, init=False)
    manage_heatmap_legend: bool = True

    def __post_init__(self):
        assert self.data is not required
        if isinstance(self.data, Series):
            self.data = self.data.to_frame()

        dtypes = list(set(self.data.dtypes))

        self.scales = default_heatmap_scales(dtypes)

        order_mapper = {'column_order': 'columns', 'row_order': 'index'}
        for attr, axis in order_mapper.items():
            value = getattr(self, attr)
            if value is not unset:
                order = Series([*value])
                if is_numeric_dtype(order):
                    order = order - 1
                    column_order = base.c(*getattr(self.data, axis)[order])
                    setattr(self, attr, base.c(*column_order))

        self.data = self.data.sort_index(axis=0).sort_index(axis=1)
        self._check_axes(self.data)

    @property
    def legends(self):
        try:
            return [
                *(
                    [
                        scale.legend
                        for scale in self.scales.values()
                        if scale.legend is not None
                    ]
                    if self.manage_heatmap_legend else
                    []
                ),
                *(
                    self.top_annotation.legends
                    if self.top_annotation else
                    []
                )
            ]
        except AttributeError as e:
            raise ValueError(e)

    def heatmap(self, plot: Plot, data: DataFrame, *args, **kwargs):
        if hasattr(plot, 'row_order'):
            kwargs['row_order'] = base.c(*plot.row_order)
        if_not_none = ['column_split', 'row_split']

        for argument in if_not_none:
            value = getattr(plot, argument)
            if value is not None:
                kwargs[argument] = value

        for dendrogram in self.dendrograms.values():
            kwargs.update(dendrogram.params())

        if_not_unset_self = [
            'row_labels', 'column_labels',
            'height', 'width',
            'row_gap', 'column_gap',
            'column_order', 'row_order',
            'show_row_names', 'show_column_names',
            'cluster_rows', 'cluster_columns',
            'layer_fun'
        ]

        for argument in if_not_unset_self:
            value = getattr(self, argument)
            if value is not unset:
                kwargs[argument] = value

        for key, value in kwargs.items():
            # convert Unit and others as needed
            if hasattr(value, 'to_r'):
                kwargs[key] = value.to_r()

        map_axes = {
            'row_labels': 'index',
            'column_labels': 'columns'
        }
        for argument, axis in map_axes.items():
            if argument in kwargs and isinstance(kwargs[argument], dict):
                kwargs[argument] = getattr(data, axis).map(kwargs[argument]).to_series()

        fill_scale = self.scales['fill']
        kwargs['col'] = fill_scale.heatmap_col

        if kwargs.get('top_annotation', None) is None:
            top_annotation = self.top_annotation
            if top_annotation is not None:
                kwargs['top_annotation'] = top_annotation.create(plot)

                extra = set(top_annotation.rows) - set(self.columns)
                missing = set(self.columns) - set(top_annotation.rows)
                if missing and not top_annotation.allow_missing:
                    raise ValueError(f'Missing top annotation for: {missing}')
                if extra:
                    raise ValueError(f'Unused top annotation for: {extra}')
                assert list(top_annotation.rows) == list(self.columns)

                if top_annotation.mapping and 'split' in top_annotation.mapping:
                    kwargs['column_split'] = top_annotation.extract_values('split')
            else:
                kwargs['top_annotation'] = NULL

        coerce_to_list = ['column_split', 'row_split', 'row_labels', 'column_labels']
        for key in coerce_to_list:
            if key in kwargs and isinstance_permissive(kwargs[key], Series):
                kwargs[key] = base.c(*kwargs[key])

        kwargs = {
            k: v
            for k, v in kwargs.items()
            if v is not unset
        }

        return complex_heatmap.Heatmap(
            py2rpy(data),
            *args,
            name=self.name,
            border=self.border,
            na_col=fill_scale.na_value,
            clustering_distance_columns=self.clustering_distance_columns,
            clustering_method_columns=self.clustering_method_columns,
            clustering_distance_rows=self.clustering_distance_rows,
            clustering_method_rows=self.clustering_method_rows,
            row_names_gp=self.row_names,
            column_title_gp=self.column_title,
            show_heatmap_legend=False if self.manage_heatmap_legend else True,
            **kwargs
        )

    @property
    def rows(self):
        return self.data.index

    @property
    def columns(self):
        return self.data.columns

    def create(self, plot: Plot):
        molecule_abundance = self.data
        if self.weight:
            weights = self.weight(molecule_abundance)

            molecule_abundance = molecule_abundance.apply(
                lambda a: a.multiply(weights.reindex(molecule_abundance.index).fillna(1))
            )

        # order is maintained between annotation and matrix by sorting the columns (patients)
        molecule_abundance = molecule_abundance[sorted(molecule_abundance.columns)]
        fill_scale = self.scales['fill']
        fill_scale.fit(molecule_abundance.stack(), 'Heatmap')

        return self.heatmap(
            plot,
            molecule_abundance,
            column_title=self.title,
            row_title=NULL,
            heatmap_legend_param=base.list(**fill_scale.params)
        )

    def decorate(self, ht_list):
        for dendrogram in self.dendrograms.values():
            dendrogram.apply_decoration(ht_list, self.name)

    def __add__(self, other):
        result = copy(self)
        result.scales = copy(result.scales)
        if isinstance_permissive(other, Scale):
            result.scales[other.aesthetic] = other
        elif isinstance_permissive(other, GuidesCollection):
            # + guides()
            for k, v in other.items():
                result.scales[k].guide = v
        elif isinstance_permissive(other, Dendrogram):
            result.dendrograms[other.axis] = other
        return result

    def _repr_html_(self):
        return (Plot() + self)._repr_html_()