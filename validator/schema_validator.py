"""Conservative OpenAPI checks, not a replacement for API machinery or CEL."""
from .models import finding

TYPES = {"object", "array", "string", "number", "integer", "boolean"}


def schema_nodes(schema, path="$", depth=0):
    """Walk structural nodes only; junctors are handled against their parent."""
    if depth > 80:
        raise ValueError("Schema supera la profundidad máxima de 80.")
    yield path, schema
    if not isinstance(schema, dict):
        return
    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        for key, value in properties.items():
            yield from schema_nodes(value, f"{path}.properties.{key}", depth + 1)
    for key in ("items", "additionalProperties"):
        if isinstance(schema.get(key), dict):
            yield from schema_nodes(schema[key], f"{path}.{key}", depth + 1)


def analyze(crd):
    out = []

    def add(id_, state, text, path, **kw):
        out.append(finding(id_, "schema", state, text, evidence={"path": path}, **kw))

    def logical_checks(branch, core, path, intstring=False):
        if not isinstance(branch, dict):
            add("SCHEMA-JUNCTOR", "FAIL", "La rama lógica debe ser un objeto.", path)
            return
        forbidden = {"description", "type", "default", "additionalProperties", "nullable"} & branch.keys()
        if forbidden:
            add("SCHEMA-JUNCTOR-STRUCTURE", "FAIL", "Definición estructural dentro de una rama lógica.", path)
        for key, child in branch.get("properties", {}).items():
            if key not in core.get("properties", {}):
                add("SCHEMA-JUNCTOR-PROPERTY", "FAIL", "Campo lógico sin definición fuera de la rama.", path)
            else:
                logical_checks(child, core["properties"][key], path + ".properties." + key)
        if "items" in branch:
            if "items" not in core:
                add("SCHEMA-JUNCTOR-ITEMS", "FAIL", "items lógico sin definición estructural.", path)
            else:
                logical_checks(branch["items"], core["items"], path + ".items")
        check_junctors(branch, core, path, intstring)

    def check_junctors(node, core, path, intstring):
        special = [{"type": "integer"}, {"type": "string"}]
        for key in ("anyOf", "oneOf", "allOf", "not"):
            if key not in node:
                continue
            if intstring and key == "anyOf" and node[key] == special:
                continue
            branches = [node[key]] if key == "not" else node[key]
            if not isinstance(branches, list):
                add("SCHEMA-JUNCTOR", "FAIL", "El combinador debe contener una lista.", path)
                continue
            for i, branch in enumerate(branches):
                # Only the exact first allOf/anyOf int-or-string exception is allowed.
                exempt = intstring and key == "allOf" and i == 0 and branch == {"anyOf": special}
                if not exempt:
                    logical_checks(branch, core, f"{path}.{key}[{i}]")

    for version in crd["spec"]["versions"]:
        root = f"spec.versions[{version['name']}].schema.openAPIV3Schema"
        schema = version.get("schema", {}).get("openAPIV3Schema")
        if not isinstance(schema, dict):
            add("SCHEMA-MISSING", "FAIL", "Falta un esquema OpenAPI por versión.", root)
            continue
        if schema.get("type") != "object":
            add("SCHEMA-ROOT", "FAIL", "El esquema raíz debe tener type: object.", root)
        before = len(out)
        for path, node in schema_nodes(schema, root):
            if not isinstance(node, dict):
                add("SCHEMA-NODE", "FAIL", "El nodo debe ser un objeto OpenAPI.", path)
                continue
            typ = node.get("type")
            exempt = node.get("x-kubernetes-int-or-string") is True or node.get("x-kubernetes-preserve-unknown-fields") is True
            if typ not in TYPES and not (typ is None and exempt):
                add("SCHEMA-TYPE", "FAIL", "Tipo ausente o no válido en un nodo estructural.", path)
            if typ == "array" and not isinstance(node.get("items"), dict):
                add("SCHEMA-ITEMS", "FAIL", "Un array requiere un esquema items.", path)
            properties = node.get("properties", {})
            if not isinstance(properties, dict):
                add("SCHEMA-PROPERTIES", "FAIL", "properties debe ser un objeto.", path)
                continue
            required = node.get("required", [])
            if not isinstance(required, list) or any(not isinstance(x, str) for x in required) or len(set(required)) != len(required):
                add("SCHEMA-REQUIRED", "FAIL", "required debe ser una lista de nombres únicos.", path)
            elif any(k not in properties for k in required) and not node.get("additionalProperties") and not node.get("x-kubernetes-preserve-unknown-fields"):
                add("SCHEMA-REQUIRED-UNDECLARED", "WARN", "required menciona campos sin esquema explícito.", path,
                    recommendation="Revisar el efecto de pruning y campos requeridos.")
            for lower, upper in (("minimum", "maximum"), ("minLength", "maxLength"), ("minItems", "maxItems"), ("minProperties", "maxProperties")):
                if lower in node and upper in node:
                    if isinstance(node[lower], (int, float)) and isinstance(node[upper], (int, float)) and node[lower] > node[upper]:
                        add("SCHEMA-BOUNDS", "FAIL", "Límites contradictorios en el esquema.", path)
            for extension in ("x-kubernetes-int-or-string", "x-kubernetes-embedded-resource"):
                if extension in node and not isinstance(node[extension], bool):
                    add("SCHEMA-EXTENSION", "FAIL", "La extensión debe ser booleana.", path + "." + extension)
            if "x-kubernetes-preserve-unknown-fields" in node and node["x-kubernetes-preserve-unknown-fields"] is not True:
                add("SCHEMA-PRESERVE", "FAIL", "preserve-unknown-fields solo puede ser true o estar ausente.", path)
            if node.get("x-kubernetes-preserve-unknown-fields") is True:
                add("SCHEMA-UNPRUNED", "PASS", "Este nodo conserva campos desconocidos; no implica incompatibilidad.", path,
                    limitations=["Los campos sin esquema no pueden validarse estáticamente."])
            if node.get("x-kubernetes-embedded-resource") and typ != "object":
                add("SCHEMA-EMBEDDED", "FAIL", "embedded-resource requiere type: object.", path)
            list_type = node.get("x-kubernetes-list-type")
            if list_type is not None:
                if typ != "array" or list_type not in ("atomic", "set", "map"):
                    add("SCHEMA-LIST-TYPE", "FAIL", "Extensión list-type incompatible con el tipo del nodo.", path)
                if list_type == "map":
                    keys = node.get("x-kubernetes-list-map-keys")
                    items = node.get("items", {})
                    props = items.get("properties", {}) if isinstance(items, dict) else {}
                    if not isinstance(keys, list) or not keys or any(not isinstance(k, str) for k in keys):
                        add("SCHEMA-MAP-KEYS", "FAIL", "Una lista map requiere claves explícitas.", path)
                    elif items.get("type") != "object" or any(k not in props or props[k].get("type") not in ("string", "integer", "number", "boolean") or props[k].get("nullable") is True or (k not in items.get("required", []) and "default" not in props[k]) for k in keys):
                        add("SCHEMA-MAP-KEYS", "FAIL", "Las claves map deben ser escalares, no nulas y requeridas o con default.", path)
                if list_type == "set" and isinstance(node.get("items"), dict):
                    item = node["items"]
                    if item.get("type") == "object" and item.get("x-kubernetes-map-type") != "atomic":
                        add("SCHEMA-SET-ATOMIC", "FAIL", "Los objetos de una lista set deben ser atomic.", path)
            if "x-kubernetes-list-map-keys" in node and list_type != "map":
                add("SCHEMA-MAP-KEYS", "FAIL", "list-map-keys requiere list-type: map.", path)
            map_type = node.get("x-kubernetes-map-type")
            if map_type is not None and (typ != "object" or map_type not in ("atomic", "granular")):
                add("SCHEMA-MAP-TYPE", "FAIL", "Extensión map-type no válida.", path)
            cel = node.get("x-kubernetes-validations")
            if cel is not None:
                if not isinstance(cel, list) or any(not isinstance(r, dict) or not isinstance(r.get("rule"), str) or not r["rule"].strip() for r in cel):
                    add("SCHEMA-CEL-FORMAT", "FAIL", "CEL requiere una lista de reglas no vacías.", path)
                elif cel:
                    add("SCHEMA-CEL-UNVERIFIED", "UNKNOWN", "CEL detectado; compilación, coste y transición no verificados.", path,
                        relation="limitation", recommendation="Probar creación y actualización de objetos representativos en el API Server objetivo.",
                        limitations=["No se ejecuta CEL ni se publican expresiones o valores de recursos."])
            check_junctors(node, node, path, node.get("x-kubernetes-int-or-string") is True)
        metadata = schema.get("properties", {}).get("metadata", {})
        if isinstance(metadata, dict) and any(k not in ("name", "generateName") for k in metadata.get("properties", {})):
            add("SCHEMA-METADATA", "FAIL", "Restricciones de metadata fuera de name/generateName.", root + ".properties.metadata")
        if len(out) == before:
            add("SCHEMA-STATIC", "PASS", "No se detectaron errores en el subconjunto estático del esquema.", root,
                limitations=["No valida completamente defaults, regex RE2, formatos, CEL, admisión o datos persistidos."])
    return out


