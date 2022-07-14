from .annotations import Annotation, ColumnAnnotation, RowAnnotation
from .clustering import clustering_distance, inverse_abs_correlation
from .heatmap import Heatmap, HeatmapTheme
from .guides import guide_colorbar, guide_colourbar, guide_legend
from .markdown import markdown
from .plot import Plot
from .scales import (
    scale_identity, scale_gradient, scale_gradient_n, scale_manual,
    scale_color_continuous, scale_fill_continuous,
    scale_color_identity, scale_fill_identity,
    scale_color_gradient, scale_fill_gradient,
    scale_color_gradient2, scale_fill_gradient2,
    scale_color_gradient_n, scale_fill_gradient_n,
    scale_color_manual, scale_fill_manual,
)

__version__ = '0.0.1'

__all__ = [
    'Plot',
    'Heatmap',
    'HeatmapTheme',
    'Annotation',
    'ColumnAnnotation',
    'RowAnnotation',
    'clustering_distance',
    'inverse_abs_correlation',
    'guide_colorbar',
    'guide_colourbar',
    'guide_legend',
    'markdown',
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
]