"""Storage declarations are not proof of the encoding of individual objects."""
from .models import finding, VERSION_SOURCE


def analyze(crd):
    out = []
    versions = crd["spec"]["versions"]
    names = [v.get("name") for v in versions]
    storage = [v["name"] for v in versions if v.get("storage") is True]
    served = [v["name"] for v in versions if v.get("served") is True]

    def add(id_, state, text, **kw):
        out.append(finding(id_, "storage", state, text, source=VERSION_SOURCE, **kw))

    if len(storage) != 1:
        add("STORAGE-ONE", "FAIL", "Debe existir exactamente una versión storage.", evidence={"storage": storage})
    if not served:
        add("SERVED-NONE", "FAIL", "No hay versiones servidas.")
    if len(storage) == 1 and storage[0] not in served:
        add("STORAGE-NOT-SERVED", "WARN", "La versión storage no se sirve; revisar clientes y conversión.")
    stored = crd.get("status", {}).get("storedVersions")
    if stored is None:
        add("STORED-UNKNOWN", "UNKNOWN", "status.storedVersions no está disponible.", relation="limitation")
    elif not isinstance(stored, list) or any(not isinstance(v, str) for v in stored):
        add("STORED-FORMAT", "FAIL", "storedVersions debe ser una lista de nombres de versión.")
    else:
        missing = [n for n in stored if n not in names]
        if missing or not stored or any(v not in stored for v in storage):
            add("STORED-INCONSISTENT", "FAIL", "Versiones persistidas y declaradas inconsistentes.",
                evidence={"stored_versions": stored, "undeclared_versions": missing, "storage": storage},
                recommendation="Verificar la migración de objetos antes de retirar versiones; no modificar el status sin evidencia.")
        if len(stored) > 1:
            add("STORED-MIGRATION", "WARN", "El status conserva varias versiones de almacenamiento.",
                evidence={"stored_versions": stored},
                recommendation="Auditar la migración; cambiar storage no reescribe los objetos existentes.",
                limitations=["storedVersions es histórico; no prueba que aún existan objetos en cada versión."])
    if len(versions) > 1 and crd["spec"].get("conversion", {}).get("strategy", "None") == "None":
        schemas = [v.get("schema", {}) for v in versions]
        if any(s != schemas[0] for s in schemas[1:]):
            add("CONVERSION-NONE-DIVERGENT", "WARN", "Esquemas diferentes con conversión None.",
                recommendation="Comprobar que los datos funcionan en todas las versiones; None solo cambia apiVersion.")
    if not out:
        add("STORAGE-CONSISTENT", "PASS", "Declaraciones served, storage y storedVersions coherentes.",
            evidence={"served": served, "storage": storage, "stored_versions": stored})
    return out
