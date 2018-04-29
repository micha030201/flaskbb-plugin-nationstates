# -*- coding: utf-8 -*-
"""
    nationstates
    ~~~~~~~~~~~~

    Integration with NationStates.net for flaskBB

    :copyright: (c) 2018 by Михаил Лебедев.
    :license: BSD License, see LICENSE for more details.
"""
import ast
import re
from setuptools import find_packages, setup
from setuptools.command.install import install


with open("nationstates/__init__.py", "rb") as f:
    version_line = re.search(
        r"__version__\s+=\s+(.*)", f.read().decode("utf-8")
    ).group(1)
    version = str(ast.literal_eval(version_line))


setup(
    name="flaskbb-plugin-nationstates",
    version=version,
    license="BSD License",
    author="Михаил Лебедев",
    author_email="micha030201@gmail.com",
    description="Integration with NationStates.net for flaskBB",
    long_description=__doc__,
    keywords="flaskbb plugin",
    packages=find_packages("."),
    include_package_data=True,
    package_data={
        "": ["nationstates/translations/*/*/*.mo",
             "nationstates/translations/*/*/*.po"]
    },
    zip_safe=False,
    platforms="any",
    entry_points={
        "flaskbb_plugins": [
            "nationstates = nationstates"
        ]
    },
    install_requires=[
        "FlaskBB"  # pin to a version to has pluggy integration
    ],
    setup_requires=[
        "Babel",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Environment :: Plugins",
        "Framework :: Flask",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],
)
