# SBOM Analysis

## Requisitos
- Python 3
- Syft
- Grype

## Instalación
pip install -r requirements.txt

## Ejecución

1. Clonar repos:
python scripts/1_clone_repos.py

2. Generar SBOM:
python scripts/2_generate_sbom.py

3. Escanear vulnerabilidades:
python scripts/3_scan_vulns.py

4. Abrir notebook:
analysis.ipynb

En caso de que se quiera utilizar con otra organizacion hay que:
1. borrar el contenido de repos
2. borrar el contenido de sboms
3. borrar el contenido de vulns
4. cambiar el nombre de la organizacion en scripts\1_clone_repos. la linea ORG = "pallets" en donde pallets es el nombre de la organizacion a analizar.

