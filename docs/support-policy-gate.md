# Soporte, inventario completo y gate — 0.6.0

Rama: dev. Base: 3fa3d89. main no se modifica; los merges quedan a cargo del usuario. Fix incremental, sin CI automático ni escrituras Kubernetes.

## Hallazgos de la revisión

El HTML local aportado registra los tags Microsoft Gatekeeper v3.23.1-8 y Tigera Operator v1.40.15-4, así como inventario parcial de Pods. Se leyó para validar el defecto; no se modificó ni se incorporó al repositorio público. Las demostraciones usan contextos y recursos sintéticos.

El fallo de Istio proviene de una matriz de soporte y no de una prueba de ejecución sobre el objetivo. Se conserva el bloqueo de upgrade, con dimensiones separadas. El límite anterior de Pods se aplicaba tras descargar la lista y no recorría explícitamente páginas; además el comparador trataba diferencias de muestras parciales como concluyentes. La revisión numérica de Microsoft tampoco tenía regla de normalización para esos dos productos.

## Cambios por prioridad

| Área | Corrección y evidencia |
|---|---|
| P0 Soporte vs fallo técnico | Se conservan status FAIL y decisión BLOCKED para política, añadiendo support_status FAIL_SUPPORT_POLICY y technical_status NOT_TESTED. El HTML indica que no se demostró una falla técnica del producto mediante la matriz. Los fallos estáticos propios de un CRD se muestran por separado como técnicos. |
| P0 Actual y objetivo | Cada versión observada se evalúa contra current y target sin duplicar penalizaciones. Se publican matrices/fuentes/revisión de ambas evaluaciones. Runtime ACTIVE requiere observación operacional; un Helm release no basta. Deuda previa y riesgo nuevo quedan null si la evidencia no permite distinguirlos. |
| P0 Revisión de empaquetado | Sólo los repositorios exactos mcr.microsoft.com/oss[/v2]/open-policy-agent/gatekeeper y mcr.microsoft.com/oss[/v2]/tigera/operator reciben la regla numérica. Se guardan raw/upstream/revisión/repositorio. rc.1 no se normaliza. Un build no obtiene soporte de distribución sólo porque upstream pasa. |
| P0 Mismatch parcial | CONTEXT_DATA_MISMATCH se reserva para diferencias semánticas sobre inventarios obligatorios completos. Si falta cobertura, se publica CONTEXT_COMPARISON_INCONCLUSIVE con inventory_truncated/inventory_incomplete, fuentes y conteos. La identidad y membresía de contextos se conservan. |
| P1 Paginación | Pods usa GET /api/v1/pods con limit=500 y continue codificado. Se recorren todas las páginas hasta token vacío o guard de seguridad. Máximo predeterminado 20000 objetos, configurable mediante el parámetro existente. Se conserva progreso ante fallos, tokens repetidos y cambio de resourceVersion; no se exportan tokens. |
| P1 Timeout global | Collector comparte un deadline entre todas sus lecturas y el contexto objetivo. Las herramientas opcionales/Azure/Pluto reciben el tiempo restante. Batch continúa imponiendo además el timeout externo por proceso. No se inventa exit code de Pluto si no llegó a iniciarse. |
| P1 istioctl opcional | Su ausencia pasa a OPTIONAL_SOURCE_UNAVAILABLE; el resumen distingue impacto nulo para versión cuando hay alternativas válidas. Si no las hay, la versión sigue UNKNOWN. No añade una unidad de error de inventario cuando el descubrimiento Kubernetes fue completo. |
| P1 Inactividad | Contadores por causa y WARN limitado a condiciones operativas relevantes. Completados/terminando no se penalizan como sidecars defectuosos. Sólo evidencia histórica sin controlador confirmado se trata como artefactos, no como una instalación activa acreditada. |
| P1 Gestión AKS | Columnas separadas para terceros/gestión no verificada y AKS administrados con evidencia pendiente; subset sin versión expuesta. Requiere metadata de AKS, no sólo imagen Microsoft. Ningún UNKNOWN se descuenta de cobertura ni se convierte en PASS. |
| P2 Gatekeeper | UNKNOWN / NO_OFFICIAL_NUMERIC_MATRIX si no existe fila oficial numérica. release_support_status también queda UNKNOWN sin una lista mantenida de releases verificada para la fecha. El enlace a la política no se convierte en matriz Kubernetes. |

Las reglas y matrices Istio/Calico, pesos 40/25/15/10/10 y fórmula de readiness siguen intactos. Los códigos NOT_COMPATIBLE y VERSION_EOL permanecen; el primero explicita failure_domain SUPPORT_POLICY. PRODUCT_SUPPORT mantiene peso cero y conserva su estado legado, con metadata de política adicional.

## Ejemplo de semántica

```json
{
  "product": "Istio",
  "status": "FAIL",
  "support_status": "FAIL_SUPPORT_POLICY",
  "technical_status": "NOT_TESTED",
  "operational_status": "RUNNING_OUTSIDE_SUPPORT_MATRIX",
  "current_kubernetes_evaluation": {
    "version": "1.34.8",
    "support_status": "OUTSIDE_SUPPORT_MATRIX",
    "observed_runtime": "ACTIVE"
  },
  "target_kubernetes_evaluation": {
    "version": "1.35.9",
    "support_status": "OUTSIDE_SUPPORT_MATRIX"
  },
  "preexisting_support_debt": true,
  "additional_upgrade_support_risk": false,
  "decision": "BLOCKED"
}
```

