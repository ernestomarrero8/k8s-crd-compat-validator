"""Configuration, TLS bundle parsing and read-only service observations."""
import base64
import binascii
import ssl
import re
from urllib.parse import urlsplit
from .collector import CollectionError
from .models import finding, VERSION_SOURCE


def analyze(crd, collector=None):
    out = []

    def add(id_, state, text, **kw):
        out.append(finding(id_, "conversion_webhook", state, text, source=VERSION_SOURCE, **kw))

    conversion = crd["spec"].get("conversion", {})
    strategy = conversion.get("strategy", "None")
    if strategy == "None":
        add("CONVERSION-NONE", "PASS", "Conversión None: no hay dependencia de un webhook.")
        return out
    if strategy != "Webhook":
        add("CONVERSION-STRATEGY", "FAIL", "Estrategia de conversión no reconocida.")
        return out
    webhook = conversion.get("webhook", {})
    review = webhook.get("conversionReviewVersions", [])
    if not isinstance(review, list) or not review or any(not isinstance(v, str) for v in review) or not {"v1", "v1beta1"}.intersection(review):
        add("CONVERSION-REVIEW", "FAIL", "No hay protocolo ConversionReview reconocido en la configuración.")
    else:
        add("CONVERSION-REVIEW", "PASS", "Hay un protocolo declarado reconocido en Kubernetes 1.34/1.35.",
            evidence={"conversion_review_versions": review}, limitations=["No prueba que el servidor webhook implemente ese protocolo."])
    config = webhook.get("clientConfig", {})
    service = config.get("service")
    url = config.get("url")
    if bool(service) == bool(url):
        add("CONVERSION-DESTINATION", "FAIL", "Debe configurarse exactamente un service o url.")
    if url:
        try:
            parsed = urlsplit(url)
            valid = parsed.scheme == "https" and bool(parsed.hostname) and not (parsed.username or parsed.password or parsed.query or parsed.fragment)
            _ = parsed.port
        except (TypeError, ValueError):
            valid = False
        if not valid:
            add("CONVERSION-URL", "FAIL", "La URL debe ser HTTPS sin credenciales, query ni fragmento.")
    service_valid = isinstance(service, dict) and all(isinstance(service.get(k), str) and len(service[k]) <= 63 and re.fullmatch(r"[a-z0-9](?:[-a-z0-9]*[a-z0-9])?", service[k]) for k in ("name", "namespace"))
    if service:
        port = service.get("port", 443)
        if not service_valid or type(port) is not int or not 1 <= port <= 65535 or (service.get("path") and (not isinstance(service["path"], str) or not service["path"].startswith("/"))):
            service_valid = False
            add("CONVERSION-SERVICE", "FAIL", "Referencia a Service, puerto o path inválidos.")
    bundle = config.get("caBundle")
    if bundle:
        try:
            pem = base64.b64decode(bundle, validate=True).decode("ascii")
            ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT).load_verify_locations(cadata=pem)
        except (ValueError, UnicodeError, binascii.Error, ssl.SSLError, TypeError):
            add("CONVERSION-CA", "FAIL", "caBundle no contiene certificados PEM válidos codificados en base64.")
    else:
        add("CONVERSION-CA-SYSTEM", "UNKNOWN", "Sin caBundle: se depende de las raíces de confianza del API Server.", relation="limitation")
    add("CONVERSION-TARGET", "UNKNOWN", "Conversión y TLS en el API Server objetivo no demostrados.", relation="limitation",
        recommendation="Verificar confianza TLS, SAN, expiración, red y conversiones bidireccionales con datos representativos en un entorno aislado.",
        limitations=["Parsear la CA o encontrar endpoints no verifica handshake, cadena, caducidad ni conversión."])
    if service_valid and collector:
        try:
            svc = collector.get("services", service["name"], service["namespace"])
            ports = [p for p in svc.get("spec", {}).get("ports", []) if p.get("port") == service.get("port", 443) and p.get("protocol", "TCP") == "TCP"]
            if not ports:
                add("CONVERSION-SERVICE-PORT", "FAIL", "El Service no publica el puerto TCP del webhook.", validation_type="live")
            if svc.get("spec", {}).get("type") == "ExternalName":
                add("CONVERSION-EXTERNAL-NAME", "UNKNOWN", "Service ExternalName: disponibilidad DNS externa no verificada.", relation="limitation", validation_type="live")
            else:
                slices = collector.get("endpointslices.discovery.k8s.io", namespace=service["namespace"], selector="kubernetes.io/service-name=" + service["name"])
                ready = sum(1 for s in slices.get("items", []) for e in s.get("endpoints", []) if e.get("addresses") and e.get("conditions", {}).get("ready") is not False)
                add("CONVERSION-ENDPOINTS", "PASS" if ready else "WARN", "Observación de endpoints actuales del Service.",
                    evidence={"ready_or_unspecified_endpoints": ready}, validation_type="live",
                    limitations=["Es una observación del clúster actual, no una prueba de disponibilidad futura ni de conectividad."])
        except CollectionError as exc:
            state = "UNKNOWN" if exc.code in ("forbidden", "query_limit") else "ERROR"
            if exc.code == "not_found":
                state = "WARN"
            add("CONVERSION-LIVE", state, str(exc), evidence={"error_code": exc.code}, relation="limitation", validation_type="live")
    elif service_valid:
        add("CONVERSION-OFFLINE", "UNKNOWN", "Service y endpoints no consultados en modo offline.", relation="limitation")
    return out
