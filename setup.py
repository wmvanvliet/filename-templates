#! /usr/bin/env python
from setuptools import setup
import codecs
import os

if __name__ == "__main__":
    if os.path.exists('MANIFEST'):
        os.remove('MANIFEST')

    setup(
        name='filename-templates',
        maintainer='Marijn van Vliet',
        maintainer_email='w.m.vanvliet@gmail.com',
        description='Make filenames from string templates',
        license='BSD-3',
        url='https://github.com/wmvanvliet/filename-templates',
        version='1.0',
        download_url='https://github.com/wmvanvliet/filename-templates/archive/main.zip',
        long_description=codecs.open('README.md', encoding='utf8').read(),
        classifiers=['Intended Audience :: Science/Research',
                     'Intended Audience :: Developers',
                     'License :: OSI Approved',
                     'Programming Language :: Python',
                     'Topic :: Software Development',
                     'Topic :: Scientific/Engineering',
                     'Operating System :: Microsoft :: Windows',
                     'Operating System :: POSIX',
                     'Operating System :: Unix',
                     'Operating System :: MacOS'],
        platforms='any',
        packages=['filename_templates'],
        tests_require=['pytest'],
    )
