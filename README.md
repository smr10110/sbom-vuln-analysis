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
