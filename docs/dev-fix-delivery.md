# Entrega incremental 0.5.1 — dev

Fecha: 5 de noviembre de 2026. Base: main, commit 1ad07d4. Todos los cambios se publican en dev; el usuario realiza los merges a main. Se conserva la arquitectura de recolección → detección → resolución → catálogo → hallazgos → reportes. No se añadió CI.

## Causas y correcciones

| Defecto | Causa raíz y cambio acotado |
|---|---|
| 2.1 Actividad vs artefactos | El diagnóstico calculaba DETECTED por la existencia de una fila. Ahora la evidencia de presencia/operación determina el estado específico; CRDs/configuración residual no confirman controlador. Se conservan detected y legacy_status. |
| 2.2 Secrets Store CSI | Faltaban aliases exactos históricos del driver y el proveedor Azure tenía un nombre de driver. Son productos independientes; el ID azure-keyvault y los catálogos personalizados con su nombre anterior siguen funcionando. |
| 2.3 Gatekeeper | Faltaba el repositorio quay.io y el fallback explícito de workloads/labels. Se inspeccionan controller-manager y audit sin fijar namespace. Sólo para Gatekeeper se especializa prioridad Helm → manager → audit → Pods → labels; se evalúan todas las versiones observadas. |
| 2.4 Tigera | Faltaba el repositorio sin prefijo tigera/operator y fallback de workload/labels. Se conserva la separación de versiones Calico/Operator; un chart versionado como Calico no se usa como binario del operador. |
| 2.5 Snapshot | CRDs no prueban controlador; sidecar y controller no estaban distinguidos. Se añadieron imágenes históricas y un detector de sidecar independiente. Metadata explícita AKS puede mostrar MANAGED / MANAGED_BY_AKS con soporte UNKNOWN, sin inventar versión numérica. |
| 2.6 Inventario | Cualquier error, incluso Helm opcional, contaminaba todos los diagnósticos. Cada fuente tiene su propio resultado; sólo las fuentes obligatorias incompletas causan INVENTORY_INCOMPLETE. Las excepciones internas se aíslan por detector y se exponen como DETECTION_ERROR. |
| 2.7 Contextos duplicados | El consolidado iteraba contextos sin identidad del clúster. Se agrupa por identidad verificada con las prioridades requeridas; se consultan todos los contextos para no perder diferencias de RBAC/datos. Los desacuerdos generan CONTEXT_DATA_MISMATCH, mantienen ambos detalles y no suman dos clústeres físicos. |
| 2.8 Ponderación | El score ya excluía la categoría operator de la unidad técnica. Se conserva esa protección, se añade exclusión explícita por PRODUCT_SUPPORT/score_weight y metadata de referencia de peso cero. La prueba con 15 CRDs evita una regresión futura. |
| 2.9 Score/cobertura/decisión | Se exponían puntos acreditados como score principal, y ERROR bloqueaba como FAIL. Se reutiliza el cálculo evaluable existente como Compatibility score, se publica cobertura por unidades y se separan BLOCKED/INCOMPLETE/ATTENTION_REQUIRED/READY. Los pesos permanecen 40/25/15/10/10. |
| 2.10 Exit codes | Pluto ya conservaba su código real, pero el consolidado mostraba un código del proceso del validador sin identificarlo. Ahora se publican por separado, con origen, códigos originales por contexto y normalización de timeout del runner. |
| 2.11 UTF-8 | rules/kubernetes.json ya contenía texto corrupto antes del renderer; el batch también dejaba la codificación del hijo al entorno. Se restauró el texto fuente en UTF-8 y se fijó UTF-8 en hijo, lectura de stdout y logs. Sin reemplazos heurísticos en ejecución. |
| 2.12 Resumen ejecutivo | Faltaban razones priorizadas, productos afectados y contextos asociados. Se añadieron columnas sin quitar el detalle existente. Un FAIL documentado precede a las limitaciones UNKNOWN; se ordenan las razones por severidad dentro de esa prioridad. |

## Archivos

Cambios de ejecución y datos, entregados completos en el ZIP:

