from setuptools import find_packages, setup
from Interlace.lib.core.__version__ import __version__


def dependencies(imported_file):
    with open(imported_file, encoding="utf-8") as file:
        return file.read().splitlines()


with open("README.md", encoding="utf-8") as readme_file:
    long_description = readme_file.read()

setup(
    name="InterlaceX",
    license="GPLv3",
    description="Turn single-threaded CLI apps into fast, multi-threaded tools with CIDR and glob support."
                "Enhanced fork with Python 3.13+ support, silent mode, and more.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="0xhunster",
    version=__version__,
    url="https://github.com/0xhunster/InterlaceX",
    packages=find_packages(exclude=('tests',)),
    package_data={'Interlace': ['*.txt']},
    entry_points={
        'console_scripts': [
            'interlacex = Interlace.interlace:main'
        ]
    },
    python_requires='>=3.8',
    install_requires=dependencies('requirements.txt'),
    include_package_data=True
)

