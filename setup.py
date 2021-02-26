# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

try:
    LONG_DESCRIPTION = open("README.md").read()
except IOError:
    LONG_DESCRIPTION = ""

setup(
    name="privacy-bot",
    version="0.1.0",
    description="Privacy Bot gathers, fetches, persists and analyze privacy policies",
    license="AGPLv3",
    author="Rémi Berson",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'find_policies  = privacy_bot.mining.find_policies:main',
            'fetch_policies = privacy_bot.mining.fetch_policies:main'
        ]
    },
    install_requires=[
        "Cython==0.25.2",
        "aiodns==1.1.1",
        "aiohttp==3.7.4",
        "cchardet==2.1.0",
        "cld2-cffi==0.1.4",
        "docopt==0.6.2",
        "regex==2017.5.26",
        "requests==2.20.0",
        "selenium==3.4.2",
        "tldextract==2.0.2",
        "tqdm==4.14.0",
    ],
    long_description=LONG_DESCRIPTION,
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
    ]
)
