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
1. Borrar el contenido de repos
2. Borrar el contenido de sboms
3. Borrar el contenido de vulns
4. Cambiar el nombre de la organizacion en scripts\1_clone_repos. La linea ORG = "pallets" en donde
pallets es el nombre de la organizacion a analizar. Y MAX_REPOS = 10 la cantidad de repositorios que
deseen analizar.

