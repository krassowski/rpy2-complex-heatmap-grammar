from dataclasses import dataclass
from typing import Any
from .r import complex_heatmap


@dataclass
class GridTextData:
    text: str
    wrapper: Any

    def __str__(self):
        return self.text


def markdown(text: str) -> GridTextData:
    return GridTextData(
        text=text,
        wrapper=complex_heatmap.gt_render(text)
    )