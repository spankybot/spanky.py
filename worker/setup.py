from glob import glob
from os.path import basename
from os.path import splitext

from setuptools import setup
from setuptools import find_packages

setup(
    name="SpankyWorker",
    version="0.1.0",
    license="WTFPL",
    author="plp",
    author_email="plp.github@gmail.com",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    scripts=[],
    url="",
    description="Python worker for Spankybot",
    long_description=open("README.txt").read(),
    install_requires=[
        "SpankyCommon",
        "discord.py >= 1.5.1",
        "watchdog"
    ],
)