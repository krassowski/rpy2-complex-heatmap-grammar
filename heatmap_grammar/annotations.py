from __future__ import annotations
from copy import copy
from dataclasses import dataclass, field
from typing import (
    Callable, Literal,
    Optional, Union, List
)
from warnings import warn

from pandas import DataFrame, Series
from pandas.api.types import is_numeric_dtype

from .constants import unset
from .r import (
    complex_heatmap,
    base,
    grid
)
from .markdown import MarkdownData
from .plot import Plot, PlotComponent
from .scales import Scale, scale_fill_gradient, scale_identity, scale_fill_random
from .guides import GuidesCollection
from .unit import Unit
from .utils import isinstance_permissive

ComplexHeatmapGeom = Literal[
    'simple',
    'barplot', 'block', 'lines', 'boxplot', 'histogram', 'density',
    'joyplot', 'horizon', 'text', 'mark', 'zoom'
]


@dataclass
class Annotation:
    geom: Callable | ComplexHeatmapGeom = 'simple'
    mapping: Optional[dict] = None
    data: DataFrame | None = field(default=None, repr=False)
    label: str | MarkdownData = None
    height: Unit | None = None
    width: Unit | None = None
    label_rotation: Literal[0, 90, 180, 270] = 0
    label_side: Literal['right', 'left', 'top', 'bottom', 'auto'] = 'auto'
    label_size: float = 5
    geom_arguments: dict = field(default_factory=dict)
    gp_arguments: dict = field(default_factory=dict)
    active_scales: list = field(default_factory=list, init=False)
    scales: dict[str, Scale] = field(default_factory=dict, init=False)

    def _default_scale(self, data: Series, aesthetic: str):
        defaults_by_dtype = {
            'numeric': scale_fill_gradient(low='white', high='red'),
            'discrete': scale_fill_random()
        }
        if aesthetic in ['fill', 'color']:
            kind = 'numeric' if is_numeric_dtype(data.dtype) else 'discrete'
            return defaults_by_dtype[kind]

        return scale_identity()

    @property
    def name(self) -> str | MarkdownData:
        return self.label or self.mapping.get('value', next(iter(self.mapping.values())))

    @property
    def name_object(self):
        return (
            self.label.wrapper
            if isinstance_permissive(self.label, MarkdownData) else
            str(self.name)
        )

    def create(self, annotation_group: 'AnnotationGroup'):
        geom = (
            getattr(complex_heatmap, 'anno_' + self.geom)
            if isinstance(self.geom, str) else
            self.geom
        )
        mapping = copy(self.mapping)
        if 'value' not in mapping and len(mapping) == 1:
            mapping['value'] = next(iter(mapping.values()))

        mapped_dataset = annotation_group.combine(
            data=self.data,
            mapping=mapping
        )

        value = mapped_dataset.extract('value')

        if self.geom == 'mark':
            value = (
                value
                .to_frame('value')
                .assign(number=range(1, len(value) + 1))
                .where(value)
                .dropna()
                ['number']
            )

        gp_mapping = self.gp_arguments.copy()
        gp_mp = {
            'fill': 'fill',
            'color': 'col'
        }
        graphical_map = {
            'label': 'pch',
            'color': 'col',
        }
        if self.geom == 'mark':
            graphical_map = {
                'label': 'labels'
            }

        scales = self.scales.copy()

        graphical_params = {}
        self.active_scales = []

        for map_key in mapped_dataset.mapping:
            if map_key == 'value' or map_key == 'split':
                continue
            values = mapped_dataset.extract(map_key).loc[value.index]

            if map_key in scales:
                scale = scales[map_key]
            else:
                scale = self._default_scale(values, map_key)

            scale.fit(values, self.name)
            if scale not in self.active_scales:
                self.active_scales.append(scale)

            matched = False
            if self.geom == 'simple' or self.geom == 'mark':
                if map_key in graphical_map:
                    graphical_key = graphical_map[map_key]
                    graphical_params[graphical_key] = scale.compute(values)
                    matched = True
            else:
                if map_key in gp_mp:
                    gp_key = gp_mp[map_key]
                    gp_mapping[gp_key] = scale.compute(values)
                    matched = True
            if not matched:
                raise ValueError(f'Unknown aestethic: {map_key}')

        if gp_mapping:
            graphical_params['gp'] = grid.gpar(**gp_mapping)

        if annotation_group.which == 'column' and self.height is not None:
            graphical_params['height'] = self.height.to_r()
        if annotation_group.which == 'row' and self.width is not None:
            graphical_params['width'] = self.width.to_r()

        return geom(
            # note: to_list() converts to native type such as float instead of np.float64
            base.c(*value.to_list()),
            which=annotation_group.which,
            **graphical_params,
            **self.geom_arguments,
        )

    def __add__(self, other):
        result = copy(self)
        result.scales = copy(result.scales)
        if isinstance_permissive(other, GuidesCollection):
            # + guides()
            for k, v in other.items():
                result.scales[k].guide = v
        else:
            result.scales[other.aesthetic] = other
        return result


