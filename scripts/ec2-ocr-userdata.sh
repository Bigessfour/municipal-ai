#!/bin/bash
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y poppler-utils tesseract-ocr libtesseract-dev git-lfs

# Marker so we know userdata finished
mkdir -p /home/ubuntu
touch /home/ubuntu/userdata-ready
chown ubuntu:ubuntu /home/ubuntu/userdata-ready
