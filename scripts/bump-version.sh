#!/bin/bash
set -eu

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

OLD_VERSION="$1"
NEW_VERSION="$2"

echo "$NEW_VERSION" > version

echo "New version: $NEW_VERSION"
