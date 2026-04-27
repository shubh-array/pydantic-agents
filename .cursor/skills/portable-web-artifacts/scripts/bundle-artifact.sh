#!/bin/bash
set -e

OUTPUT_FILE="${OUTPUT_FILE:-bundle.html}"

echo "Bundling React app to a self-contained HTML file..."

if [ ! -f "package.json" ]; then
  echo "Error: No package.json found. Run this script from your project root."
  exit 1
fi

if [ ! -f "index.html" ]; then
  echo "Error: No index.html found in project root."
  echo "This script requires an index.html entry point."
  exit 1
fi

if ! command -v pnpm >/dev/null 2>&1; then
  echo "Error: pnpm is required. Install pnpm or run the initializer first."
  exit 1
fi

echo "Installing bundling dependencies..."
pnpm add -D parcel @parcel/config-default parcel-resolver-tspaths html-inline

if [ ! -f ".parcelrc" ]; then
  echo "Creating Parcel configuration with path alias support..."
  cat > .parcelrc << 'EOF'
{
  "extends": "@parcel/config-default",
  "resolvers": ["parcel-resolver-tspaths", "..."]
}
EOF
fi

echo "Cleaning previous build output..."
rm -rf dist "$OUTPUT_FILE"

echo "Building with Parcel..."
pnpm exec parcel build index.html --dist-dir dist --no-source-maps

echo "Inlining assets into $OUTPUT_FILE..."
pnpm exec html-inline dist/index.html > "$OUTPUT_FILE"

FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)

echo "Bundle complete."
echo "Output: $OUTPUT_FILE ($FILE_SIZE)"
echo "Preview locally by opening the file in a browser or serve it with a static file server."