- `validator/detection_status.py` (nuevo), `platform_discovery.py`, `platform_analyzer.py`: presencia, actividad, fuentes e inventario parcial.
- `catalogs/operators/detectors.json`: aliases exactos y separación de productos, sin cambiar el formato del catálogo.
- `validator/version_resolver.py`: prioridad específica de Gatekeeper y trazabilidad de la fuente; no se altera normalización SemVer.
- `validator/platform_catalog.py`: alias del nombre histórico del proveedor Azure, conservando catálogos personalizados y sus sufijos de distribución.
- `validator/cluster_identity.py` (nuevo), `collector.py`, `azure_validator.py`: identidad estable, GET de kube-system y proyección exclusiva del endpoint del kubeconfig.
- `validator/models.py`, `product_link.py`: referencias PRODUCT_SUPPORT explícitamente sin peso adicional.
- `validator/readiness.py`, `cli.py`: score evaluable, cobertura, política configurable y estado/código del validador.
- `validator/platform_report.py`, `report_generator.py`, `consolidated_report.py`: presentación aditiva, agrupación, discrepancias y campos ejecutivos.
- `batch.py`: forwarding de configuración, UTF-8 del hijo/log y conservación de códigos originales.
- `rules/kubernetes.json`: sólo restauración de caracteres UTF-8 y versión de la revisión; IDs, condiciones, severidades, resultados y fuentes se conservan.
- `validator/__init__.py`, `pyproject.toml`: versión 0.5.1.
- `tests/test_incremental_dev.py` (nuevo): 43 casos nuevos parametrizados; `test_collector_cli.py`, `test_platforms.py`, `test_product_registry.py`, `test_reported_compatibility_cases.py`: expectativas actualizadas únicamente para las nuevas semánticas explícitas de exit/decisión/cobertura y consultas de identidad. Se mantienen sus aserciones técnicas y de seguridad.
- `readiness.example.yaml` (nuevo), `fixtures/generate_dev_example.py` (nuevo), `README.md`, `AGENTS.md` (nuevo) y este documento.
- Reportes sintéticos regenerados en `reports/examples`, `reported-cases`, `product-analysis` y `dev-analysis`; resumen JSON aditivo del consolidado.

El manifiesto `deliverables/files-manifest.json` contiene la lista exacta de archivos y SHA-256. `deliverables/dev-fix-complete-files.zip` incluye el contenido completo de cada archivo modificado/nuevo de esta entrega, sin .git, credenciales, logs de producción ni fragmentos de código aislados. Se aplica sobre la base indicada; no sustituye archivos ajenos a la entrega.

## Pruebas y comandos ejecutados

Antes de cambiar implementación se ejecutó:

```sh
python -m pytest tests/test_incremental_dev.py -q --tb=short
```

Resultado inicial real: **24 fallos, 1 aprobado**. La prueba ya correcta protegía Istio/Calico. Se ampliaron luego los casos con prioridad de Gatekeeper, webhooks, identidad, UTF-8, builds administrados, configuración inválida, compatibilidad del catálogo anterior y códigos independientes. La prueba de prioridad y la del alias de catálogo se ejecutaron primero en rojo antes de corregir esos casos.

Verificación final:

```sh
python -m pytest -q --tb=short
git diff --check
git diff main -- catalogs/support/istio.json catalogs/support/calico.json validator/storage_validator.py validator/schema_validator.py validator/conversion_validator.py validator/crd_analyzer.py
python main.py --version
python batch.py --version
```

Resultado: **238 pruebas aprobadas** (incluye un caso parametrizado nuevo del detector sidecar en la suite existente). Versiones: 0.5.1. La comparación de los catálogos y módulos técnicos protegidos está vacía. El log de pytest se entrega en `deliverables/verification.txt`. El entorno emite una deprecación de pytest-asyncio instalada globalmente, sin fallos de pruebas; no es una dependencia nueva del proyecto.

Ejemplos reproducidos, sin acceso a clúster:

```sh
python main.py --input fixtures/mixed-crds.json --platform-input fixtures/platform-inventory.json --current 1.34.8 --target-version 1.35.9 --output reports/examples --format all
python main.py --input fixtures/product-crds.json --platform-input fixtures/product-inventory.json --current 1.34.8 --target-version 1.35.9 --output reports/examples/product-analysis --format all
python main.py --input fixtures/valid-crds.json --platform-input fixtures/reported-platform-cases.json --current 1.34.8 --target-version 1.35.9 --output reports/examples/reported-cases --format all
python fixtures/generate_consolidated_example.py --source reports/examples/reported-cases/report.json
python fixtures/generate_dev_example.py
```

