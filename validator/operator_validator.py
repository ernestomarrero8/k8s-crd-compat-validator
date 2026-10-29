"""Evidence-based ownership hints and explicitly reviewed vendor support records."""
import hashlib
import re
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import URLError
from .collector import read_json, CollectionError
from .models import finding
from .rule_engine import safe_source
from .version import Version

OLM_SOURCE = "https://olm.operatorframework.io/docs/concepts/crds/clusterserviceversion/"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OperatorCatalog:
    def __init__(self, path=None, verify_sources=False, timeout=10):
        self.entries = read_json(path) if path else []
        self.verify_sources = verify_sources
        self.timeout = timeout
        self.cache = {}
        if not isinstance(self.entries, list):
            raise ValueError("El catálogo de operadores debe ser una lista JSON.")
        required = {"crds", "operator", "operator_version", "kubernetes_min", "kubernetes_max", "source", "source_sha256", "reviewed_on", "evidence"}
        for entry in self.entries:
            if not isinstance(entry, dict) or not required <= entry.keys():
                raise ValueError("Entrada del catálogo incompleta.")
            if not isinstance(entry["crds"], list) or not entry["crds"] or any(not isinstance(c, str) for c in entry["crds"]):
                raise ValueError("El catálogo requiere nombres exactos de CRD.")
            if any(not isinstance(entry[k], str) or not entry[k] for k in required - {"crds"}):
                raise ValueError("Metadatos del catálogo inválidos.")
            if not safe_source(entry["source"]) or not re.fullmatch(r"[0-9a-f]{64}", entry["source_sha256"]):
                raise ValueError("Se requiere fuente HTTPS y SHA256 del documento revisado.")
            if Version.parse(entry["kubernetes_min"]) > Version.parse(entry["kubernetes_max"]):
                raise ValueError("Rango Kubernetes invertido en catálogo.")

    def source_verified(self, entry):
        if not self.verify_sources:
            return None
        url = entry["source"]
        if url not in self.cache:
            try:
                request = Request(url, headers={"User-Agent": "k8s-crd-compat-validator/0.1"})
                with build_opener(NoRedirect).open(request, timeout=self.timeout) as response:
                    content = response.read(2_000_001)
                self.cache[url] = hashlib.sha256(content).hexdigest() if len(content) <= 2_000_000 else None
            except (URLError, OSError, ValueError):
                self.cache[url] = None
        return self.cache[url] == entry["source_sha256"]


def analyze(crd, target, collector=None, catalog=None):
    catalog = catalog or OperatorCatalog()
    out, candidates = [], []
    meta = crd["metadata"]
    labels, annotations = meta.get("labels", {}), meta.get("annotations", {})
    name = meta["name"]
    label_name, label_version = labels.get("app.kubernetes.io/name"), labels.get("app.kubernetes.io/version")
    if label_name:
        candidates.append({"name": label_name, "version": label_version, "basis": "crd_labels", "confidence": "hint"})
    release, namespace = annotations.get("meta.helm.sh/release-name"), annotations.get("meta.helm.sh/release-namespace")
    if release:
        candidates.append({"name": release, "version": None, "basis": "helm_release", "confidence": "hint"})
    if collector:
        try:
            csvs = collector.get("clusterserviceversions.operators.coreos.com", all_namespaces=True)
            for csv in csvs.get("items", []):
                spec = csv.get("spec", {})
                owned = spec.get("customresourcedefinitions", {}).get("owned", [])
                if any(o.get("name") == name for o in owned):
                    candidates.append({"name": spec.get("displayName") or csv.get("metadata", {}).get("name"),
                                       "version": spec.get("version"), "basis": "olm_owned", "confidence": "declared_owner",
                                       "min_kube_version": spec.get("minKubeVersion")})
        except CollectionError as exc:
            out.append(finding("OPERATOR-OLM", "operator", "UNKNOWN" if exc.code in ("forbidden", "not_found", "query_limit") else "ERROR", str(exc),
                               evidence={"error_code": exc.code}, source=OLM_SOURCE, relation="limitation", validation_type="live"))
        if release and namespace:
            try:
                # Narrow Helm query; never collect pod env, Secrets or logs into reports.
                deployments = collector.get("deployments.apps", namespace=namespace, selector="app.kubernetes.io/instance=" + release)
                for deploy in deployments.get("items", []):
                    dmeta = deploy.get("metadata", {})
                    dlabels = dmeta.get("labels", {})
                    candidates.append({"name": dlabels.get("app.kubernetes.io/name") or dmeta.get("name"),
                                       "version": dlabels.get("app.kubernetes.io/version"), "basis": "helm_deployment", "confidence": "hint"})
            except CollectionError as exc:
                out.append(finding("OPERATOR-DEPLOYMENT", "operator", "UNKNOWN" if exc.code in ("forbidden", "query_limit", "not_found") else "ERROR", str(exc),
                                   evidence={"error_code": exc.code}, relation="limitation", validation_type="live"))
    out.append(finding("OPERATOR-IDENTITY", "operator", "PASS" if candidates else "UNKNOWN", "Candidatos a operador responsable.",
                       evidence={"candidates": candidates}, relation="documented" if candidates else "limitation",
                       limitations=["Labels y Helm son indicios; un release o chart puede no identificar la versión del controlador."]))
    # Conflicting identity/version evidence is deliberately not resolved by picking the first entry.
    entries = [e for e in catalog.entries if name in e["crds"] and any(c["name"] == e["operator"] and c["version"] == e["operator_version"] for c in candidates)]
    if len(entries) != 1:
        out.append(finding("OPERATOR-SUPPORT", "operator", "UNKNOWN", "No hay una única matriz revisada que coincida con operador, versión y CRD.", relation="limitation",
                           recommendation="Obtener la matriz oficial del proveedor y registrar evidencia en --operator-catalog; no inferir soporte por Running."))
    else:
        entry = entries[0]
        verified = catalog.source_verified(entry)
        supported = Version.parse(entry["kubernetes_min"]) <= target <= Version.parse(entry["kubernetes_max"])
        state = "UNKNOWN" if verified is False else "PASS" if supported else "WARN"
        out.append(finding("OPERATOR-SUPPORT", "operator", state,
                           "Evaluación del rango documentado en el catálogo revisado.", source=entry["source"], relation="documented",
                           evidence={k: entry[k] for k in ("operator", "operator_version", "kubernetes_min", "kubernetes_max", "reviewed_on", "evidence", "source_sha256")} | {"source_hash_verified_online": verified, "target_in_range": supported},
                           limitations=["La matriz es curada por el usuario: el programa no interpreta ni inventa soporte a partir de HTML.",
                                        "Fuera del rango documentado es soporte no acreditado, no una incompatibilidad técnica demostrada."],
                           recommendation="Si el objetivo queda fuera del rango, solicitar confirmación al proveedor o actualizar el operador."))
    return out
