import argparse
from pathlib import Path
import sys
from . import __version__
from .collector import Collector, CollectionError, read_json, crd_items
from .coverage import CoverageCatalog
from . import pluto
from .version import Version, upgrade_path
from .rule_engine import RuleEngine
from .operator_validator import OperatorCatalog
from .crd_analyzer import analyze
from .models import finding, STATES
from .report_generator import build_report, write_reports
from .platform_catalog import PlatformCatalog
from .platform_analyzer import analyze as analyze_platform
from .readiness import score, load_config
from .cluster_identity import collect_identity
from .product_link import owner_result, annotate
from .platform_discovery import DEFAULT_PLATFORM_LIMIT


def positive(value):
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Debe ser un entero positivo.") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("Debe ser un entero positivo.")
    return number


def parser():
    p = argparse.ArgumentParser(description="Analiza riesgos de CRDs durante un upgrade Kubernetes; solo lectura.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--target", "--target-version", required=True, help="Versión Kubernetes objetivo, por ejemplo 1.35.9")
    p.add_argument("--current", help="Versión actual; obligatoria en offline, validada contra servidor en LIVE")
    p.add_argument("--context", help="Contexto de origen; por defecto el activo")
    p.add_argument("--input", type=Path, help="Exportación JSON de CRDs; activa modo offline sin red")
    p.add_argument("--output", type=Path, default=Path("reports"), help="Directorio de reportes (default: reports)")
    p.add_argument("--format", choices=("json", "markdown", "md", "html", "all"), default="all")
    p.add_argument("--include-instances", action="store_true", help="Lectura limitada de Custom Resources")
    p.add_argument("--coverage-path", type=Path, help="Catálogo JSON de cobertura y protocolos revisados")
    p.add_argument("--pluto-timeout", type=positive, default=120, help="Timeout total de Pluto en segundos")
    p.add_argument("--rules-path", type=Path, help="Archivo/directorio JSON; agrega reglas a las incluidas")
    p.add_argument("--operator-catalog", type=Path, help="Matriz de soporte revisada con fuentes y versiones exactas")
    p.add_argument("--platform-catalog", "--support-catalog", type=Path, help="Directorio de matrices oficiales de plataformas (reemplaza las incluidas)")
    p.add_argument("--platform-input", type=Path, help="Snapshot JSON de inventario de plataformas; permite análisis offline")
    p.add_argument("--platform-limit", type=positive, default=DEFAULT_PLATFORM_LIMIT, help="Máximo de seguridad por fuente (default 20000); Pods se leen en páginas de 500")
    p.add_argument("--cluster-timeout", type=positive, default=1800, help="Presupuesto total de lectura LIVE por clúster, segundos")
    p.add_argument("--full-platform-evidence", action="store_true", help="Conservar en JSON toda la evidencia permitida del inventario examinado; el HTML usa resúmenes de Istio")
    p.add_argument("--detectors-path", type=Path, help="Aliases explícitos de repositorios/charts para productos conocidos")
    p.add_argument("--readiness-config", type=Path, help="Configuración readiness JSON o YAML de escalares documentados")
    p.add_argument("--verify-sources", action="store_true", help="Consulta documentos HTTPS del catálogo y verifica SHA256; solo LIVE")
    p.add_argument("--target-context", help="Clúster objetivo: comparar CRDs preinstalados y discovery, sin escrituras")
    p.add_argument("--verbose", action="store_true", help="Mostrar conteos y reglas; nunca salida cruda de kubectl")
    p.add_argument("--timeout", type=positive, default=30, help="Timeout por consulta, segundos (default: 30)")
    p.add_argument("--max-queries", type=positive, default=200, help="Máximo de invocaciones por contexto (default: 200)")
    p.add_argument("--page-size", type=positive, default=100)
    p.add_argument("--max-pages", type=positive, default=5, help="Páginas por CRD y versión")
    p.add_argument("--max-instances", type=positive, default=500, help="Objetos por CRD y versión")
    p.add_argument("--fail-on", default="FAIL,ERROR", help="Estados exactos separados por coma, o NONE; default FAIL,ERROR. ERROR siempre devuelve 2.")
    return p


