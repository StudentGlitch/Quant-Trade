"""setup.py — packaging for the webcrawler tool."""

from setuptools import find_packages, setup

setup(
    name="webcrawler",
    version="0.1.0",
    description="IDX annual report crawler and downloader",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.31.0",
        "playwright>=1.52.0",
    ],
    entry_points={
        "console_scripts": [
            "idx-annual-reports=webcrawler.cli:main",
        ],
    },
)
