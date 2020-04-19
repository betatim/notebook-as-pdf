import os
from setuptools import find_packages, setup


HERE = os.path.dirname(__file__)

with open(os.path.join(HERE, "README.md"), encoding="utf8") as f:
    readme = f.read()

setup(
    author="Tim Head",
    author_email="betatim@gmail.com",
    version="0.0.1",
    description="Jupyter extension to export notebooks as PDFs",
    install_requires=["nbconvert", "pyppeteer", "pikepdf"],
    keywords="jupyter pdf export bundler",
    license="BSD3",
    long_description=readme,
    long_description_content_type="text/markdown",
    name="notebook-as-pdf",
    packages=find_packages(),
    python_requires=">=3.6",
    url="https://github.com/betatim/notebook-as-pdf",
    entry_points={
        "nbconvert.exporters": ["PDF via HTML = notebook_as_pdf:PDFExporter"]
    },
)
