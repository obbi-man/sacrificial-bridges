"""Setup для sacrificial-bridges."""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="sacrificial-bridges",
    version="0.1.0",
    description="Мостики вместо support structures для 3D-печати",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Pulsar AI",
    license="MIT",
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "numpy>=1.24",
        "trimesh>=4.0",
        "scipy>=1.10",
    ],
    entry_points={
        "console_scripts": [
            "sacrificial-bridges=sacrificial_bridges.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Graphics :: 3D Modeling",
        "Topic :: Utilities",
    ],
    keywords="3d-printing supports bridge tree prusaslicer cura bambu",
)
