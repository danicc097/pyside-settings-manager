#!/bin/bash

set -euo pipefail

if [ -z "$1" ]; then
  echo "Error: Please provide a semantic version number (e.g., ./release.sh 1.2.3)" && exit 1
fi

VERSION=$1

if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Error: Version '$VERSION' is not a valid semantic version (e.g., 1.2.3)" && exit 1
fi

if git ls-remote --tags origin "v$VERSION" | grep -q "v$VERSION"; then
  echo "Error: Tag v$VERSION already exists in remote repository" && exit 1
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ] && [ "$CURRENT_BRANCH" != "master" ]; then
  echo "Error: Must be on main or master branch to release" && exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "Error: Working directory is not clean. Please commit or stash changes." && exit 1
fi

if [ ! -f "pyproject.toml" ]; then
  echo "Error: pyproject.toml not found" && exit 1
fi

sed -i "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml

git add pyproject.toml
git commit -m "release v$VERSION"
git push origin "$CURRENT_BRANCH"

git tag "v$VERSION"
git push origin "v$VERSION"

echo "Successfully released version v$VERSION"
