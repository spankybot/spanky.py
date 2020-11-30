from glob import glob
from os.path import basename
from os.path import splitext

from setuptools import setup
from setuptools import find_packages

setup(
    name="SpankyCommon",
    version="0.1.0",
    license="WTFPL",
    author="plp",
    author_email="plp.github@gmail.com",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    description="Common files for Spankybot server and client",
    long_description="",
    install_requires=[
        "google-api-python-client",
        "grpcio>=1.34.0rc1",
        "grpcio-tools",
    ],
)