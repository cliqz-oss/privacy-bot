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
        "beautifulsoup4==4.6.0",
        "cchardet==2.1.0",
        "docopt==0.6.2",
        "html2text==2016.9.19",
        "langdetect==1.0.7",
        "lxml==3.7.3",
        "pypandoc==1.4",
        "readability-lxml==0.6.2",
        "requests==2.14.2",
        "selenium==3.4.2",
        "tldextract==2.0.2",
    ],
    long_description=LONG_DESCRIPTION,
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
    ]
)
