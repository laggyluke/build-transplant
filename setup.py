#!/usr/bin/env python

import os
from setuptools import setup, find_packages

data_patterns = [
    'templates/**.html',
    'static/**.jpg',
    'static/**.css',
    'static/**.js',
    'static/**.txt',
]

setup(name='relengapi-transplant',
    version='0.1.0',
    description='A tool to transplant commits from one Mercurial repository into another',
    author='George Miroshnykov',
    author_email='gmiroshnykov@mozilla.com',
    url='https://github.com/laggyluke/transplant',
    entry_points={
        "relengapi_blueprints": [
            'mapper = relengapi.blueprints.transplant:bp',
        ],
    },
    packages=find_packages(),
    namespace_packages=['relengapi', 'relengapi.blueprints'],
    data_files=[
        ('relengapi-' + dirpath, [os.path.join(dirpath, f) for f in files])
        for dirpath, _, files in os.walk('docs')
        # don't include directories not containing any files, as they will be
        # included in installed-files.txt, and deleted (rm -rf) on uninstall;
        # see https://bugzilla.mozilla.org/show_bug.cgi?id=1088676
        if files
    ],
    package_data={  # NOTE: these files must *also* be specified in MANIFEST.in
        'relengapi.blueprints.transplant': data_patterns,
    },
    install_requires=[
        'Flask',
        'relengapi>=0.3',
    ],
    license='MPL2',
    extras_require={
        'test': [
            'nose',
            'mock',
            'pep8',
            'pyflakes',
            'coverage',
        ]
    })
