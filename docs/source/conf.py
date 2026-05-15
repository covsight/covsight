# -*- coding: utf-8 -*-
#
# covsight documentation build configuration file

import datetime
import os
import sys

# Ensure covsight and covsight.core packages are importable
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_repo_root, "src"))
sys.path.insert(0, os.path.join(_repo_root, "packages", "covsight-core", "python"))

os.environ["SPHINX_BUILD"] = "1"

# -- General configuration -----------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
    "sphinx_design",
    "sphinx_issues",
    "sphinxarg.ext",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

issues_github_path = "covsight/covsight"

templates_path = ["_templates"]

source_suffix = ".rst"

master_doc = "index"

project = "covsight"
copyright = f"2024-{datetime.datetime.now().year}, Matthew Ballance and Contributors"
author = "Matthew Ballance and Contributors"

release = "0.1.0"
version = "0.1"

autoclass_content = "both"

exclude_patterns = []

pygments_style = "sphinx"

# -- Options for HTML output ---------------------------------------------------

html_theme = "sphinx_rtd_theme"

htmlhelp_basename = "covsightdoc"

# -- Options for LaTeX output --------------------------------------------------

latex_documents = [
    ("index", "covsight.tex", "covsight Documentation",
     "Matthew Ballance and Contributors", "manual"),
]

man_pages = [
    ("index", "covsight", "covsight Documentation",
     ["Matthew Ballance and Contributors"], 1),
]

graphviz_output_format = "svg"
