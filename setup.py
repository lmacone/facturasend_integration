from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in facturasend_integration/__init__.py
from facturasend_integration import __version__ as version

setup(
	name="facturasend_integration",
	version=version,
	description="Integración de FacturaSend Paraguay con ERPNext para facturación electrónica",
	author="Luis",
	author_email="luis@example.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
