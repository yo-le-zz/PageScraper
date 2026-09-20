#!/usr/bin/env bash

set -euo pipefail


# ============================================================
# Configuration
# ============================================================

APP_NAME="pagescrapper"
BINARY_NAME="pascra"

VERSION="$(
    uv run python -c '
import tomllib

with open("pyproject.toml", "rb") as f:
    print(tomllib.load(f)["project"]["version"])
'
)"

ARCH="amd64"

ROOT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")"
    pwd
)"

BUILD_DIR="$ROOT_DIR/build"
DIST_DIR="$ROOT_DIR/dist"

NUITKA_DIR="$BUILD_DIR/nuitka"
DEB_ROOT="$BUILD_DIR/deb"

INSTALL_DIR="$DEB_ROOT/opt/$APP_NAME"
BIN_DIR="$DEB_ROOT/usr/bin"
DEBIAN_DIR="$DEB_ROOT/DEBIAN"

MAIN_FILE="$ROOT_DIR/src/PageScrapper/main.py"


# ============================================================
# Vérifications
# ============================================================

echo "🚀 Build PageScrapper v$VERSION"
echo

if [[ ! -f "$MAIN_FILE" ]]; then
    echo "❌ Fichier principal introuvable :"
    echo "   $MAIN_FILE"
    exit 1
fi


# ============================================================
# Nettoyage
# ============================================================

rm -rf "$BUILD_DIR"
rm -rf "$DIST_DIR"

mkdir -p \
    "$BUILD_DIR" \
    "$DIST_DIR"


# ============================================================
# Synchronisation uv
# ============================================================

echo "📦 Synchronisation uv..."

uv sync --dev

echo


# ============================================================
# Vérification de Chromium
# ============================================================

echo "🌐 Vérification de Chromium..."

if command -v chromium >/dev/null 2>&1; then
    CHROMIUM_PATH="$(command -v chromium)"
    echo "✓ Chromium trouvé : $CHROMIUM_PATH"

elif command -v chromium-browser >/dev/null 2>&1; then
    CHROMIUM_PATH="$(command -v chromium-browser)"
    echo "✓ Chromium trouvé : $CHROMIUM_PATH"

else
    echo "❌ Chromium n'est pas installé."
    echo
    echo "Installe-le avec :"
    echo "  sudo apt install chromium"
    exit 1
fi

echo


# ============================================================
# Compilation Nuitka
# ============================================================

echo "⚙️ Compilation Nuitka..."

uv run python -m nuitka \
    --standalone \
    --onefile \
    --follow-imports \
    --assume-yes-for-downloads \
    --output-dir="$NUITKA_DIR" \
    --output-filename="$BINARY_NAME" \
    --include-package=PageScrapper \
    --include-package=PageScrapper.scraper \
    --include-package=playwright \
    --include-package=typer \
    "$MAIN_FILE"

echo


# ============================================================
# Vérification du binaire
# ============================================================

BINARY="$NUITKA_DIR/$BINARY_NAME"

if [[ ! -f "$BINARY" ]]; then
    echo "❌ Binaire Nuitka introuvable :"
    echo "   $BINARY"
    exit 1
fi

echo "✓ Binaire compilé"


# ============================================================
# Préparation du paquet Debian
# ============================================================

echo
echo "📦 Préparation du paquet Debian..."

mkdir -p \
    "$INSTALL_DIR" \
    "$BIN_DIR" \
    "$DEBIAN_DIR"


cp \
    "$BINARY" \
    "$INSTALL_DIR/$BINARY_NAME"


# ============================================================
# Wrapper
# ============================================================

cat > "$BIN_DIR/$BINARY_NAME" << EOF
#!/bin/sh
exec /opt/$APP_NAME/$BINARY_NAME "\$@"
EOF

chmod +x \
    "$BIN_DIR/$BINARY_NAME"


# ============================================================
# Métadonnées Debian
# ============================================================

cat > "$DEBIAN_DIR/control" << EOF
Package: $APP_NAME
Version: $VERSION
Section: web
Priority: optional
Architecture: $ARCH
Maintainer: yolezz
Depends: chromium
Description: PageScrapper - extracteur web haute fidélité
 Extrait le HTML, CSS, JavaScript et les assets
 d'une page web avec Chromium.
EOF


# ============================================================
# Construction du .deb
# ============================================================

DEB_FILE="$DIST_DIR/${APP_NAME}_${VERSION}_${ARCH}.deb"

echo
echo "🔨 Construction du paquet Debian..."

dpkg-deb \
    --build \
    "$DEB_ROOT" \
    "$DEB_FILE"


# ============================================================
# Résultat
# ============================================================

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Build PageScrapper terminé !"
echo
echo "📦 Paquet :"
echo "   $DEB_FILE"
echo
echo "🔧 Binaire :"
echo "   $BINARY_NAME"
echo
echo "📏 Taille :"
du -h "$DEB_FILE" | cut -f1
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"