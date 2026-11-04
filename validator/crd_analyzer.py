"""Combine independent observations without promoting uncertainty to compatibility."""
import re
from . import schema_validator, storage_validator, conversion_validator, operator_validator
from .collector import CollectionError
from .models import finding, aggregate, SEVERITIES
from .product_link import product_finding, unmapped_finding

DNS_LABEL = re.compile(r"[a-z0-9](?:[-a-z0-9]*[a-z0-9])?")
DNS_SUBDOMAIN = re.compile(r"[a-z0-9](?:[-a-z0-9.]*[a-z0-9])?")


def structure(crd):
    errors = []
    for key in ("metadata", "spec", "status"):
        if not isinstance(crd.get(key, {}), dict):
            errors.append(key)
    if errors:
        return errors
    meta, spec = crd.get("metadata", {}), crd.get("spec", {})
    names = spec.get("names", {})
    if not isinstance(names, dict):
        return ["spec.names"]
    group, plural = spec.get("group"), names.get("plural")
    if not isinstance(group, str) or not DNS_SUBDOMAIN.fullmatch(group) or "." not in group or any(not DNS_LABEL.fullmatch(p) for p in group.split(".")):
        errors.append("spec.group")
    if not isinstance(plural, str) or not DNS_LABEL.fullmatch(plural):
        errors.append("spec.names.plural")
    if not isinstance(names.get("kind"), str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", names["kind"]):
        errors.append("spec.names.kind")
    if meta.get("name") != f"{plural}.{group}":
        errors.append("metadata.name")
    for key in ("labels", "annotations"):
        values = meta.get(key, {})
        if not isinstance(values, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in values.items()):
            errors.append("metadata." + key)
    if spec.get("scope") not in ("Namespaced", "Cluster"):
        errors.append("spec.scope")
    versions = spec.get("versions")
    if not isinstance(versions, list) or not versions:
        errors.append("spec.versions")
    else:
        seen = set()
        for i, version in enumerate(versions):
            path = f"spec.versions[{i}]"
            if not isinstance(version, dict):
                errors.append(path)
                continue
            name = version.get("name")
            if not isinstance(name, str) or not DNS_LABEL.fullmatch(name) or name in seen:
                errors.append(path + ".name")
            else:
                seen.add(name)
            if any(type(version.get(k)) is not bool for k in ("served", "storage")):
                errors.append(path + ".served/storage")
            for key in ("schema", "subresources"):
                if not isinstance(version.get(key, {}), dict):
                    errors.append(path + "." + key)
    conversion = spec.get("conversion", {})
    if not isinstance(conversion, dict):
        errors.append("spec.conversion")
    else:
        webhook = conversion.get("webhook", {})
        if not isinstance(webhook, dict) or not isinstance(webhook.get("clientConfig", {}), dict):
            errors.append("spec.conversion.webhook")
        elif "service" in webhook.get("clientConfig", {}) and not isinstance(webhook["clientConfig"]["service"], dict):
            errors.append("spec.conversion.webhook.clientConfig.service")
    conditions = crd.get("status", {}).get("conditions", [])
    if not isinstance(conditions, list) or any(not isinstance(c, dict) for c in conditions):
        errors.append("status.conditions")
    return errors


def analyze_instances(crd, collector, options):
    if not collector:
        return [finding("INSTANCES-OFFLINE", "instances", "UNKNOWN", "No se consultan instancias en modo offline.", relation="limitation")]
    out = []
    spec = crd["spec"]
    for version in spec["versions"]:
        if not version["served"]:
            continue
        try:
            summary, objects = collector.instances(spec["group"], version["name"], spec["names"]["plural"], **options)
            issue_count, samples = 0, []
            schema = version.get("schema", {}).get("openAPIV3Schema", {})
            for obj in objects:
                issues = schema_validator.instance_issues(obj, schema)
                if issues:
                    issue_count += 1
                    samples.extend(issues[:max(0, 10 - len(samples))])
            summary.update({"objects_with_possible_schema_issues": issue_count, "issue_samples": samples,
                            "persisted_versions": "UNKNOWN", "count_scope": "per_requested_version_do_not_sum"})
            mismatch = any(v != summary["requested_version"] for v in summary["response_versions"])
            state = "WARN" if issue_count or mismatch or not summary["complete"] else "PASS"
            out.append(finding("INSTANCES-READ", "instances", state, "Lectura paginada y validación parcial de respuestas de la API.",
                               evidence=summary, validation_type="live",
                               limitations=["La versión de respuesta no identifica la versión en etcd.",
                                            "No ejecuta CEL, regex, validación de updates ni admisión. Un valor histórico puede estar protegido por ratcheting.",
                                            "Los mismos objetos pueden aparecer al consultar distintas versiones; no sumar esos conteos."],
                               recommendation="Revisar hallazgos con el esquema de la versión solicitada y probar transiciones en un entorno aislado."))
        except CollectionError as exc:
            out.append(finding("INSTANCES-READ", "instances", "UNKNOWN" if exc.code in ("forbidden", "query_limit") else "ERROR", str(exc),
                               evidence={"error_code": exc.code, "requested_version": version["name"]}, validation_type="live", relation="limitation"))
    return out


def analyze_target(crd, target_collector, target_crds, target_error):
    if target_error:
        return [finding("TARGET-READ", "target_validation", "UNKNOWN" if target_error.code in ("forbidden", "query_limit") else "ERROR",
                        str(target_error), relation="limitation", validation_type="target_read", evidence={"error_code": target_error.code})]
    match = target_crds.get(crd["metadata"]["name"])
    if not match:
        return [finding("TARGET-NOT-INSTALLED", "target_validation", "UNKNOWN", "El CRD no está instalado en el clúster objetivo.",
                        relation="limitation", validation_type="target_read", recommendation="Preparar manualmente el entorno aislado si se necesitan pruebas de admisión o conversión.")]
    same = match.get("spec") == crd["spec"]
    out = [finding("TARGET-DEFINITION", "target_validation", "PASS" if same else "UNKNOWN", "Comparación de definición con el CRD instalado en el objetivo.",
                   evidence={"same_spec": same}, relation="tested", validation_type="target_read",
                   limitations=["La presencia de una definición no prueba aceptación de escrituras nuevas ni reconciliación."])]
    if same:
        try:
            for v in crd["spec"]["versions"]:
                if v["served"]:
                    data = target_collector._run(["get", "--raw", f"/apis/{crd['spec']['group']}/{v['name']}"])
                    present = any(r.get("name") == crd["spec"]["names"]["plural"] for r in data.get("resources", []))
                    out.append(finding("TARGET-DISCOVERY", "target_validation", "PASS" if present else "WARN", "Discovery del recurso en el API Server objetivo.",
                                       evidence={"version": v["name"], "resource_present": present}, relation="tested", validation_type="target_read"))
        except CollectionError as exc:
            out.append(finding("TARGET-DISCOVERY", "target_validation", "UNKNOWN" if exc.code in ("forbidden", "query_limit") else "ERROR", str(exc),
                               evidence={"error_code": exc.code}, relation="limitation", validation_type="target_read"))
    out.append(finding("TARGET-WRITE-UNTESTED", "target_validation", "UNKNOWN", "Admisión, updates, CEL y conversiones de escritura no ejecutados.",
                       relation="limitation", validation_type="target_read",
                       limitations=["Este programa no realiza escrituras, ni siquiera dry-run; las pruebas mutantes requieren otro procedimiento autorizado."]))
    return out


def analyze(crd, current, target, engine, collector=None, catalog=None, include_instances=False,
            instance_options=None, target_collector=None, target_crds=None, target_error=None, coverage=None, product=None, product_mode=False):
    from .coverage import CoverageCatalog
    coverage = coverage or CoverageCatalog()
    errors = structure(crd)
    name = crd.get("metadata", {}).get("name", "<sin nombre>") if isinstance(crd.get("metadata"), dict) else "<sin nombre>"
    if not isinstance(name, str):
        name = "<nombre inválido>"
    findings = []
    if errors:
        findings.append(finding("STRUCTURE-INVALID", "structure", "FAIL", "La definición contiene campos estructurales inválidos.",
                                evidence={"paths": errors}, limitations=["Las comprobaciones dependientes de estos campos no pudieron ejecutarse."]))
    else:
        findings.append(finding("STRUCTURE-BASIC", "structure", "PASS", "Identidad, scope, nombres y versiones con estructura válida."))
        if crd.get("apiVersion") != "apiextensions.k8s.io/v1":
            findings.append(finding("CRD-REPRESENTATION", "structure", "UNKNOWN", "El analizador espera una exportación apiextensions.k8s.io/v1.", relation="limitation"))
        if crd["spec"].get("preserveUnknownFields") is True:
            findings.append(finding("SCHEMA-LEGACY-PRESERVE", "schema", "WARN", "CRD heredado con spec.preserveUnknownFields: true.",
                                    recommendation="Preparar un esquema estructural antes de modificar el CRD; comprobar pruning.",
                                    limitations=["Puede ser un CRD heredado válido en almacenamiento; no se atribuye su origen al upgrade."]))
        conditions = crd.get("status", {}).get("conditions", [])
        if not conditions:
            findings.append(finding("CONDITIONS-MISSING", "structure", "UNKNOWN", "Sin condiciones del CRD para verificar su establecimiento.", relation="limitation"))
        for condition in conditions:
            typ, state = condition.get("type"), condition.get("status")
            if (typ in ("NonStructuralSchema", "Terminating") and state == "True") or (typ in ("Established", "NamesAccepted") and state == "False"):
                findings.append(finding("CRD-CONDITION", "structure", "WARN", "El API Server informa una condición problemática preexistente.",
                                        evidence={"type": typ, "status": state}, validation_type="observed_status"))
        checks = [lambda: storage_validator.analyze(crd), lambda: schema_validator.analyze(crd),
                  lambda: conversion_validator.analyze(crd, collector, coverage.protocols(target)),
                  lambda: [product_finding(product)] if product else [unmapped_finding()] if product_mode else operator_validator.analyze(crd, target, collector, catalog), lambda: engine.evaluate(crd, current, target)]
        if include_instances:
            checks.append(lambda: analyze_instances(crd, collector, instance_options or {}))
        if target_collector:
            checks.append(lambda: analyze_target(crd, target_collector, target_crds or {}, target_error))
        for check in checks:
            try:
                findings.extend(check())
            except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
                findings.append(finding("CHECK-INPUT-ERROR", "execution", "ERROR", "Una comprobación encontró una estructura no interpretable.",
                                        relation="limitation", limitations=["Detalle omitido para no publicar datos del recurso. Revisar la definición de entrada."]))
    if not include_instances:
        findings.append(finding("INSTANCES-NOT-REQUESTED", "instances", "UNKNOWN", "Instancias no inspeccionadas; usar --include-instances para lectura limitada.", relation="limitation"))
    return {"name": name, "status": aggregate(findings), "severity": max((f.severity for f in findings), key=SEVERITIES.index),
            "findings": [f.to_dict() for f in findings]}
