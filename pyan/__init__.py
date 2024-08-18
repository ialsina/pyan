#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from glob import glob
import io
from typing import List, Union

from .analyzer import CallGraphVisitor
from .main import main  # noqa: F401, for export only.
from .visgraph import VisualGraph
from .writers import DotWriter, HTMLWriter, DotConverter

__version__ = "1.2.1"

