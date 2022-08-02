from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Union, Iterable
from warnings import warn

from numpy import linspace
from pandas import Series
from rpy2.robjects.packages import importr

from .guides import Guide, GuideType, GUIDE_REGISTER
from .markdown import MarkdownData
from .constants import required, unset
from .r import base, stats, circlize
from .rpy2_helpers import rpy2py
from .utils import isinstance_permissive, check_required


CirclizeColorspace = Literal['RGB', 'HSV', 'HLS', 'XYZ', 'sRGB', 'LUV', 'LAB']

Limits = Union[List[float], Literal[None]]
Aesthetics = Literal['fill', 'color', 'shape']


@dataclass
class Scale:
    aesthetic: Aesthetics = required
    guide: GuideType = None
    name: str | MarkdownData = unset
    na_value: str = 'grey50'
    _fitted: bool = field(default=False, init=False)

    def __post_init__(self):
        check_required(self)

    def fit(self, data: Series, name: str | MarkdownData):
        if self.name is unset:
            self.name = name
        assert isinstance(self.name, str) or isinstance_permissive(self.name, MarkdownData)
        self._fitted = True
        self._guide_params = self._prepare_params()

    @property
    def legend(self):
        guide = self._solve_guide()
        return guide.legend(**self._guide_params)

    @property
    def params(self):
        guide = self._solve_guide()
        return guide.params(**self._guide_params)

    def compute(self, data: Series):
        raise NotImplementedError()

    def _prepare_params(self) -> dict:
        raise NotImplementedError()

    def _check_fited(self):
        if not self._fitted:
            raise ValueError('Scale was not fitted, call .fit(data, name) first!')

    def _solve_guide(self) -> Guide:
        if isinstance(self.guide, str) or self.guide is None:
            guide = GUIDE_REGISTER[self.guide]()
        else:
            guide = self.guide
        return guide

    @property
    def heatmap_col(self):
        """Whatever is needed to pass to Heatmap() in the `col` parameter.

        Can be ignored if a scale cannot be used for heatmap."""
        raise NotImplementedError()


@dataclass
class scale_identity(Scale):
    aesthetic: Aesthetics = 'any'

    def compute(self, data: Series):
        return stats.setNames(
            base.c(*data.apply(str).to_list()),
            base.c(*data.to_list())
        )

    def _prepare_params(self):
        return {}

    @property
    def legend(self):
        return None


@dataclass
class scale_manual(Scale):
    guide: GuideType = 'legend'
    values: Dict[Any, str] = required
    limits: Limits = None

    def _prepare_params(self):
        return dict(
            colors=self.values,
            title=self.name
        )

    def compute(self, data: Series):
        self._check_fited()
        return stats.setNames(
            base.c(*data.map(self.values).to_list()),
            base.c(*data.to_list())
        )

    @property
    def heatmap_col(self):
        return base.structure(
            list(self.values.values()), names=list(self.values.keys())
        )


@dataclass
class scale_random(scale_manual):
    guide: GuideType = 'legend'
    values: Dict[Any, str] = field(default_factory=dict, init=False)
    limits: Limits = None
    luminosity: Literal['bright', 'light', 'dark', 'random'] = 'random'
    transparency: float = 0
    hue: str = unset

    def fit(self, data: Series, name: str | MarkdownData):
        values = data.unique()
        colors = rpy2py(circlize.rand_color(
            n=len(values),
            luminosity=self.luminosity,
            transparency=float(self.transparency),
            **(
                {}
                if self.hue is unset
                else {'hue': self.hue}
            )
        ))
        self.values = dict(zip(values, colors))
        super().fit(data, name)


@dataclass
class scale_brewer(scale_manual):
    guide: GuideType = 'legend'
    values: Dict[Any, str] = field(default_factory=dict, init=False)
    limits: Limits = None
    palette: str = 'Set1'

    def fit(self, data: Series, name: str | MarkdownData):
        brewer = importr('RColorBrewer')

        values = data.unique()
        colors = rpy2py(brewer.brewer_pal(
            n=len(values),
            name=self.palette
        ))
        self.values = dict(zip(values, colors))
        super().fit(data, name)


