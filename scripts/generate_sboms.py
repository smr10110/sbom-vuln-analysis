"""
Genera SBOMs en formato JSON para todos los repositorios usando Syft.

Uso:
    python scripts/generate_sboms.py
    python scripts/generate_sboms.py --repos-path PATH --output-path PATH

Requisitos:
    - Syft CLI instalado (https://github.com/anchore/syft)
    - Repositorios clonados en data/repos/
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import subprocess
from pathlib import Path


RUTA_BASE = Path(__file__).resolve().parents[1]
RUTA_REPOS_POR_DEFECTO = RUTA_BASE / "data" / "repos"
RUTA_RESULTADOS_POR_DEFECTO = RUTA_BASE / "data" / "results"
SUFIJO_SBOM = "-sbom.json"
MENSAJE_SYFT_NO_INSTALADO = (
    "Syft CLI no encontrado. Instálalo con: brew install syft "
    "o visita https://github.com/anchore/syft"
)

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
LOGGER = logging.getLogger(__name__)
PATRON_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


class SBOMGenerator:
    def __init__(self, repos_path: str, output_path: str):
        self.repos_path = Path(repos_path).expanduser().resolve()
        self.output_path = Path(output_path).expanduser().resolve()
        self.project_root = Path(__file__).resolve().parents[1]
        self.syft_path: str | None = None

    def discover_repositories(self) -> list[str]:
        if not self.repos_path.exists() or not self.repos_path.is_dir():
            raise FileNotFoundError(f"Directorio de repositorios no encontrado: {self.repos_path}")

        repositorios = sorted(
            str(ruta.relative_to(self.project_root))
            for ruta in self.repos_path.iterdir()
            if ruta.is_dir()
        )

        if not repositorios:
            LOGGER.warning("No se encontraron repositorios en %s", self.repos_path)

        return repositorios

    def generate_sbom(self, repo_path: str) -> str:
        ruta_repo = self.project_root / repo_path

        if not ruta_repo.exists() or not ruta_repo.is_dir():
            raise FileNotFoundError(f"Repositorio no encontrado: {ruta_repo}")

        if not any(ruta_repo.iterdir()):
            raise ValueError(f"El repositorio está vacío: {ruta_repo}")

        syft_path = self.syft_path or shutil.which("syft")
        if not syft_path:
            raise RuntimeError(MENSAJE_SYFT_NO_INSTALADO)

        comando = [syft_path, f"dir:{ruta_repo}", "-o", "syft-json"]
        resultado = subprocess.run(comando, capture_output=True, text=True, check=False)

        if resultado.returncode != 0:
            raise RuntimeError(
                f"Syft falló en {ruta_repo.name}: {resultado.stderr.strip()}"
            )

        return self._normalizar_json(resultado.stdout)

    def save_sbom(self, repo_name: str, sbom_data: str) -> Path:
        self.output_path.mkdir(parents=True, exist_ok=True)
        ruta_salida = self.output_path / f"{repo_name}{SUFIJO_SBOM}"
        ruta_salida.write_text(sbom_data, encoding="utf-8")
        LOGGER.info("SBOM guardado: %s", ruta_salida.relative_to(self.project_root))
        return ruta_salida

    def run(self):
        repositorios = self.discover_repositories()
        if not repositorios:
            return

        self.syft_path = shutil.which("syft")
        if not self.syft_path:
            raise RuntimeError(MENSAJE_SYFT_NO_INSTALADO)

        LOGGER.info("Usando Syft: %s", self.syft_path)
        self.output_path.mkdir(parents=True, exist_ok=True)

        exitosos, errores = 0, 0

        for indice, repo_path in enumerate(repositorios, start=1):
            ruta_repo = self.project_root / repo_path
            LOGGER.info("[%s/%s] Procesando %s", indice, len(repositorios), repo_path)

            try:
                sbom_data = self.generate_sbom(repo_path)
                self.save_sbom(ruta_repo.name, sbom_data)
                exitosos += 1
            except Exception as error:
                errores += 1
                parcial = self.output_path / f"{ruta_repo.name}{SUFIJO_SBOM}"
                if parcial.exists():
                    parcial.unlink()
                LOGGER.error("[%s/%s] Error en %s: %s", indice, len(repositorios), repo_path, error)

        LOGGER.info(
            "Resumen | total=%s | exitosos=%s | errores=%s",
            len(repositorios), exitosos, errores,
        )

    def _normalizar_json(self, salida_cruda: str) -> str:
        texto = PATRON_ANSI.sub("", salida_cruda).replace("\ufeff", "").strip()
        inicio = texto.find("{")
        fin = texto.rfind("}")
        if inicio != -1 and fin != -1:
            try:
                return json.dumps(json.loads(texto[inicio:fin + 1]), ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pass
        raise RuntimeError("Syft no devolvió JSON válido.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera SBOMs con Syft para todos los repositorios.")
    parser.add_argument("--repos-path", default=str(RUTA_REPOS_POR_DEFECTO))
    parser.add_argument("--output-path", default=str(RUTA_RESULTADOS_POR_DEFECTO))
    args = parser.parse_args()

    generador = SBOMGenerator(args.repos_path, args.output_path)
    try:
        generador.run()
    except Exception as error:
        LOGGER.error("%s", error)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
