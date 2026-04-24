# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sys
from importlib import metadata


DOCS_ROOT = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(DOCS_ROOT, ".."))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")

if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)


project = "dnfile"
author = "MalwareFrank"

try:
    release = metadata.version("dnfile")
except metadata.PackageNotFoundError:
    release = "0.0.0"

version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
]

autosummary_generate = True
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = []

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
