#!/usr/bin/env bash
VENV=venv

python3 -mvenv venv
rm -rf README.md index.html README_files *.png
PATH=${VENV}/bin:$PATH

pip install -U pip wheel setuptools
pip install -r requirements.txt

jupyter-nbconvert --ExecutePreprocessor.timeout=600 --execute --to markdown --output=README.md README.ipynb
jupyter-nbconvert --ExecutePreprocessor.timeout=600 --execute --to html --output=index.html README.ipynb
jupyter-nbconvert --ExecutePreprocessor.timeout=600 --execute --to pdf --output="MI Rep Staff Disbursement Analysis.pdf" README.ipynb
