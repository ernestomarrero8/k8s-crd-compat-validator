from copy import deepcopy
import pytest
from validator import storage_validator, schema_validator, conversion_validator
from validator.operator_validator import analyze as operator_analyze
from validator.version import Version
from validator.collector import CollectionError


def rules(findings):
    return {f.rule_id: f.status for f in findings}


def test_valid_crd_is_not_guaranteed_pass(crd, inspect_crd):
    result = inspect_crd(crd)
    assert result["status"] == "UNKNOWN"
    assert not any(f["status"] in ("FAIL", "ERROR") for f in result["findings"])
    assert "STORAGE-CONSISTENT" in {f["rule_id"] for f in result["findings"]}


def test_custom_alpha_beta_names_are_not_deprecated_apis(crd, inspect_crd):
    for name in ("v1alpha1", "v1beta1"):
        crd["spec"]["versions"][0]["name"] = name
        crd["status"]["storedVersions"] = [name]
        assert not any(f["status"] == "FAIL" for f in inspect_crd(crd)["findings"])


def test_multiple_storage(crd):
    extra = deepcopy(crd["spec"]["versions"][0])
    extra["name"] = "v1"
    crd["spec"]["versions"].append(extra)
    assert rules(storage_validator.analyze(crd))["STORAGE-ONE"] == "FAIL"


def test_multiple_served_allowed(crd):
    extra = deepcopy(crd["spec"]["versions"][0])
    extra.update(name="v1", storage=False)
    crd["spec"]["versions"].append(extra)
    assert rules(storage_validator.analyze(crd)) == {"STORAGE-CONSISTENT": "PASS"}


@pytest.mark.parametrize("stored", [[], ["removed"], ["v1"], [42]])
def test_invalid_stored_versions(crd, stored):
    crd["status"]["storedVersions"] = stored
    assert "FAIL" in rules(storage_validator.analyze(crd)).values()


def test_storage_change_does_not_mean_migration(crd):
    extra = deepcopy(crd["spec"]["versions"][0])
    extra.update(name="v1", storage=True)
    crd["spec"]["versions"][0]["storage"] = False
    crd["spec"]["versions"].append(extra)
    crd["status"]["storedVersions"] = ["v1alpha1", "v1"]
    assert rules(storage_validator.analyze(crd))["STORED-MIGRATION"] == "WARN"


def test_divergent_schemas_none_conversion(crd):
    extra = deepcopy(crd["spec"]["versions"][0])
    extra.update(name="v1", storage=False)
    extra["schema"]["openAPIV3Schema"]["properties"]["other"] = {"type": "string"}
    crd["spec"]["versions"].append(extra)
    assert rules(storage_validator.analyze(crd))["CONVERSION-NONE-DIVERGENT"] == "WARN"


@pytest.mark.parametrize("schema,rule", [
    ({"properties": {"x": {"type": "string"}}}, "SCHEMA-ROOT"),
    ({"type": "object", "properties": {"x": {}}}, "SCHEMA-TYPE"),
    ({"type": "object", "properties": {"x": {"type": "array"}}}, "SCHEMA-ITEMS"),
    ({"type": "object", "properties": {"x": {"type": "string", "minLength": 4, "maxLength": 2}}}, "SCHEMA-BOUNDS"),
    ({"type": "object", "x-kubernetes-preserve-unknown-fields": False}, "SCHEMA-PRESERVE"),
    ({"type": "object", "x-kubernetes-list-type": "map"}, "SCHEMA-LIST-TYPE"),
    ({"type": "object", "x-kubernetes-map-type": "other"}, "SCHEMA-MAP-TYPE"),
    ({"type": "object", "properties": {"x": {"type": "array", "items": {"type": "object"}, "x-kubernetes-list-type": "map"}}}, "SCHEMA-MAP-KEYS"),
    ({"type": "object", "x-kubernetes-validations": [{"message": "missing rule"}]}, "SCHEMA-CEL-FORMAT"),
    ({"type": "object", "anyOf": [{"properties": {"x": {"minimum": 0}}}]}, "SCHEMA-JUNCTOR-PROPERTY"),
    ({"type": "object", "allOf": [{"description": "bad"}]}, "SCHEMA-JUNCTOR-STRUCTURE"),
])
def test_schema_problems(crd, schema, rule):
    crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"] = schema
    assert rules(schema_validator.analyze(crd))[rule] == "FAIL"


