#!/usr/bin/env python3
"""An Exif GPS editor

"""

from setuptools import setup, find_packages
from codecs import open
from os.path import abspath, dirname, join

here = abspath(dirname(__file__))

with open(join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='exifgpseditor',
    version='1.0.0a1',
    description='An Exif GPS Editor',
    long_description=long_description,
    url='https://github.com/Zigazou/exifgpseditor',
    author='Frédéric BISSON',
    author_email='zigazou@free.fr',
    license='GPL-3',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Multimedia :: Graphics :: Editors',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
    data_files=[
        ('share/exifgpseditor', ['exifgpseditor/exifgpseditor.glade',
                                 'exifgpseditor/exifgpseditor_icon.png'
                                ]
        ),
    ],
    keywords='exif gps editor gui image',
    packages=find_packages(),
    entry_points={
        'console_scripts': ['exifgpseditor=exifgpseditor:main'],
    },
)

