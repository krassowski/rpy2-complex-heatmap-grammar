from __future__ import annotations
from abc import abstractmethod
from copy import copy, deepcopy
from dataclasses import dataclass, field
from functools import reduce
from typing import Generic, TypeVar
from warnings import warn

from pandas import DataFrame, Series, concat
from rpy2.robjects.packages import importr
from rpy2.rinterface import rternalize

from .constants import unset
from .markdown import MarkdownData
from .r import complex_heatmap, base
from .utils import isinstance_permissive

_add = base._env['+']
_vertical_concatenate = complex_heatmap._env['%v%']


class Plot:

    def __init__(self):
        self.components: list['PlotComponent'] = []
        self.theme = {
            'heatmap_legend_list': []
        }
        self._size = {}
        self.row_split = None
        self.column_split = None

    def _check_data_integrity(self):
        if len(self.components) < 2:
            return
        first = self.components[0]
        for component in self.components[1:]:
            if len(first.rows) != len(component.rows):
                raise ValueError(
                    'Rows number out of agreement between components'
                    f' {first.rows} and {component.rows}'
                )
            if not all(first.rows == component.rows):
                raise ValueError(
                    'Rows out of agreement between components'
                    f' {first.rows} and {component.rows}'
                )

    def __add__(self, other):
        if other is None:
            return self
        result = copy(self)
        result.theme = deepcopy(result.theme)

        if isinstance_permissive(other, Theme):
            result.theme.update(other.__dict__)
        elif not isinstance_permissive(other, PlotComponent):
            result.components[-1] += other
        else:
            if (
                hasattr(other, 'mapping')
                and other.mapping
                and 'split' in other.mapping
            ):
                split = other.extract_values('split')
                name = f'{other.which}_split'
                existing = getattr(result, name)
                if existing is not None:
                    assert all(existing == split)
                setattr(result, name, base.c(*split))
            other.attach(result)
            result.components.append(other)
        result._check_data_integrity()
        return result

    def __truediv__(self, other):
        result = copy(self)
        assert result.components
        last_component = result.components[-1]
        if not isinstance(last_component, VerticalGroup):
            last_component = VerticalGroup(members=[last_component])
        other.attach(self)
        last_component.members.append(other)
        result.components[-1] = last_component
        result._check_data_integrity()
        return result

    def size(self, w=None, h=None, r=None):
        result = copy(self)
        result._size.update({
            k: v
            for k, v in {
                'width': w,
                'height': h,
                'r': r
            }.items()
            if v is not None
        })
        return result

    def plot(self):
        if not self.components:
            return

        component_plots = [
            c.create(self)
            for c in self.components
        ]

        plot = reduce(_add, component_plots[1:], component_plots[0])

        theme = deepcopy(self.theme)

        legends = theme['heatmap_legend_list']
        for c in self.components:
            if hasattr(c, 'legends'):
                for legend in c.legends:
                    if legend not in legends:
                        legends.append(legend)

        for key in ['row_split', 'column_split']:
            value = getattr(self, key)
            if value is not None:
                theme[key] = value

        ht_list = complex_heatmap.draw(
            plot,
            **{
                k: (
                    v.wrapper
                    if isinstance_permissive(v, MarkdownData) else
                    v
                )
                for k, v in theme.items()
                if v is not unset
            }
        )

        self.decorate(ht_list)

        return ht_list

    def decorate(self, ht_list):
        for component in self.components:
            if hasattr(component, 'decorate'):
                component.decorate(ht_list)

    def interact(self):
        interactive_complex_heatmap = importr('InteractiveComplexHeatmap')
        plot = self.plot()
        interactive_plot = interactive_complex_heatmap.ht_shiny(plot)
        base.print(interactive_plot)

    def _repr_html_(self):
        from rpy2.ipython.rmagic import RMagics
        from IPython import get_ipython

        try:
            plot = self.plot()

            args = ' '.join([f'--{k} {v}' for k, v in self._size.items()])

            @rternalize
            def decorate():
                self.decorate(plot)
                return plot

            RMagics(get_ipython()).R(
                line=f'-i plot -i decorate {args}',
                cell='print(plot)\nsink = decorate()',
                local_ns={'plot': plot, 'decorate': decorate}
            )
        except Exception as e:
            warn(
                'Errors in plotting encountered: '
                'call `._repr_html_()` method  for details'
            )
            raise e

        return ''


PlotType = TypeVar('PlotType', bound=Plot)


class PlotComponent(Generic[PlotType]):

    def attach(self, plot: PlotType):
        self.plot = plot

    @abstractmethod
    def create(self, plot: PlotType):
        pass

    @property
    @abstractmethod
    def rows(self) -> Series:
        raise ValueError(f'Not implemented for {self}')

    def __truediv__(self, other):
        result = copy(self)
        if not isinstance(result, VerticalGroup):
            result = VerticalGroup(members=[result])
        result.members.append(other)
        return result

    def _check_axes(self, data: DataFrame):
        for axis_name in ['index', 'columns']:
            axis = getattr(data, axis_name)
            assert not axis.isna().any()
            assert len(set(axis)) == len(axis)


@dataclass
class VerticalGroup(PlotComponent):
    members: list[PlotComponent] = field(default_factory=list)

    def create(self, *args, **kwargs):
        component_plots = [
            c.create(*args, **kwargs)
            for c in self.members
        ]
        return reduce(
            _vertical_concatenate,
            component_plots[1:],
            component_plots[0]
        )

    @property
    def rows(self) -> Series:
        return concat(
            member.rows
            for member in self.members
        )

    def __add__(self, component: PlotComponent):
        # TODO
        raise


@dataclass
class Theme:
    pass


@dataclass
class labs(Theme):
    column_title: str | MarkdownData = unset