#!/usr/bin/env python
"""The setup script."""
import pathlib
from setuptools import setup

HERE = pathlib.Path(__file__).parent
requirements = [
    l
    for l in (HERE / "requirements.txt").read_text().splitlines()
    if not l.startswith("#")
]

dev_requirements = [
    l
    for l in (HERE / "requirements_dev.txt").read_text().splitlines()
    if not l.startswith("#")
]

setup(
    use_scm_version=True,
    install_requires=requirements,
    extras_require={"dev": dev_requirements},
)
