# Use the official Python runtime as the base image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Install any necessary dependencies
RUN apt-get update && \
    apt-get install -y zip && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file to the working directory
COPY dev-lambda/requirements.txt .

# Install the Python packages listed in requirements.txt
RUN pip install --platform manylinux2014_x86_64 --only-binary=:all: -r requirements.txt -t /opt/python/

# Set the CMD to zip the installed packages into a layer
# change the `requests-layer` to the LAYER_NAME variable as per create_layer.sh file

CMD cd /opt && zip -r9 /app/prbot-layer.zip .
