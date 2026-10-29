"""Regenerate synthetic CRD examples; no cluster or network access."""
from copy import deepcopy
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    base = json.loads((root / "valid-crds.json").read_text(encoding="utf-8"))["items"][0]
    cases = [deepcopy(base)]

    def case(plural):
        crd = deepcopy(base)
        crd["metadata"]["name"] = plural + ".example.com"
        crd["spec"]["names"] = {"plural": plural, "singular": plural[:-1], "kind": plural.replace("-", " ").title().replace(" ", "")[:-1]}
        cases.append(crd)
        return crd

    invalid_schema = case("broken-schemas")
    invalid_schema["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"]["spec"]["properties"]["replicas"].pop("type")
    stored = case("retired-versions")
    stored["status"]["storedVersions"] = ["v1alpha1", "retired"]
    webhook = case("broken-webhooks")
    webhook["spec"]["conversion"] = {"strategy": "Webhook", "webhook": {
        "conversionReviewVersions": ["v9"], "clientConfig": {"service": {"name": "converter", "namespace": "operators", "port": 70000}, "caBundle": "invalid"}}}
    cel = case("cel-widgets")
    cel["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"]["spec"]["x-kubernetes-validations"] = [{"rule": "self.replicas <= 20"}]
    migration = case("migrating-widgets")
    v1 = deepcopy(migration["spec"]["versions"][0])
    v1["name"] = "v1"
    migration["spec"]["versions"][0]["storage"] = False
    migration["spec"]["versions"].append(v1)
    migration["status"]["storedVersions"] = ["v1alpha1", "v1"]
    (root / "mixed-crds.json").write_text(json.dumps({"apiVersion": "v1", "kind": "List", "items": cases}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
