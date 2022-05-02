#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = ["pefile>=2019.4.18"]

setup_requirements = [
    "pytest-runner",
]

test_requirements = [
    "pytest>=3",
    "isort==5.10.1",
    "pycodestyle==2.8.0",
    "mypy==0.950",
]

setup(
    author="MalwareFrank",
    python_requires=">=3.5",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    description="Parse .NET executable files.",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="dnfile",
    name="dnfile",
    packages=find_packages(where="src", include=["dnfile", "dnfile.*"]),
    package_dir={"": "src"},
    package_data={"dnfile": ["py.typed"]},
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    extras_require={'test': test_requirements},
    url="https://github.com/malwarefrank/dnfile",
    version="0.11.0",
    zip_safe=False,
)
