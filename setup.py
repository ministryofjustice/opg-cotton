#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='opg-cotton',
    version='0.8.5',
    url='http://github.com/ministryofjustice/opg-cotton',
    license='MIT',
    author='',
    author_email='',
    description='',
    long_description=__doc__,
    packages=find_packages(),
    zip_safe=False,
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
    # For tests
    test_suite='nose.collector',
    tests_require=['nose'],
)
