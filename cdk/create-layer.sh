#!/bin/bash
python3 -m venv ./python
source ./python/bin/activate
echo "Virtual environment created"
ENV=$1

# Install packages into the virtual environment without specifying a custom target directory
pip install --platform manylinux2010_x86_64 --only-binary=:all: langchain="0.0.5" PyGithub="1.54.1" -t ./python -v
echo "Packages installed to ./$ENV-lambda/layer.zip"

# Create the zip file preserving the entire site-packages directory structure
zip -r "./$ENV-lambda/layer.zip" ./python/

# Clean up temporary files
deactivate
rm -rf ./python
