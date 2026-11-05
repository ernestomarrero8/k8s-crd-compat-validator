"""Only GET/LIST operations. No shell, manifests, kubeconfig dumps or raw errors."""
import json
from pathlib import Path
import subprocess
from urllib.parse import urlencode, quote

from .version import Version

SERVER_CONFIG = ["config", "view", "--minify", "-o", "jsonpath={.clusters[0].cluster.server}"]


class CollectionError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__({"forbidden": "RBAC insuficiente para la lectura solicitada.",
                          "not_found": "Recurso o API no disponible.",
                          "timeout": "La consulta excedió el timeout.",
                          "kubectl_missing": "kubectl no está disponible.",
                          "invalid_json": "Respuesta JSON inválida.",
                          "command_failed": "Falló la lectura; detalle omitido para proteger credenciales.",
                          "unreachable": "No se pudo alcanzar el API Server. Revisar red/DNS y si el contexto apunta a un clúster eliminado; el diagnóstico no demuestra eliminación.",
                          "query_limit": "Se alcanzó el límite global de consultas.",
                          "invalid_response": "La respuesta no tiene la estructura esperada."}.get(code, code))


def read_json(path):
    # Windows PowerShell 5 redirects UTF-16, PowerShell 7 redirects UTF-8.
    data = Path(path).read_bytes()
    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    try:
        return json.loads(data.decode(encoding))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("Archivo JSON inválido (se admite UTF-8 y UTF-16 con BOM).") from exc


def crd_items(data):
    if not isinstance(data, dict):
        raise ValueError("La entrada debe ser un CRD o una lista JSON de CRDs.")
    if data.get("kind") == "CustomResourceDefinition":
        items = [data]
    elif data.get("kind") in ("List", "CustomResourceDefinitionList") and isinstance(data.get("items"), list):
        items = data["items"]
    else:
        raise ValueError("Se esperaba CustomResourceDefinition, List o CustomResourceDefinitionList.")
    if any(not isinstance(x, dict) or x.get("kind") != "CustomResourceDefinition" for x in items):
        raise ValueError("La lista contiene elementos que no son CRDs.")
    names = [x.get("metadata", {}).get("name") for x in items if isinstance(x.get("metadata", {}), dict)]
    if any(isinstance(n, str) and names.count(n) > 1 for n in names):
        raise ValueError("La entrada contiene nombres de CRD duplicados.")
    return items


class Collector:
    def __init__(self, context=None, timeout=30, max_queries=200, runner=None):
        self.context = context
        self.timeout = timeout
        self.max_queries = max_queries
        self.queries = 0
        self.runner = runner or subprocess.run
        self.cache = {}

    def _run(self, args, json_output=True):
        if not args or args[0] not in ("get", "version", "config") or (args[0] == "config" and args not in (["config", "current-context"], SERVER_CONFIG)):
            raise ValueError("El colector solo admite lecturas get/version y config current-context.")
        if self.queries >= self.max_queries:
            raise CollectionError("query_limit")
        self.queries += 1
        command = ["kubectl", f"--request-timeout={self.timeout}s"]
        if self.context:
            command += ["--context", self.context]
        command += args
        try:
            result = self.runner(command, capture_output=True, text=True, encoding="utf-8",
                                 errors="replace", timeout=self.timeout + 2, check=False, shell=False)
        except FileNotFoundError as exc:
            raise CollectionError("kubectl_missing") from exc
        except subprocess.TimeoutExpired as exc:
            raise CollectionError("timeout") from exc
        except OSError as exc:
            raise CollectionError("command_failed") from exc
        if result.returncode:
            error = result.stderr.lower()
            code = "forbidden" if "forbidden" in error or "unauthorized" in error else (
                "not_found" if "notfound" in error or "not found" in error or "doesn't have a resource type" in error
                else "unreachable" if any(t in error for t in ("no such host", "name or service not known", "connection refused", "unable to connect to the server", "i/o timeout"))
                else "command_failed")
            raise CollectionError(code)
        if not json_output:
            return result.stdout.strip()
        try:
            value = json.loads(result.stdout)
        except (ValueError, RecursionError) as exc:
            raise CollectionError("invalid_json") from exc
        if not isinstance(value, dict):
            raise CollectionError("invalid_response")
        return value

    def current_context(self):
        if not self.context:
            # Pin it once: a later change to the user's active context cannot redirect reads.
            self.context = self._run(["config", "current-context"], json_output=False)
            if not self.context:
                raise CollectionError("invalid_response")
        return self.context

    def version(self):
        data = self._run(["version", "-o", "json"])
        try:
            return Version.parse(data["serverVersion"]["gitVersion"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CollectionError("invalid_response") from exc

    def api_server(self):
        # Project only the endpoint, never export credentials or a kubeconfig body.
        return self._run(SERVER_CONFIG, json_output=False)

    def crds(self):
        return crd_items(self._run(["get", "crds", "-o", "json"]))

    def get(self, resource, name=None, namespace=None, selector=None, all_namespaces=False):
        args = ["get", resource]
        if name:
            args += [name]
        if namespace:
            args += ["--namespace", namespace]
        if all_namespaces:
            args += ["--all-namespaces"]
        if selector:
            args += ["--selector", selector]
        args += ["-o", "json"]
        key = tuple(args)
        if key not in self.cache:
            try:
                self.cache[key] = self._run(args)
            except CollectionError as exc:
                self.cache[key] = exc
        value = self.cache[key]
        if isinstance(value, CollectionError):
            raise value
        return value

    def instances(self, group, version, plural, *, page_size=100, max_pages=5, max_instances=500):
        base = "/apis/" + "/".join(quote(p, safe="") for p in (group, version, plural))
        count, pages, token, versions, objects = 0, 0, "", set(), []
        while pages < max_pages and count < max_instances:
            params = {"limit": min(page_size, max_instances - count)}
            if token:
                params["continue"] = token
            data = self._run(["get", "--raw", base + "?" + urlencode(params)])
            items = data.get("items")
            if not isinstance(items, list) or any(not isinstance(x, dict) for x in items):
                raise CollectionError("invalid_response")
            pages += 1
            accepted = items[:max_instances - count]
            count += len(accepted)
            objects.extend(accepted)
            versions.update(x.get("apiVersion", "missing") for x in accepted)
            token = data.get("metadata", {}).get("continue", "")
            if not isinstance(token, str):
                raise CollectionError("invalid_response")
            if len(accepted) < len(items):
                token = "truncated"
                break
            if not token:
                break
        return {"count_observed": count, "complete": not bool(token), "pages": pages,
                "requested_version": f"{group}/{version}", "response_versions": sorted(versions)}, objects