def instance_issues(value, schema, path="$", depth=0):
    """Return paths/reasons only, never custom resource values or names."""
    if depth > 80 or not isinstance(schema, dict):
        return []
    if value is None and schema.get("nullable"):
        return []
    typ = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool}
    if schema.get("x-kubernetes-int-or-string") and type(value) in (int, str):
        return []
    if typ in types and (not isinstance(value, types[typ]) or (typ in ("number", "integer") and isinstance(value, bool))):
        return [{"path": path, "reason": "type"}]
    issues = []
    if "enum" in schema and value not in schema["enum"]:
        issues.append({"path": path, "reason": "enum"})
    if type(value) in (int, float):
        for key, fails in (("minimum", lambda b: value < b), ("maximum", lambda b: value > b)):
            if isinstance(schema.get(key), (int, float)) and fails(schema[key]):
                issues.append({"path": path, "reason": key})
    if isinstance(value, (str, list)):
        lower, upper = ("minLength", "maxLength") if isinstance(value, str) else ("minItems", "maxItems")
        if lower in schema and len(value) < schema[lower]:
            issues.append({"path": path, "reason": lower})
        if upper in schema and len(value) > schema[upper]:
            issues.append({"path": path, "reason": upper})
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                issues.append({"path": path + "." + key, "reason": "required"})
        for key, child in schema.get("properties", {}).items():
            if key in value:
                issues.extend(instance_issues(value[key], child, path + "." + key, depth + 1))
    if isinstance(value, list):
        for child in value:
            issues.extend(instance_issues(child, schema.get("items", {}), path + "[]", depth + 1))
    return issues
