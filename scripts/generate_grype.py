"""
Analiza vulnerabilidades en dependencias usando Grype (SCA).
Toma como entrada los SBOMs generados por Syft en la Parte 1.

Uso:
    python scripts/generate_grype.py
    python scripts/generate_grype.py --sboms-path PATH --output-path PATH

Requisitos:
    - Grype CLI instalado (https://github.com/anchore/grype)
    - SBOMs generados previamente con generate_sboms.py en data/results/

Salida por repositorio:
    - {repo}-grype-raw.json : salida original de Grype
    - {repo}-grype.json     : formato normalizado para análisis
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
from pathlib import Path


RUTA_BASE = Path(__file__).resolve().parents[1]
RUTA_RESULTADOS_POR_DEFECTO = RUTA_BASE / "data" / "results"
SUFIJO_SBOM = "-sbom.json"
SUFIJO_RAW = "-grype-raw.json"
SUFIJO_GRYPE = "-grype.json"
MENSAJE_GRYPE_NO_INSTALADO = (
    "Grype CLI no encontrado. Instálalo desde https://github.com/anchore/grype"
)

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
LOGGER = logging.getLogger(__name__)


class GrypeAnalyzer:
    def __init__(self, sboms_path: str, output_path: str):
        self.sboms_path = Path(sboms_path).expanduser().resolve()
        self.output_path = Path(output_path).expanduser().resolve()
        self.project_root = Path(__file__).resolve().parents[1]
        self.grype_path: str | None = None

    def discover_sboms(self) -> list[Path]:
        if not self.sboms_path.exists() or not self.sboms_path.is_dir():
            raise FileNotFoundError(f"Directorio de SBOMs no encontrado: {self.sboms_path}")

        sboms = sorted(self.sboms_path.glob(f"*{SUFIJO_SBOM}"))

        if not sboms:
            LOGGER.warning("No se encontraron SBOMs en %s", self.sboms_path)

        return sboms

    def run_grype(self, sbom_path: Path) -> str:
        """Ejecuta Grype sobre un SBOM y devuelve el JSON con vulnerabilidades."""
        grype_path = self.grype_path or shutil.which("grype")
        if not grype_path:
            raise RuntimeError(MENSAJE_GRYPE_NO_INSTALADO)

        # Grype acepta SBOMs directamente con el prefijo sbom:
        resultado = subprocess.run(
            [grype_path, f"sbom:{sbom_path}", "--output=json"],
            capture_output=True, text=True, check=False,
        )

        if resultado.returncode != 0 and "error" in resultado.stderr.lower():
            raise RuntimeError(f"Grype falló en {sbom_path.name}: {resultado.stderr}")

        if not resultado.stdout:
            raise RuntimeError(f"Grype no produjo salida para {sbom_path.name}")

        return resultado.stdout

    def parse_grype_output(self, grype_json_str: str) -> dict:
        try:
            grype_data = json.loads(grype_json_str)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"JSON de Grype inválido: {error}")

        matches = grype_data.get("matches", [])
        resultado = {
            "total_vulnerabilities": len(matches),
            "vulnerabilities_by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "vulnerabilities": [],
        }

        for match in matches:
            vuln = self._procesar_match(match)
            resultado["vulnerabilities"].append(vuln)
            sev = vuln["severity"].lower()
            if sev in resultado["vulnerabilities_by_severity"]:
                resultado["vulnerabilities_by_severity"][sev] += 1

        return resultado

    def save_analysis(self, repo_name: str, grype_raw: str, analysis: dict) -> None:
        self.output_path.mkdir(parents=True, exist_ok=True)

        raw_path = self.output_path / f"{repo_name}{SUFIJO_RAW}"
        raw_path.write_text(grype_raw, encoding="utf-8")

        norm_path = self.output_path / f"{repo_name}{SUFIJO_GRYPE}"
        norm_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

        LOGGER.info(
            "Grype guardado: %s | %s",
            raw_path.relative_to(self.project_root),
            norm_path.relative_to(self.project_root),
        )

    def run(self):
        sboms = self.discover_sboms()
        if not sboms:
            return

        self.grype_path = shutil.which("grype")
        if not self.grype_path:
            raise RuntimeError(MENSAJE_GRYPE_NO_INSTALADO)

        self.output_path.mkdir(parents=True, exist_ok=True)
        exitosos, errores = 0, 0

        for indice, sbom_path in enumerate(sboms, start=1):
            repo_name = sbom_path.name.replace(SUFIJO_SBOM, "")
            LOGGER.info("[%s/%s] Escaneando SBOM de %s", indice, len(sboms), repo_name)

            try:
                raw = self.run_grype(sbom_path)
                analysis = self.parse_grype_output(raw)
                self.save_analysis(repo_name, raw, analysis)
                LOGGER.info("  -> %s vulnerabilidades encontradas", analysis["total_vulnerabilities"])
                exitosos += 1
            except Exception as error:
                errores += 1
                for sufijo in [SUFIJO_RAW, SUFIJO_GRYPE]:
                    parcial = self.output_path / f"{repo_name}{sufijo}"
                    if parcial.exists():
                        parcial.unlink()
                LOGGER.error("[%s/%s] Error en %s: %s", indice, len(sboms), repo_name, error)

        LOGGER.info(
            "Resumen | total=%s | exitosos=%s | errores=%s",
            len(sboms), exitosos, errores,
        )

    def _procesar_match(self, match: dict) -> dict:
        artifact = match.get("artifact", {})
        vulnerability = match.get("vulnerability", {})
        fix_versions = vulnerability.get("fix", {}).get("versions", [])

        return {
            "package": artifact.get("name", "unknown"),
            "version": artifact.get("version", "unknown"),
            "vuln_id": vulnerability.get("id", "unknown"),
            "severity": vulnerability.get("severity", "Unknown"),
            "fix_version": fix_versions[0] if fix_versions else "N/A",
            "description": vulnerability.get("description", ""),
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analiza vulnerabilidades en dependencias usando los SBOMs generados por Syft."
    )
    parser.add_argument(
        "--sboms-path",
        default=str(RUTA_RESULTADOS_POR_DEFECTO),
        help="Directorio donde están los SBOMs (*-sbom.json).",
    )
    parser.add_argument(
        "--output-path",
        default=str(RUTA_RESULTADOS_POR_DEFECTO),
        help="Directorio donde se guardarán los resultados.",
    )
    args = parser.parse_args()

    analizador = GrypeAnalyzer(args.sboms_path, args.output_path)
    try:
        analizador.run()
    except Exception as error:
        LOGGER.error("%s", error)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
