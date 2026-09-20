# PageScrapper

**PageScrapper** est un extracteur web haute fidélité basé sur Chromium.

Il permet de récupérer une page web et ses ressources principales afin de générer une copie locale exploitable.

## Fonctionnalités

* 🌐 Extraction de pages web avec Chromium
* 📄 Récupération du HTML
* 🎨 Récupération des fichiers CSS
* ⚙️ Récupération du JavaScript
* 🖼️ Récupération des assets
* 🔗 Réécriture des références vers les ressources locales
* 🧪 Mode `--test` pour reconstruire une copie locale de la page

## Installation

> **PageScrapper v1.0.0 est Linux uniquement et Debian uniquement.**

Téléchargez le fichier `.deb` correspondant à votre architecture puis installez-le avec :

```bash
sudo apt install ./pagescrapper_1.0.0_amd64.deb
```

Chromium doit être installé sur le système.

```bash
sudo apt install chromium
```

## Utilisation

Extraire une page :

```bash
pascra https://example.com
```

Tester la reconstruction locale :

```bash
pascra https://example.com --test
```

Afficher l'aide :

```bash
pascra --help
```

Afficher la version :

```bash
pascra --version
```

## Sortie

Les fichiers extraits sont placés dans le dossier `output/`.

```text
output/
├── html/
├── css/
├── javascript/
├── assets/
└── index.html
```

Avec `--test`, `index.html` est généré à la racine de `output/` afin de pouvoir ouvrir la copie locale directement dans un navigateur.

## Configuration requise

* Linux
* Debian
* Python 3.13+ *(pour l'installation depuis les sources)*
* Chromium

## Version

**v1.0.0**

## Auteur

**yolezz**
