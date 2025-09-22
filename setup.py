#!/usr/bin/env python3
"""
Setup script for Image Deduplicator
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="image-deduplicator",
    version="2.0.0",
    author="MTGMAD",
    author_email="linux73@protonmail.com",
    description="Cross-platform Python application to find and manage duplicate images with visual interface",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/MTGMAD/image-dedup",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Graphics",
        "Topic :: System :: Filesystems",
    ],
    python_requires=">=3.7",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "image-deduplicator=image_deduplicator:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
