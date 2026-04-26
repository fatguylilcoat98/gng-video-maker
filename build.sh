#!/bin/bash
set -e

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies (using pre-compiled wheels only)..."
pip install --only-binary=all --no-cache-dir -r requirements.txt

echo "Build complete!"