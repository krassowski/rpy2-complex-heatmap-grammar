# rpy2-complex-heatmap-grammar
Python heatmap interface using intuitive grammar of graphics, implemented as an rpy2 wrapper around ComplexHeatmap package.

## Introduction

What this package is:
- an exploration in search of the dream API for complex heatmap creation
- trying to get the best of Python, ggplot2 (/[plotnine](https://github.com/has2k1/plotnine)) and ComplexHeatmap
- oriented towards data exploration in Jupyter notebooks with IPython (-compatible) kernel
- pushing boundaries for Python-R interoperability via [rpy2](https://rpy2.github.io/)

What this package is NOT:
- likely not suitable for beginners (if you can get through installation/used rpy2 before you are not a beginner)
- not a drop-in substitute for ComplexHeatmap for Python
- not ready for production use (API is subject to change)
- not affiliated with rpy2 or ComplexHeatmap

Intrigued? Check out the [examples](https://github.com/krassowski/rpy2-complex-heatmap-grammar/blob/main/Examples.ipynb).

## Installation

Requirements

- Python >=3.9
  - packages: rpy2, pandas, numpy, IPython
- R >=4.1
  - packages: ComplexHeatmap


Installation from PyPI:

```
pip install heatmap-grammar
```

Latest version:

```
pip install git+https://github.com/krassowski/rpy2-complex-heatmap-grammar.git
```