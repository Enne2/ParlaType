#!/bin/bash
set -e

APP_NAME="parlatype"
VERSION="2.0.0"
RPMBUILD_DIR="$HOME/rpmbuild"

# Create rpmbuild structure
mkdir -p $RPMBUILD_DIR/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Create source tarball
echo "Creating source tarball..."
# We use a temporary directory to create the correct folder structure inside the tarball
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/$APP_NAME-$VERSION"

# Copy files to temp dir
cp -r main.py parlatype requirements.txt README.md parlatype.desktop parlatype.svg parlatype-setup parlatype.sh "$TEMP_DIR/$APP_NAME-$VERSION/"
cp -r prompts "$TEMP_DIR/$APP_NAME-$VERSION/"
# Models are downloaded at install time, not included in RPM
# cp -r models "$TEMP_DIR/$APP_NAME-$VERSION/"

# Create tarball
tar -czf "$RPMBUILD_DIR/SOURCES/$APP_NAME-$VERSION.tar.gz" -C "$TEMP_DIR" "$APP_NAME-$VERSION"
rm -rf "$TEMP_DIR"

# Copy spec file
cp parlatype.spec "$RPMBUILD_DIR/SPECS/"

# Build RPM
echo "Building RPM using $(nproc) cores..."
rpmbuild -ba "$RPMBUILD_DIR/SPECS/parlatype.spec"

echo "Done. RPMs are in $RPMBUILD_DIR/RPMS/"