El producto no fue probado funcionalmente sobre el objetivo. Un CRD de ese producto puede tener un defecto técnico independiente; no se oculta por la clasificación de soporte. El JSON retiene el estado combinado legado del CRD y añade technical_status/technical_failure_demonstrated; la columna técnica HTML excluye la referencia PRODUCT_SUPPORT.

En los builds Microsoft observados: v3.23.1-8 → upstream 3.23.1 / revisión 8; v1.40.15-4 → upstream 1.40.15 / revisión 4. Se evalúa el selector upstream. Si una matriz upstream pasa pero no acredita el build, VENDOR_BUILD_UNVERIFIED conserva UNKNOWN; un registro vendor_versions explícito puede acreditarlo. No se exige un rango inventado para eliminar UNKNOWN.

## Ejemplo y pruebas ejecutadas

Antes de implementación, `python -m pytest tests/test_support_gate.py -q --tb=short` reprodujo **16 fallos y 3 casos ya correctos**. Se añadieron posteriormente casos de integración de páginas, progreso parcial, token repetido, snapshot cambiado, timeout, metadata de snapshot, Completed sin WARN, clasificación de fallo técnico, selección exacta de build y deuda previa desconocida.

La suite completa final ejecutada con `python -m pytest -q --tb=short` tiene **289 pruebas aprobadas**: se conservan las 259 anteriores y se añaden 30 casos parametrizados. Sólo se actualiza una expectativa antigua de Gatekeeper para el nuevo código solicitado, manteniendo UNKNOWN y el legacy_rule_id. El log real queda en `deliverables/support-policy-gate/verification.txt`. La deprecación pytest-asyncio del entorno no es una dependencia añadida.

Comandos ejecutados:

```sh
python -m pytest tests/test_support_gate.py -q --tb=short
python -m pytest -q --tb=short
python fixtures/generate_support_gate_example.py
git diff --check
python main.py --version
python batch.py --version
```

El generador utiliza un runner simulado de Collector: **2657 Pods en seis páginas**, sin ejecutar kubectl. Luego analiza snapshots offline para seis contextos en tres identidades:

- demo-match: inventarios completos con distinto orden/muestras, resultado MATCH.
- demo-partial: ambos recortados a 120 objetos con diferentes subconjuntos, CONTEXT_COMPARISON_INCONCLUSIVE, sin afirmar mismatch.
- demo-different: inventarios completos con una versión Argo CD diferente, CONTEXT_DATA_MISMATCH.

El ejemplo muestra 157 sidecars, 125 activos y 32 inactivos: 20 Completed, 5 Terminating, 2 Failed, 3 Running_proxy_not_Ready y 2 Pending; sólo tres proxies no Ready y un Pending prolongado generan el aviso operativo. No atribuye fallos técnicos a los Jobs completados. No se compara su tamaño con el HTML privado real: son datasets distintos.

## Archivos y compatibilidad

- Nuevos: `validator/distribution_version.py`, `support_evaluation.py`, `tests/test_support_gate.py`, `fixtures/generate_support_gate_example.py` y este documento.
- Modificados: collector, descubrimiento/análisis, resolver (metadata de versión), catálogo (semántica/selección de build), estados de inventario, evidencia Istio, comparación/consolidación, renderers, metadata de PRODUCT_SUPPORT, CLI/batch, detectores Microsoft, README y versión.
- Se conservan nombres de parámetros existentes. Se añade --cluster-timeout; --platform-limit cambia su default de 2000 a un máximo de seguridad 20000. --context-timeout continúa en batch.
- El JSON pasa a esquema 1.6 con campos aditivos; status PASS/WARN/FAIL/UNKNOWN/ERROR y products_unknown completo siguen disponibles. Las nuevas particiones de UNKNOWN son de presentación, no de ponderación.
- Los archivos completos y SHA-256 están en `deliverables/support-policy-gate/complete-files.zip` y `files-manifest.json`, aplicables sobre 3fa3d89.

## Operación y límites

```sh
python main.py --context production --target-version 1.35.9 --cluster-timeout 1800
bash crd-compat-validator.sh --target-version 1.35.9 --context-timeout 1800
```

La ejecución directa aplica un presupuesto compartido a las lecturas; la serialización del reporte puede requerir tiempo posterior. El runner batch aplica además un límite total del proceso. Cada petición está acotada por --timeout y el tiempo restante; --max-queries limita también la paginación. Llegar al máximo de seguridad, perder autorización o no terminar la secuencia nunca produce inventory_complete=true. No se reinicia silenciosamente una paginación sobre otro snapshot.

No se validó un AKS real. Las pruebas verifican contratos de paginación y evidencia sintética; no son una certificación de funcionamiento productivo ni una prueba funcional de operadores sobre 1.35. Un diff describe observaciones y no demuestra por sí solo que una identidad esté mal configurada. Evidencia insuficiente sigue requiriendo revisión o bloqueo conservador. El HTML anterior debe regenerarse para disponer de inventarios completos y las dimensiones nuevas.

Referencias primarias revisadas: [paginación de la API Kubernetes](https://kubernetes.io/docs/reference/using-api/api-concepts/#retrieving-large-results-sets-in-chunks), [instalación de Gatekeeper](https://open-policy-agent.github.io/gatekeeper/website/docs/install/) y [política de releases](https://github.com/open-policy-agent/gatekeeper/blob/master/docs/Release_Management.md). Esas fuentes no se convierten en una matriz numérica inventada ni en garantía del build Microsoft. No se modificó el catálogo de Istio ni el de Calico; no se añadieron escrituras al clúster, upgrades, reinicios ni CI.
