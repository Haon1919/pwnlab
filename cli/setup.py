from setuptools import setup, find_packages

setup(
    name="blaqliq",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.7",
        "rich>=13.7.0",
        "httpx>=0.27.2",
        "pyyaml>=6.0.2",
        "keyring>=25.2.1",
    ],
    entry_points={
        "console_scripts": [
            "blaqliq=blaqliq.main:cli",
        ],
    },
)
