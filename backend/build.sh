#!/usr/bin/env bash
# Update package list
apt-get update -y

# Install R
apt-get install -y r-base

# Install R packages
R -e "install.packages('nflreadr', repos='http://cran.rstudio.com/')"
