from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from .r import grid


@dataclass
class Unit:
    x: float
    units: Literal[
        'npc',
        'cm',
        'inches',
        'mm',
        'points',
        'picas',
        'bigpts',
        'dida',
        'cicero',
        'scaledpts',
        'lines',
        'char',
        'native',
        'snpc',
        'strwidth',
        'strheight',
        'grobwidth',
        'grobheight'
    ]
    data: str | None = None

    def to_r(self):
        if self.data is not None:
            return grid.unit(float(self.x), self.units, self.data)
        return grid.unit(float(self.x), self.units)