Los tres comandos de main devuelven 1 por FAIL documentados de los fixtures. Los generadores devuelven 0. Los valores de Pluto simulados en tests son mocks; no se presentan como ejecuciones reales contra un clúster.

## Antes y después del HTML

| Caso sintético | Antes (v0.5.0) | Ahora (v0.5.1) |
|---|---|---|
| Gatekeeper sólo CRDs | DETECTED, versión UNKNOWN | ARTIFACTS_ONLY; controlador activo false; CONTROLLER_NOT_CONFIRMED; soporte UNKNOWN |
| Argo CD ausente, Helm no disponible y Kubernetes completo | INVENTORY_INCOMPLETE por error opcional global | NOT_DETECTED con limitación Helm inventory unavailable |
| Dos contextos del mismo Resource ID | Dos filas y doble total de clúster | Una fila, dos contextos asociados; detalles por contexto preservados |
| Contextos con datos diferentes | Dos evaluaciones independientes sin relación explícita | Una identidad, CONTEXT_DATA_MISMATCH y ambos reportes completos, validator exit consolidado 2 |
| Pluto PASS y validador FAIL | Exit code 1 junto a Pluto, origen ambiguo | Pluto exit 0 / Validator exit 1 |
| Texto de reglas | validaciÃ³n / cÃ³digo | validación / código, en UTF-8 en el archivo fuente |
| Fixture reported-cases | Puntos de preparación 46.3, cobertura ponderada 61.1%, BLOCKED | Compatibility score 75.8, cobertura por unidades 50.0%, BLOCKED; no son métricas directamente comparables |

El consolidado nuevo de `reports/examples/dev-analysis/consolidated.html` contiene **4 contextos → 2 identidades**, con dos contextos por fila. Una identidad tiene discrepancia marcada explícitamente. El principal bloqueo sigue siendo Istio 1.24.1, no una limitación UNKNOWN. Son datos sintéticos.

## Conservación y límites

**Istio 1.24.1 sigue FAIL contra 1.35.9**, selector 1.24.x, hallazgos VERSION_EOL y NOT_COMPATIBLE. Helm, Deployment pilot y Pod proxyv2 conservan evidencia. **Calico v3.31.2 sigue PASS**, selector 3.31.x, versión normalizada 3.31.2 y origen Calico ClusterInformation. Sus dos catálogos de soporte no se modificaron.

No se tocaron los módulos de estructura/análisis de CRD, storage, esquema ni conversión. Se conservaron las advertencias CEL, instancias no inspeccionadas y los tres códigos K135, junto con evidencia y fuentes. Un producto compatible sigue sin ocultar un defecto técnico de storage.

Límites remanentes:

- No se validó un clúster real; inventarios, comandos y metadata de tests/ejemplos son simulados. No se ejecutaron escrituras Kubernetes, upgrades, reinicios ni helm upgrade.
- Actividad/presencia no acredita compatibilidad ni el binario por digest. Si un snapshot no contiene estado operacional, no se inventan réplicas disponibles; se registra presencia del workload.
- No se añadieron matrices de soporte no verificadas. Gatekeeper, Tigera, sidecar, builds Azure y componentes administrados pueden conservar UNKNOWN con causa documentada.
- Las consultas complementarias de APIService/webhook/Service/EndpointSlice son opcionales; sus fallos se conservan en las fuentes. Los webhooks conocidos se reconocen por identidad exacta, sin atribuir cualquier webhook a un producto por coincidencias parciales.
- Si no hay identidad común verificable, se mantienen contextos separados. No se deduplica por nombre. Si hay discrepancias, la fila ejecutiva usa el contexto principal y exige revisar todos los detalles; no fabrica una fusión de inventarios.
- Se conserva UNKNOWN como evidencia pendiente. Un Compatibility score alto con poca cobertura no convierte la decisión en READY.
- Los reportes históricos ya corruptos no se reparan automáticamente: deben regenerarse con 0.5.1. La configuración YAML soporta sólo los tres escalares documentados, sin un parser YAML general ni dependencias adicionales.