@dataclass
class MappedDataset:
    data: DataFrame
    mapping: dict

    @property
    def index(self):
        return self.data.index

    def extract(self, variable: str):
        return self.data[self.mapping[variable]]


@dataclass
class AnnotationGroup(PlotComponent):
    data: Optional[DataFrame] = field(default=None, repr=False)
    mapping: Optional[dict] = None
    layers: list[Annotation] = field(default_factory=list)
    default_label_side: str = 'abstract'   # TODO
    which: str = 'abstract'
    gap: Unit | None = None
    height: Unit | None = None
    width: Unit | None = None
    allow_missing: bool = False

    @property
    def legends(self) -> list:
        return [
            scale.legend
            for layer in self.layers
            for scale in layer.active_scales
            if scale.legend is not None
        ]

    def set_data(self, data: DataFrame):
        new = copy(self)
        new.data = data
        return new

    def constructor(self, *args, **kwargs):
        raise NotImplementedError()

    @property
    def rows(self) -> Series:
        return self.combine().index

    def combine(self, data: DataFrame = None, mapping: dict = None):
        """Create value extractor which can extract data and values from:

        - combined mapping of annotation group and annotation (if provided)
        - annotation group data or provided group data
        """
        if data is None:
            data = self.data

        data = data.sort_index()
        self._check_axes(data)

        combined_mapping: dict = {}
        if self.mapping:
            combined_mapping = copy(self.mapping)
        if mapping:
            combined_mapping.update(mapping)

        return MappedDataset(
            data=data,
            mapping=combined_mapping
        )

    def extract_values(self, variable: str):
        """Extract values from annotation group data and mapping."""
        dataset = self.combine()
        return dataset.extract(variable)

    def create(self, plot: Plot):

        annotations = {
            str(layer.name): layer.create(self)
            for layer in self.layers
        }
        kwargs = {}
        for key in ['gap', 'width', 'height']:
            value = getattr(self, key)
            if value is not None:
                kwargs[key] = value.to_r()
        if len(self.layers) == 0:
            warn('Empty annotation')
        return self.constructor(
            **annotations,
            annotation_name_gp=grid.gpar(fontsize=base.c(*[
                layer.label_size
                for layer in self.layers
            ])),
            show_legend=True,
            #simple_anno_size_adjust=True,
            # TODO
            annotation_name_rot=base.c(*[
                layer.label_rotation
                for layer in self.layers
            ]),
            annotation_name_side=base.c(*[
                (
                    self.default_label_side
                    if layer.label_side == 'auto'
                    else layer.label_side
                )
                for layer in self.layers
            ]),
            annotation_label=base.list(**{
                str(layer.name): layer.name_object
                for layer in self.layers
            }),
            **kwargs
            #annotation_legend_param=self.legends
        )

    def __add__(self, annotation: Union[Annotation, List[Annotation]]):
        result = copy(self)
        result.layers = copy(result.layers)

        if annotation is None:
            annotations = []
        elif not isinstance(annotation, list):
            annotations = [annotation]
        else:
            annotations = annotation

        for annotation in annotations:
            if (
                isinstance_permissive(annotation, dict)
                and not isinstance_permissive(annotation, GuidesCollection)
            ):
                result.mapping = copy(result.mapping)
                if result.mapping is None:
                    result.mapping = {}
                result.mapping.update(annotation)
            elif not isinstance_permissive(annotation, Annotation):
                result.layers[-1] += annotation
            else:
                result.layers.append(annotation)
        return result

    def check_no_none(self, kwargs):
        for k, v in kwargs.items():
            if v is None or v is unset:
                raise ValueError(f'{k} is None or unset in R call')


@dataclass
class ColumnAnnotation(AnnotationGroup):
    which: str = 'column'
    default_label_side: str = 'right'

    def constructor(self, *args, **kwargs):
        self.check_no_none(kwargs)
        return complex_heatmap.columnAnnotation(*args, **kwargs)


@dataclass
class RowAnnotation(AnnotationGroup):
    which: str = 'row'
    default_label_side: str = 'top'

    def constructor(self, *args, **kwargs):
        self.check_no_none(kwargs)
        return complex_heatmap.rowAnnotation(*args, **kwargs)