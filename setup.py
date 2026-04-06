from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in omnione/__init__.py
from omnione import __version__ as version

setup(
	name="omnione",
	version=version,
	description="Omni One",
	author="Outpost.Work LLP",
	author_email="anas@outpost.work",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
