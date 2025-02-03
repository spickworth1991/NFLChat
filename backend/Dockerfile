# Base image with Python and R support
FROM rocker/r-ver:4.2.2

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    libpython3-dev \
    libpcre2-dev \
    liblzma-dev \
    libbz2-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    build-essential

# Upgrade pip and install build tools
RUN pip3 install --upgrade pip setuptools wheel

# Install R packages
RUN R -e "install.packages(c('nflreadr'), repos='https://cran.rstudio.com/')"

# Install Python packages
COPY requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt

# Set the working directory
WORKDIR /app

# Copy application files
COPY . /app

# Expose the application port
EXPOSE 5000

# Command to run the application
CMD ["python3", "app.py"]
