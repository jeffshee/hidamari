#!/bin/sh

set -e

# Define the Flatpak app ID once
APP_ID="page.codeberg.zynequ.Kapitano"

# Derive the manifest filename and URL
MANIFEST_FILE="$APP_ID.json"
MANIFEST_URL="https://raw.githubusercontent.com/flathub/$APP_ID/refs/heads/master/$MANIFEST_FILE"

# Destination directory (upstream project folder)
DEST_DIR="."

# Ensure destination exists
mkdir -p "$DEST_DIR"

# Download and overwrite
echo "Downloading $MANIFEST_FILE to $DEST_DIR..."
curl -L "$MANIFEST_URL" -o "$DEST_DIR/$MANIFEST_FILE"

# Check for success
if [ $? -eq 0 ]; then
    echo "Successfully downloaded $MANIFEST_FILE."
else
    echo "Download failed!" >&2
    exit 1
fi