@dataclass
class scale_gradient_n(Scale):
    guide: GuideType = 'colourbar'
    colors: list[str] | Iterable[str] = required
    space: CirclizeColorspace = 'LAB'
    limits: Limits = None
    # n points deciding where to place provided n colours
    points: list[float] = unset
    breaks: list[float] = unset
    quantiles: list[float] = field(default_factory=lambda: [0, 1])
    symmetrical: bool = False
    color_ramp_kwargs: dict = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.colors = list(self.colors)

    def fit_points(self, limits):
        return linspace(
            limits[0],
            limits[1],
            len(self.colors)
        )

    def fit(self, data: Series, name: str | MarkdownData):
        if self.limits is None:
            assert self.quantiles[0] <= self.quantiles[1]
            limits = [
                data.quantile(self.quantiles[0]),
                data.quantile(self.quantiles[1])
            ]
            if self.symmetrical:
                if limits[0] > 0 or limits[1] < 0:
                    warn('Symmetrical gradient requested, but interval does not include zero')
                larger = max([abs(lim) for lim in limits])
                limits = [
                    -larger,
                    larger
                ]
        else:
            limits = self.limits
            assert not self.symmetrical
        limits = [float(x) for x in limits]
        if self.points is unset:
            self.fitted_points = [
                float(x)
                for x in self.fit_points(limits)
            ]
        else:
            self.fitted_points = self.points
        super().fit(data, name)

    def _prepare_params(self):
        params = dict(
            color_function=self._color_function,
            title=self.name,
            colors=dict(zip(
                self.fitted_points,
                self.colors
            ))
        )
        if self.breaks is not unset:
            params['at'] = base.c(
                *[float(x) for x in self.breaks]
            )
        return params

    @property
    def _color_function(self):
        self._check_fited()
        assert self.colors is not required
        return circlize.colorRamp2(
            breaks=base.c(*self.fitted_points),
            colors=base.c(*self.colors),
            space=self.space,
            **self.color_ramp_kwargs
        )

    def compute(self, data: Series):
        self._check_fited()
        return stats.setNames(
            self._color_function(base.c(*data.to_list())),
            base.c(*data.to_list())
        )

    @property
    def heatmap_col(self):
        return self._color_function


@dataclass
class scale_gradient2(scale_gradient_n):
    low: str = 'blue'
    mid: str = 'white'
    high: str = 'red'
    midpoint: float = unset

    def fit_points(self, limits):
        if self.midpoint is unset:
            return super().fit_points(limits)
        return [
            limits[0],
            self.midpoint,
            limits[1]
        ]

    @property
    def colors(self):
        return [self.low, self.mid, self.high]

    @colors.setter
    def colors(self, colors):
        return


@dataclass
class scale_gradient(scale_gradient_n):
    low: str = 'blue'
    high: str = 'red'

    @property
    def colors(self):
        return [self.low, self.high]

    @colors.setter
    def colors(self, colors):
        return


@dataclass
class scale_fill_gradient2(scale_gradient2):
    aesthetic: Aesthetics = 'fill'


@dataclass
class scale_color_gradient2(scale_gradient2):
    aesthetic: Aesthetics = 'color'


@dataclass
class scale_fill_gradient(scale_gradient):
    aesthetic: Aesthetics = 'fill'


@dataclass
class scale_color_gradient(scale_gradient):
    aesthetic: Aesthetics = 'color'


@dataclass
class scale_fill_gradient_n(scale_gradient_n):
    aesthetic: Aesthetics = 'fill'


@dataclass
class scale_color_gradient_n(scale_gradient_n):
    aesthetic: Aesthetics = 'color'


@dataclass
class scale_fill_identity(scale_identity):
    aesthetic: Aesthetics = 'fill'


@dataclass
class scale_color_identity(scale_identity):
    aesthetic: Aesthetics = 'color'


@dataclass
class scale_color_manual(scale_manual):
    aesthetic: Aesthetics = 'color'


@dataclass
class scale_fill_manual(scale_manual):
    aesthetic: Aesthetics = 'fill'


@dataclass
class scale_fill_random(scale_random):
    aesthetic: Aesthetics = 'fill'


@dataclass
class scale_color_random(scale_random):
    aesthetic: Aesthetics = 'color'


@dataclass
class scale_fill_brewer(scale_brewer):
    aesthetic: Aesthetics = 'fill'


@dataclass
class scale_color_brewer(scale_brewer):
    aesthetic: Aesthetics = 'color'


scale_color_continuous = scale_color_gradient
scale_fill_continuous = scale_fill_gradient