@pytest.mark.parametrize("property_schema", [
    {"x-kubernetes-preserve-unknown-fields": True},
    {"x-kubernetes-int-or-string": True},
    {"x-kubernetes-int-or-string": True, "anyOf": [{"type": "integer"}, {"type": "string"}]},
    {"x-kubernetes-int-or-string": True, "allOf": [{"anyOf": [{"type": "integer"}, {"type": "string"}]}]},
    {"type": "array", "x-kubernetes-list-type": "map", "x-kubernetes-list-map-keys": ["name"],
     "items": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}},
])
def test_valid_schema_exceptions(crd, property_schema):
    crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"]["x"] = property_schema
    assert not any(f.status == "FAIL" for f in schema_validator.analyze(crd))


def test_cel_is_unknown_with_specific_upgrade_warning(crd, inspect_crd):
    crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["x-kubernetes-validations"] = [{"rule": "self.spec.replicas >= 0"}]
    result = inspect_crd(crd)
    findings = {f["rule_id"]: f for f in result["findings"]}
    assert findings["SCHEMA-CEL-UNVERIFIED"]["status"] == "UNKNOWN"
    assert findings["K135-CEL-ERROR-VALUES"]["relation"] == "upgrade"
    assert findings["K135-CEL-ERROR-VALUES"]["status"] == "WARN"


def webhook(crd, review=None):
    crd["spec"]["conversion"] = {"strategy": "Webhook", "webhook": {
        "conversionReviewVersions": review or ["v1"],
        "clientConfig": {"service": {"name": "converter", "namespace": "system", "port": 443}}}}
    return crd["spec"]["conversion"]["webhook"]


def test_webhook_bad_protocol_and_ca(crd):
    hook = webhook(crd, ["v9"])
    hook["clientConfig"]["caBundle"] = "not-a-certificate"
    result = rules(conversion_validator.analyze(crd, protocols=["v1", "v1beta1"]))
    assert result["CONVERSION-REVIEW"] == "FAIL"
    assert result["CONVERSION-CA"] == "FAIL"


def test_webhook_v1beta1_is_still_a_protocol(crd):
    webhook(crd, ["v1beta1"])
    result = rules(conversion_validator.analyze(crd, protocols=["v1", "v1beta1"]))
    assert result["CONVERSION-REVIEW"] == "PASS"
    assert result["CONVERSION-TARGET"] == "UNKNOWN"


@pytest.mark.parametrize("config,rule", [
    ({}, "CONVERSION-DESTINATION"),
    ({"url": "http://example.com"}, "CONVERSION-URL"),
    ({"url": "https://user:pass@example.com"}, "CONVERSION-URL"),
    ({"url": "https://example.com?q=secret"}, "CONVERSION-URL"),
    ({"service": {"name": "s", "namespace": "n", "port": 70000}}, "CONVERSION-SERVICE"),
])
def test_webhook_bad_configuration(crd, config, rule):
    webhook(crd)["clientConfig"] = config
    assert rules(conversion_validator.analyze(crd, protocols=["v1", "v1beta1"]))[rule] == "FAIL"


def test_live_endpoints_do_not_prove_target_compatibility(crd):
    webhook(crd)
    class Live:
        def get(self, resource, *args, **kwargs):
            if resource == "services":
                return {"spec": {"ports": [{"port": 443}]}}
            return {"items": [{"endpoints": [{"addresses": ["10.0.0.2"], "conditions": {"ready": True}}]}]}
    result = rules(conversion_validator.analyze(crd, Live()))
    assert result["CONVERSION-ENDPOINTS"] == "PASS"
    assert result["CONVERSION-TARGET"] == "UNKNOWN"


def test_webhook_rbac_unknown(crd):
    webhook(crd)
    class Denied:
        def get(self, *args, **kwargs):
            raise CollectionError("forbidden")
    assert rules(conversion_validator.analyze(crd, Denied()))["CONVERSION-LIVE"] == "UNKNOWN"


def test_operator_unknown_even_with_labels(crd):
    assert rules(operator_analyze(crd, Version.parse("1.35.9")))["OPERATOR-SUPPORT"] == "UNKNOWN"


@pytest.mark.parametrize("field,value", [("versions", None), ("versions", [None]), ("conversion", None), ("scope", "bad")])
def test_malformed_crd_does_not_abort_inventory(crd, inspect_crd, field, value):
    crd["spec"][field] = value
    result = inspect_crd(crd)
    assert result["status"] == "FAIL"


def test_instance_schema_values_never_returned():
    schema = {"type": "object", "required": ["missing"], "properties": {"secret": {"type": "integer"}}}
    issues = schema_validator.instance_issues({"secret": "DO_NOT_PRINT"}, schema)
    assert {i["reason"] for i in issues} == {"required", "type"}
    assert "DO_NOT_PRINT" not in repr(issues)
