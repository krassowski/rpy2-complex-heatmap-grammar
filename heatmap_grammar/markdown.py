from dataclasses import dataclass
from typing import Any
from rpy2.robjects.packages import importr
from .r import complex_heatmap


_grid_text_loaded = False


@dataclass
class MarkdownData:
    text: str

    @property
    def wrapper(self) -> Any:
        global _grid_text_loaded
        if not _grid_text_loaded:
            # import gridtext to avoid obtrusive message
            # "Loading required namespace: gridtext"
            # TODO: tell users they need to install it if import fails
            importr('gridtext')
            grid_text_loaded = True
        return complex_heatmap.gt_render(self.text)

    def __str__(self):
        return self.text


def markdown(text: str) -> MarkdownData:
    return MarkdownData(text=text)