def exit_code(report, fail_on):
    findings = report["global_findings"] + [f for c in report["crds"] for f in c["findings"]]
    states = {f["status"] for f in findings}
    if "ERROR" in states:
        return 2
    if report.get("readiness", {}).get("required_inventory_missing"):
        return 2
    if report.get("readiness", {}).get("decision") == "INCOMPLETE":
        return 2
    return 1 if states.intersection(fail_on) else 0


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    try:
        target = Version.parse(args.target)
        declared_current = Version.parse(args.current) if args.current else None
        fail_on = set(args.fail_on.upper().split(","))
        if fail_on == {"NONE"}:
            fail_on = set()
        elif not fail_on <= set(STATES):
            raise ValueError("--fail-on acepta PASS,WARN,FAIL,UNKNOWN,ERROR o NONE.")
        if args.input and (args.context or args.target_context or args.verify_sources):
            raise ValueError("Offline no permite --context, --target-context ni --verify-sources; no se usa red.")
        if args.input and not declared_current:
            raise ValueError("El modo offline requiere --current.")
        if args.verify_sources and not args.operator_catalog:
            raise ValueError("--verify-sources requiere --operator-catalog.")
        coverage = CoverageCatalog(args.coverage_path)
        engine = RuleEngine(args.rules_path)
        catalog = OperatorCatalog(args.operator_catalog, args.verify_sources, args.timeout)
        platform_catalog = PlatformCatalog(args.platform_catalog, args.detectors_path)
        readiness_config = load_config(args.readiness_config)
        collector = None
        if args.input:
            current = declared_current
            cluster = "offline:" + args.input.name
            crds = crd_items(read_json(args.input))
        else:
            collector = Collector(args.context, args.timeout, args.max_queries, total_timeout=args.cluster_timeout)
            cluster = collector.current_context()
            current = collector.version()
            if declared_current and declared_current != current:
                raise ValueError("--current no coincide con la versión del servidor detectada.")
            crds = collector.crds()
        path = upgrade_path(current, target)
        global_findings = []
        if path["skips_minors"]:
            global_findings.append(finding("UPGRADE-MINOR-JUMP", "upgrade_path", "WARN", "El objetivo salta versiones minor.",
                evidence=path, relation="upgrade", recommendation="Planificar y validar cada salto y las restricciones del proveedor del clúster."))
        global_findings.append(coverage.assess(current, target))
        if not crds:
            global_findings.append(finding("CRD-INVENTORY-EMPTY", "inventory", "UNKNOWN", "No se encontraron CRDs en la entrada.", relation="limitation"))
        target_collector, target_crds, target_error = None, {}, None
        if args.target_context:
            if args.target_context == cluster:
                raise ValueError("--target-context debe ser distinto del contexto de origen.")
            target_collector = Collector(args.target_context, args.timeout, args.max_queries, total_timeout=collector.remaining_timeout(args.cluster_timeout))
            # A version mismatch aborts: observations of another version cannot validate the requested target.
            detected = target_collector.version()
            if detected != target:
                raise ValueError("El servidor de --target-context no ejecuta exactamente la versión objetivo.")
            try:
                target_crds = {c["metadata"]["name"]: c for c in target_collector.crds()}
            except CollectionError as exc:
                target_error = exc
        options = {"page_size": args.page_size, "max_pages": args.max_pages, "max_instances": args.max_instances}
        try:
            platform, platform_findings = analyze_platform(collector, crds, current, target, platform_catalog,
                read_json(args.platform_input) if args.platform_input else None, args.platform_limit, args.full_platform_evidence)
        except (KeyError, TypeError, AttributeError):
            failure = finding("PLATFORM-DISCOVERY-ERROR", "operator_compatibility", "ERROR",
                "No se pudo interpretar una respuesta del inventario de plataformas; el análisis de CRDs se conserva.", relation="limitation")
            platform = {"products": [], "discovery": failure.to_dict(), "aks": {"detected": False, "limitations": [failure.description]}, "catalog": platform_catalog.provenance()}
            platform_findings = [failure]
        global_findings.extend(platform_findings)
        results = []
        for crd in crds:
            product = owner_result(crd, platform, platform_catalog.ownership) if isinstance(crd.get("spec"), dict) and isinstance(crd.get("metadata"), dict) else None
            # Explicit legacy catalog keeps its extra independent ownership checks.
            linked = product if not args.operator_catalog else None
            result = analyze(crd, current, target, engine, collector, catalog, args.include_instances,
                             options, target_collector, target_crds, target_error, coverage, linked, not bool(args.operator_catalog))
            results.append(annotate(result, linked))
            if args.verbose:
                print(f"CRD {len(results)}/{len(crds)}: {result['status']} ({len(result['findings'])} hallazgos)", file=sys.stderr)
        identity = collect_identity(collector, platform, cluster)
        queries = (collector.queries if collector else 0) + (target_collector.queries if target_collector else 0)
        try:
            pluto_timeout = collector.remaining_timeout(args.pluto_timeout) if collector else args.pluto_timeout
            pluto_result, pluto_finding = pluto.run(cluster, target, pluto_timeout, offline=bool(args.input))
        except CollectionError:
            pluto_result = {"status": "ERROR", "executed": False, "exit_code": None, "stdout": "", "command": [],
                "message": "Pluto no se inició: se agotó el timeout global del clúster."}
            pluto_finding = finding("CLUSTER-TIMEOUT", "execution", "ERROR", pluto_result["message"], evidence={"error_code": "cluster_timeout"})
        global_findings.append(pluto_finding)
        report = build_report(cluster, current, target, path, results, global_findings, queries, args.target_context)
        report["pluto"] = pluto_result
        report["platform"] = platform
        report["cluster_identity"] = identity["cluster_identity"]
        report["cluster_identity_evidence"] = identity
        report["readiness"] = score(report, readiness_config)
        code = exit_code(report, fail_on)
        report["validator"] = {"status": "ERROR" if code == 2 else "FAIL" if code == 1 else report["overall_status"],
            "exit_code": code, "decision": report["readiness"]["decision"], "exit_policy": args.fail_on}
        report["summary"]["platform_products"] = len(platform["products"])
        report["summary"]["unknown_products"] = platform.get("support_coverage", {}).get("unknown_products")
        report["summary"]["unknown_product_percentage"] = platform.get("support_coverage", {}).get("unknown_percentage")
        report["summary"]["crds_linked_to_product"] = sum("product_compatibility" in r for r in results)
        report["summary"]["crds_without_product"] = sum("product_compatibility" not in r for r in results)
        report["summary"]["platform_states"] = {s: sum(p["status"] == s for p in platform["products"]) for s in STATES}
        report["summary"]["support_policy_blocks"] = sum(p.get("support_status") == "FAIL_SUPPORT_POLICY" for p in platform["products"])
        report["summary"]["technical_crd_failures"] = sum(c.get("technical_failure_demonstrated", False) for c in report["crds"])
        report["knowledge"] = {"coverage_catalog_version": coverage.data["catalog_version"], "coverage_sha256": coverage.sha256, "rule_catalogs": engine.provenance()}
        written = write_reports(report, args.output, "markdown" if args.format == "md" else args.format)
        print(f"k8s-crd-compat-validator {__version__} | Kubernetes {current} -> {target} | CRDs: {len(results)} | Estado: {report['overall_status']}")
        print(" | ".join(f"{s}: {n}" for s, n in report["summary"]["states"].items()))
        print(f"Plataformas: {len(platform['products'])} | Readiness: {report['readiness']['score']}/100 | {report['readiness']['decision']}")
        print(f"Cobertura de evidencia: {report['readiness']['evidence_coverage']}% | Método de score: {report['readiness']['scoring_version']}")
        print(f"Bloqueos de soporte: {report['summary']['support_policy_blocks']} | Defectos técnicos de CRDs: {report['summary']['technical_crd_failures']}")
        print("PASS acredita comprobaciones realizadas; no garantiza compatibilidad completa.")
        for file in written:
            print(f"Reporte: {file.resolve()}")
        return code
    except CollectionError as exc:
        print(f"ERROR [{exc.code}]: {exc}", file=sys.stderr)
        return 2
    except (ValueError, OSError, RecursionError) as exc:
        # OSError filenames may include sensitive paths; avoid dumping the exception.
        message = str(exc) if isinstance(exc, ValueError) else "No se pudo leer/escribir el archivo o se excedió la profundidad de entrada."
        print(f"ERROR: {message}", file=sys.stderr)
        return 2
