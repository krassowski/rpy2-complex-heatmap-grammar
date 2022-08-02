from .annotations import Annotation, ColumnAnnotation, RowAnnotation
from .dendrograms import ColumnDendrogram, RowDendrogram
from .clustering import clustering_distance, inverse_abs_correlation
from .heatmap import Heatmap, HeatmapTheme
from .guides import guide_colorbar, guide_colourbar, guide_legend, guides
from .markdown import markdown
from .plot import Plot, labs
from .scales import (
    scale_identity, scale_gradient, scale_gradient_n, scale_manual,
    scale_color_continuous, scale_fill_continuous,
    scale_color_identity, scale_fill_identity,
    scale_color_gradient, scale_fill_gradient,
    scale_color_gradient2, scale_fill_gradient2,
    scale_color_gradient_n, scale_fill_gradient_n,
    scale_color_manual, scale_fill_manual,
    scale_color_random, scale_fill_random,
    scale_color_brewer, scale_fill_brewer,
)
from .unit import Unit

unit = Unit


# just in case if needs to be expanded
class aes(dict):
    pass


__version__ = '0.0.3'

__all__ = [
    'Plot',
    'Heatmap',
    'HeatmapTheme',
    'ColumnDendrogram',
    'RowDendrogram',
    'Annotation',
    'ColumnAnnotation',
    'RowAnnotation',
    'aes',
    'clustering_distance',
    'inverse_abs_correlation',
    'guide_colorbar',
    'guide_colourbar',
    'guide_legend',
    'guides',
    'markdown',
    'labs',
    'scale_identity',
    'scale_gradient',
    'scale_gradient_n',
    'scale_manual',
    'scale_color_continuous', 'scale_fill_continuous',
    'scale_color_identity', 'scale_fill_identity',
    'scale_color_gradient', 'scale_fill_gradient',
    'scale_color_gradient2', 'scale_fill_gradient2',
    'scale_color_gradient_n', 'scale_fill_gradient_n',
    'scale_color_manual', 'scale_fill_manual',
    'scale_color_random', 'scale_fill_random',
    'scale_color_brewer', 'scale_fill_brewer',
    'unit'
]
