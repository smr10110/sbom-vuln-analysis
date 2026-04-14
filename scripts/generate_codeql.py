"""
Analiza el código fuente con CodeQL (SAST) en todos los repositorios.

Uso:
    python scripts/generate_codeql.py
    python scripts/generate_codeql.py --repos-path PATH --output-path PATH

Requisitos:
    - CodeQL CLI instalado (https://github.com/github/codeql-cli-binaries/releases)
    - Query packs instalados:
        codeql pack download codeql/python-queries
        codeql pack download codeql/javascript-queries
        codeql pack download codeql/java-queries
    - Repositorios clonados en data/repos/

Salida por repositorio:
    - {repo}-codeql.json : resultados normalizados
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path


RUTA_BASE = Path(__file__).resolve().parents[1]
RUTA_REPOS_POR_DEFECTO = RUTA_BASE / "data" / "repos"
RUTA_RESULTADOS_POR_DEFECTO = RUTA_BASE / "data" / "results"
SUFIJO_CODEQL = "-codeql.json"
MENSAJE_CODEQL_NO_INSTALADO = (
    "CodeQL CLI no encontrado. Instálalo desde "
    "https://github.com/github/codeql-cli-binaries/releases"
)

EXTENSIONES_LENGUAJE = {
    ".py": "python",
    ".js": "javascript", ".ts": "javascript",
    ".jsx": "javascript", ".tsx": "javascript",
    ".java": "java",
    ".cpp": "cpp", ".c": "cpp",
    ".cs": "csharp",
    ".go": "go",
}

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
LOGGER = logging.getLogger(__name__)


class CodeQLAnalyzer:
    def __init__(self, repos_path: str, output_path: str):
        self.repos_path = Path(repos_path).expanduser().resolve()
        self.output_path = Path(output_path).expanduser().resolve()
        self.project_root = Path(__file__).resolve().parents[1]
        self.codeql_path: str | None = None
        self.temp_dir: Path | None = None

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

    def run_codeql(self, repo_path: str) -> str:
        ruta_repo = self.project_root / repo_path

        if not ruta_repo.exists() or not ruta_repo.is_dir():
            raise FileNotFoundError(f"Repositorio no encontrado: {ruta_repo}")

        if not any(ruta_repo.iterdir()):
            raise ValueError(f"El repositorio está vacío: {ruta_repo}")

        lenguaje = self._detectar_lenguaje(ruta_repo)
        if not lenguaje:
            LOGGER.warning("Sin lenguaje soportado en %s. Omitiendo.", ruta_repo.name)
            return json.dumps({"runs": []})

        LOGGER.info("Lenguaje detectado en %s: %s", ruta_repo.name, lenguaje)

        db_path = self._crear_base_datos(ruta_repo, lenguaje)
        try:
            return self._analizar(db_path, lenguaje, ruta_repo.name)
        finally:
            shutil.rmtree(db_path, ignore_errors=True)

    def parse_sarif(self, sarif_str: str) -> dict:
        try:
            sarif = json.loads(sarif_str)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"SARIF inválido: {error}") from error

        resultado = {
            "total_issues": 0,
            "issues_by_severity": {"error": 0, "warning": 0, "note": 0},
            "issues": [],
        }

        runs = sarif.get("runs", [])
        if not runs:
            return resultado

        for issue_raw in runs[0].get("results", []):
            issue = self._procesar_resultado(issue_raw)
            resultado["issues"].append(issue)
            nivel = issue_raw.get("level", "warning")
            if nivel in resultado["issues_by_severity"]:
                resultado["issues_by_severity"][nivel] += 1
            resultado["total_issues"] += 1

        return resultado

    def save_analysis(self, repo_name: str, analysis: dict) -> Path:
        self.output_path.mkdir(parents=True, exist_ok=True)
        ruta_salida = self.output_path / f"{repo_name}{SUFIJO_CODEQL}"
        ruta_salida.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
        LOGGER.info("CodeQL guardado: %s", ruta_salida.relative_to(self.project_root))
        return ruta_salida

    def run(self):
        repositorios = self.discover_repositories()
        if not repositorios:
            return

        self.codeql_path = shutil.which("codeql")
        if not self.codeql_path:
            raise RuntimeError(MENSAJE_CODEQL_NO_INSTALADO)

        self.temp_dir = Path(tempfile.gettempdir()) / "codeql_analysis"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_path.mkdir(parents=True, exist_ok=True)

        exitosos, errores = 0, 0

        for indice, repo_path in enumerate(repositorios, start=1):
            ruta_repo = self.project_root / repo_path
            LOGGER.info("[%s/%s] Analizando %s", indice, len(repositorios), repo_path)

            try:
                sarif_str = self.run_codeql(repo_path)
                analysis = self.parse_sarif(sarif_str)
                self.save_analysis(ruta_repo.name, analysis)
                LOGGER.info("  -> %s issues encontrados", analysis["total_issues"])
                exitosos += 1
            except Exception as error:
                errores += 1
                parcial = self.output_path / f"{ruta_repo.name}{SUFIJO_CODEQL}"
                if parcial.exists():
                    parcial.unlink()
                LOGGER.error("[%s/%s] Error en %s: %s", indice, len(repositorios), repo_path, error)

        LOGGER.info(
            "Resumen | total=%s | exitosos=%s | errores=%s",
            len(repositorios), exitosos, errores,
        )

    def _detectar_lenguaje(self, ruta_repo: Path) -> str | None:
        conteos: dict[str, int] = {}
        for archivo in ruta_repo.rglob("*"):
            if archivo.is_file():
                lenguaje = EXTENSIONES_LENGUAJE.get(archivo.suffix.lower())
                if lenguaje:
                    conteos[lenguaje] = conteos.get(lenguaje, 0) + 1
        return max(conteos, key=conteos.get) if conteos else None

    def _crear_base_datos(self, ruta_repo: Path, lenguaje: str) -> Path:
        db_path = self.temp_dir / f"{ruta_repo.name}_db"
        comando = [
            self.codeql_path, "database", "create", str(db_path),
            "--language", lenguaje,
            "--source-root", str(ruta_repo),
            "--overwrite",
        ]

        resultado = subprocess.run(comando, capture_output=True, text=True, check=False)

        # Fallback para JavaScript: intentar sin autobuild
        if resultado.returncode != 0 and lenguaje == "javascript":
            LOGGER.warning("Autobuild falló en %s. Intentando con --skip-autobuild...", ruta_repo.name)
            db_path = self.temp_dir / f"{ruta_repo.name}_db_noautobuild"
            comando_retry = comando[:-1] + ["--skip-autobuild", "--overwrite"]
            resultado = subprocess.run(comando_retry, capture_output=True, text=True, check=False)

        if resultado.returncode != 0:
            raise RuntimeError(
                f"No se pudo crear la base de datos CodeQL para {ruta_repo.name}: "
                f"{resultado.stderr.strip()}"
            )

        return db_path

    def _resolver_query_suite(self, lenguaje: str) -> str:
        suite_pattern = f"{lenguaje}-queries/*/codeql-suites/{lenguaje}-security-and-quality.qls"
        # Search in shared location (Docker), user home, and /root fallback
        search_roots = [
            Path("/opt/codeql/packages/codeql"),
            Path.home() / ".codeql" / "packages" / "codeql",
        ]
        for base in search_roots:
            suite_files = list(base.glob(suite_pattern))
            if suite_files:
                return str(suite_files[0])

        return f"codeql/{lenguaje}-queries"

    def _analizar(self, db_path: Path, lenguaje: str, repo_name: str) -> str:
        query_suite = self._resolver_query_suite(lenguaje)
        sarif_path = self.output_path / f"{repo_name}_temp.sarif"

        comando = [
            self.codeql_path, "database", "analyze", str(db_path),
            query_suite,
            "--format=sarifv2.1.0",
            f"--output={sarif_path}",
        ]

        resultado = subprocess.run(comando, capture_output=True, text=True, check=False)

        if resultado.returncode != 0:
            LOGGER.warning(
                "CodeQL analyze retornó código %s en %s: %s",
                resultado.returncode, repo_name, resultado.stderr.strip()[:300],
            )

        if sarif_path.exists():
            return sarif_path.read_text(encoding="utf-8")

        return json.dumps({"version": "2.1.0", "runs": []})

    def _procesar_resultado(self, resultado: dict) -> dict:
        locations = resultado.get("locations", [])
        location = locations[0] if locations else {}
        physical = location.get("physicalLocation", {})
        artifact = physical.get("artifactLocation", {})
        message = resultado.get("message", {})

        return {
            "rule_id": resultado.get("ruleId", "unknown"),
            "level": resultado.get("level", "warning"),
            "message": message.get("text", "") if isinstance(message, dict) else str(message),
            "file": artifact.get("uri", "unknown"),
            "region": physical.get("region", {}),
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analiza código fuente con CodeQL para todos los repositorios."
    )
    parser.add_argument("--repos-path", default=str(RUTA_REPOS_POR_DEFECTO))
    parser.add_argument("--output-path", default=str(RUTA_RESULTADOS_POR_DEFECTO))
    args = parser.parse_args()

    analizador = CodeQLAnalyzer(args.repos_path, args.output_path)
    try:
        analizador.run()
    except Exception as error:
        LOGGER.error("%s", error)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
