"""Run the user's external API deprecation scanner, without parsing its table."""
import os
import re
import subprocess
from .models import finding

SOURCE = "https://pluto.docs.fairwinds.com/advanced/"


def sanitize(text):
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    text = re.sub(r"(?i)Bearer\s+\S+", "Bearer [REDACTED]", text)
    text = re.sub(r"(?i)((?:token|password|secret|api[_-]?key)\s*[=:]\s*)\S+", r"\1[REDACTED]", text)
    text = re.sub(r"https?://[^\s/@]+:[^\s/@]+@", "https://[REDACTED]@", text)
    return "".join(c for c in text if c in "\n\t" or ord(c) >= 32)


def run(context, target, timeout=120, offline=False, runner=None):
    command = ["pluto", "detect-all-in-cluster", "-o", "wide", "--kube-context", context,
               "--target-versions", f"k8s=v{target}", "--ignore-deprecations=false",
               "--ignore-removals=false", "--ignore-unavailable-replacements=false"]
    result = {"executed": False, "command": command if not offline else [], "context": context,
              "target_version": str(target), "exit_code": None, "stdout": "", "stderr_omitted": True,
              "limitations": ["Pluto tiene su propio catálogo de APIs; un resultado limpio no prueba cobertura de versiones futuras.",
                               "La detección depende de los objetos y metadatos disponibles para Pluto."]}
    status, message = "UNKNOWN", "Pluto no se ejecuta en modo offline."
    if not offline:
        try:
            # Prevent environment settings from narrowing the scan or hiding findings.
            env = {k: v for k, v in os.environ.items() if not k.upper().startswith("PLUTO_")}
            completed = (runner or subprocess.run)(command, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=timeout, check=False, shell=False, env=env)
            result.update(executed=True, exit_code=completed.returncode)
            status = {0: "PASS", 2: "WARN", 3: "FAIL", 4: "WARN"}.get(completed.returncode, "ERROR")
            message = {0: "Pluto completó la detección sin hallazgos reportados.", 2: "Pluto detectó APIs deprecadas.",
                       3: "Pluto detectó APIs eliminadas.", 4: "Pluto detectó reemplazos no disponibles en el objetivo."}.get(completed.returncode, "Pluto no pudo completar la detección; revisar instalación y permisos.")
            if status != "ERROR":
                result["stdout"] = sanitize(completed.stdout[:200_000])
                result["output_truncated"] = len(completed.stdout) > 200_000
                if result["output_truncated"]:
                    result["limitations"].append("Salida truncada a 200000 caracteres.")
            result["stderr_present"] = bool(completed.stderr)
        except FileNotFoundError:
            status, message = "ERROR", "Pluto no está instalado o no está disponible en PATH."
        except subprocess.TimeoutExpired:
            result["executed"] = True
            status, message = "ERROR", "Pluto excedió el timeout; resultado incompleto."
        except OSError:
            status, message = "ERROR", "No se pudo iniciar Pluto."
    result.update(status=status, message=message)
    observation = finding("PLUTO-SCAN", "native_api_deprecations", status, message,
                          source=SOURCE, relation="limitation" if status in ("UNKNOWN", "ERROR") else "upgrade",
                          validation_type="external_tool", evidence={"exit_code": result["exit_code"], "executed": result["executed"]},
                          recommendation="Revisar la sección Pluto y mantener actualizado el binario y su catálogo de APIs.", limitations=result["limitations"])
    return result, observation
