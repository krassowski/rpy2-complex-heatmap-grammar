from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Literal

from rpy2.robjects import local_context, rl

from .r import base, complex_heatmap
from .unit import Unit
from .utils import Side
from .constants import unset
from .rpy2_helpers import rpy2py


@dataclass
class Dendrogram:
    show: bool = True
    side: Side = unset
    reorder: bool = unset
    axis: str = ''
    decorate: Callable | None = None

    def params(self):
        axis = self.axis
        return {
            f'show_{axis}_dend': self.show,
            f'{axis}_dend_side': self.side,
            f'{axis}_dend_reorder': self.reorder
        }

    def _get_dend(self, ht_list, name: str):
        getter = getattr(complex_heatmap, f'{self.axis}_dend')
        denrograms = getter(ht_list)
        n = rpy2py(base.length(ht_list))

        if n == 1:
            return denrograms
        return denrograms.rx2(name)

    def apply_decoration(self, ht_list, name: str):
        if not self.decorate:
            return
        tree = self._get_dend(ht_list, name)
        decorator = getattr(complex_heatmap, f'decorate_{self.axis}_dend')

        with local_context() as lc:
            lc['decorate'] = self.decorate
            lc['tree'] = tree
            decorator(name, rl('decorate(tree)'))


@dataclass
class RowDendrogram(Dendrogram):
    axis: str = 'row'
    side: Literal['left', 'right'] = unset
    width: Unit = Unit(1, 'cm')


@dataclass
class ColumnDendrogram(Dendrogram):
    axis: str = 'column'
    side: Literal['top', 'bottom'] = unset
    height: Unit = Unit(1, 'cm')

    def params(self):
        axis = self.axis
        return {
            **super().params(),
            f'{axis}_dend_height': self.height,
        }