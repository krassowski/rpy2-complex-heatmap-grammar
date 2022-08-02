from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Union
from rpy2.rinterface import NULL
from .constants import unset
from .markdown import MarkdownData
from .rpy2_helpers import r_dict
from .r import base, complex_heatmap, grid
from .utils import isinstance_permissive

def legend_discrete(colors, title: str, **kwargs):
    return complex_heatmap.Legend(
        title=title,
        at=base.names(colors),
        labels=base.names(colors),
        legend_gp=grid.gpar(
            fill=colors
        ),
        **kwargs
    )


def legend_colorbar(col_fun, title: str, **kwargs):
    return complex_heatmap.Legend(
        col_fun=col_fun,
        title=title,
        **kwargs
    )


@dataclass
class Guide:
    title: str | MarkdownData = unset
    label: bool = True
    direction: Literal['horizontal', 'vertical'] = 'vertical'
    border: str = unset
    background: str = unset

    def _shared_arguments(self) -> dict:
        args = {}
        for arg in ['border', 'background', 'direction']:
            value = getattr(self, arg)
            if value is None:
                value = NULL
            if value is not unset:
                args[arg] = value
        return args

    def params(self, title: str, colors=None, color_function=None, **kwargs):
        raise NotImplementedError()

    def legend(self, title: str, colors=None, color_function=None, **kwargs):
        raise NotImplementedError()

    def _title_for_r(self, title: str | MarkdownData):
        title = title if self.title is unset else self.title
        return (
            title.wrapper
            if isinstance_permissive(title, MarkdownData) else
            title
        )


GuideType = Union[Literal['colourbar', 'colorbar', 'legend', 'none', None], Guide]


@dataclass
class guide_none(Guide):

    def params(self, title: str, colors=None, color_function=None, **kwargs):
        return {}

    def legend(self, title: str, colors=None, color_function=None, **kwargs):
        return None


@dataclass
class guide_legend(Guide):
    ncol: int = unset
    nrow: int = unset
    reverse: bool = False
    border: str = 'black'

    def params(self, title: str, colors: dict = None, color_function=None, **kwargs):
        assert colors
        if self.reverse:
            colors = {
                key: colors[key]
                for key in reversed(colors)
            }
        return dict(
            colors=r_dict(colors),
            title=self._title_for_r(title),
            **self._shared_arguments(),
            **kwargs
        )

    def legend(self, *args, **kwargs):
        return legend_discrete(**self.params(*args, **kwargs))


@dataclass
class guide_colourbar(Guide):

    def params(self, title: str, colors=None, color_function=None, **kwargs):
        assert color_function
        return dict(
            col_fun=color_function,
            title=self._title_for_r(title),
            **self._shared_arguments(),
            **kwargs
        )

    def legend(self, *args, **kwargs):
        return legend_colorbar(**self.params(*args, **kwargs))


guide_colorbar = guide_colourbar


class GuidesCollection(dict):
    pass


def guides(**kwargs: dict[str, Guide]):
    return GuidesCollection(**kwargs)


GUIDE_REGISTER = {
    'colourbar': guide_colourbar,
    'colorbar': guide_colorbar,
    'legend': guide_legend,
    'none': guide_none,
    None: guide_none
}