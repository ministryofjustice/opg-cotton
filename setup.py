#!/usr/bin/env python

from setuptools import setup

setup(
    name='opg-cotton',
    version='0.8.0',
    url='http://github.com/ministryofjustice/opg-cotton',
    license='MIT',
    author='',
    author_email='',
    description='',
    long_description=__doc__,
    packages=['cotton'],
    zip_safe=True,
    platforms='any',
    install_requires=[
        'fabric',
        'boto',
        'jinja2',
        'python-dateutil',
        'pyyaml',
        'GitPython',
        'pptable',
    ],
    classifiers=[
    ],
    entry_points="""
    [console_scripts]
    parsed-salt=cotton.cli:parsed_salt
    parsed-salt-call=cotton.cli:parsed_salt_call
    """,
)
