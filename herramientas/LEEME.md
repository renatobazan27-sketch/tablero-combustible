# Herramientas de publicación

Sin datos: solo el código que arma la página. Los datos viven en el tablero de Claude y se cifran antes de subirse.

1. `build_standalone.py plantilla.html d3.min.js fuentes/ carpeta_csv/ tablero.html` arma el tablero en un solo HTML.
2. `cifrar.py tablero.html "<clave>" index.html` lo cifra (AES-256-GCM, PBKDF2 600 000 iteraciones) para GitHub Pages.

La clave nunca se guarda en este repositorio.
