# Seguimiento incremental 0.5.2

Rama: dev. Base: 09e9b7c. Los merges a main quedan a cargo del usuario. No se añade CI ni acceso de escritura al clúster.

## Evidencia revisada

Se leyó el HTML aportado localmente: 19.040.009 bytes, 176.267 líneas. No se copió al repositorio público ni se modificó. Las evidencias de gatekeeper-audit y tigera-operator sólo conservaban identidad por nombre, sin repositorio/tag. El inventario también registraba `pods: inventory_limit`, 2.000 objetos examinados, e `istioctl version: binary_missing` como fuente opcional.

Un HTML que omitió la imagen no permite recuperar su versión efectiva. Esta entrega corrige la captura/representación para la siguiente ejecución, sin inventar los datos faltantes del archivo anterior. Además se corrigió un límite inclusivo: llegar exactamente al máximo de una lista Kubernetes completa no demuestra por sí solo truncamiento. Un error ya registrado en un reporte histórico no se elimina sin una captura nueva.

## Causas y cambios

| Solicitud | Causa y corrección |
|---|---|
| ERROR sin causa inmediata | El consolidado mostraba sólo el estado y un detalle por contexto. Ahora incluye una sección antes de la tabla con número de grupos con errores, fuentes, códigos, objetos examinados y acciones. Los errores de inventario no se confunden con FAIL de compatibilidad. |
| Gatekeeper/Tigera sin versión | El fallback de workload conocido leía labels, pero descartaba las imágenes cuyo repositorio no estaba en la lista exacta. Ahora inspecciona containers e initContainers y vincula el nombre conocido al contenedor del controlador; conserva observaciones de todos los contenedores. No toma tags de helpers, versiones de chart, ni la versión de Calico como Tigera. Los repositorios exactos/configurados existentes siguen funcionando. |
| Evidencia insuficiente del workload | Se conservan imagen, repositorio, declared_tag, imageID cuando está disponible, chart y labels de versión. Un Deployment normalmente no expone imageID de runtime: se deja null y no se inventa un digest. Los Pods aportan ready, restartCount y estado permitido, sin mensajes potencialmente sensibles. |
| Secrets Store CSI | Un catálogo con política general y sin filas numéricas no puede acreditar un binario histórico. El resultado continúa UNKNOWN con NO_OFFICIAL_KUBERNETES_MATRIX y explicación de versión/objetivo. La razón interna no_numeric_rows queda en JSON y no se muestra como mensaje del usuario en HTML. |
| Snapshot administrado | Se mezclaba origen administrado con compatibilidad. Ahora las dimensiones son versión MANAGED, managed_by AKS, compatibilidad UNKNOWN y razón MANAGED_VERSION_NOT_EXPOSED. Los IDs/valores anteriores están en campos legacy. No se emite PASS sin garantía aplicable al objetivo. |
| INVENTORY_INCOMPLETE sobredimensionado | Los nodos eran obligatorios también para descartar cualquier operador. Los operadores basados en workloads/CRDs ahora usan sus fuentes pertinentes; nodos sigue siendo obligatorio globalmente y para AKS. Helm continúa opcional. Una fuente obligatoria realmente fallida conserva el estado incompleto y se muestra por nombre/error. CRDs pasa a estar explícito en el ledger. |
| CONTEXT_DATA_MISMATCH sin diff | El fingerprint detectaba el cambio pero no lo describía. Se añadió una proyección de diferencias por contexto: conteos/nombres de CRDs, productos visibles, versiones, consultas fallidas y cobertura. Se mantienen ambos detalles y no se altera el algoritmo de identidad/agrupación. |
| Istio excesivo | Se repetían listas por Pod en el detalle y hallazgos. El HTML usa resúmenes de control plane/gateways y contadores de sidecars por versión/actividad. JSON sigue conservando evidencia disponible, con --full-platform-evidence para incluir todas las observaciones permitidas del inventario examinado. Los contadores se calculan antes del límite de muestras. |

El fallback de mirror requiere un workload conocido y el nombre exacto de imagen del controlador; no se identifica un producto sólo por una subcadena cualquiera. Para el nombre genérico operator de Tigera se exige además un contenedor tigera-operator/operator, evitando confundir helpers. Cuando falta esa identidad explícita, se conserva la imagen observada, se puede usar una versión declarada válida del workload y, si no existe, se conserva UNKNOWN. Los aliases explícitos por --detectors-path permanecen disponibles.

## Lo que se conservó

- Catálogos de soporte Istio y Calico sin modificaciones.
- Funciones SemVer release/bound/in_range y archivo version_resolver.py sin cambios de resolución.
- Identidad, fingerprint y agrupación del consolidado sin cambios.
- Archivo readiness.py completo, pesos, score/cobertura/decisión y función exit_code sin cambios.
- Peso cero PRODUCT_SUPPORT y módulos de estructura, schema/CEL, storage, conversión e instancias sin cambios.
- UTF-8 explícito, códigos independientes Pluto/validador y modo sólo lectura.

Se verificaron las funciones protegidas mediante comparación AST contra la base y los archivos protegidos mediante git diff. Las diferencias permitidas son captura de evidencia, campos/mensajes solicitados, alcance de las fuentes de detección y presentación del reporte.

## Pruebas y ejecución

Primero se ejecutó `python -m pytest tests/test_report_followup.py -q --tb=short`: **12 fallos**, reproduciendo los defectos sin modificar implementación. Después se agregaron casos de límite exacto/continuación, sufijo de distribución explícito, helpers de Tigera y flag de JSON completo. Se mantuvieron los tests existentes; sólo se actualizaron dos expectativas de nombres/semántica de Secrets Store y Snapshot expresamente solicitadas, conservando sus aserciones UNKNOWN y los campos legacy.

La suite final se ejecuta con:

```sh
python -m pytest -q --tb=short
git diff --check
python fixtures/generate_followup_example.py
```

Resultado verificado: **259 pruebas aprobadas**, incluidas 21 pruebas nuevas parametrizadas de este seguimiento. El log de ejecución está en `deliverables/report-followup/verification.txt`. El entorno puede emitir la deprecación de pytest-asyncio previamente instalada; no se añade como dependencia.

La prueba de tamaño compara 40 y 1.000 Pods con evidencia completa: el HTML no crece con el listado por Pod (crecimiento inferior a 3 KB en el caso probado), conserva contadores y no altera el JSON original, las versiones ni el veredicto. El ejemplo sintético tiene 160 sidecars, 12 Pods no operativos y 8 activos con versión distinta a la del control plane, mientras Istio sigue FAIL.

El ejemplo `reports/examples/report-followup/consolidated.html` agrupa tres contextos sintéticos en dos identidades. Expone dos grupos de errores técnicos, un mismatch con Deployment RBAC/CRDs/productos diferentes y otro inventario realmente recortado a 120 Pods. Su tamaño es aproximadamente 223 KB y 4.200 líneas. No debe compararse como reducción porcentual del HTML real de 19 MB: son datasets distintos. La reducción independiente del número de sidecars se verifica en la prueba dedicada.

## Archivos de esta entrega

- `validator/platform_discovery.py`, `workload_evidence.py` (nuevo): imágenes de workloads conocidos, estados permitidos y resúmenes de Istio.
- `validator/detection_status.py`, `platform_analyzer.py`: fuentes pertinentes, CRDs explícitos, JSON completo opcional y semántica administrada.
- `validator/context_diff.py` (nuevo), `consolidated_report.py`: causas accionables y diferencias, sin modificar deduplicación.
- `validator/platform_catalog.py`: sólo mensaje/código de Secrets Store cuando faltan filas; no modifica el matching de Istio/Calico.
- `validator/platform_report.py`, `report_generator.py`: compacción exclusiva de evidencia de Istio en HTML, manteniendo matrices y hallazgos técnicos.
- `validator/cli.py`, `batch.py`: opción aditiva --full-platform-evidence, disponible también desde la shell.
- `tests/test_report_followup.py` (nuevo); expectativas explícitas actualizadas en `test_incremental_dev.py` y `test_product_registry.py`.
- `fixtures/generate_followup_example.py` (nuevo), reportes sintéticos, README, este documento, pyproject.toml e init de versión 0.5.2.

El ZIP y el manifiesto en `deliverables/report-followup/` incluyen los archivos completos modificados/nuevos y sus SHA-256, aplicables sobre la base indicada. No contienen el HTML real aportado ni inventario privado del usuario.

## Fuentes y límites remanentes

Se revisaron la [política oficial de instalación/soporte](https://secrets-store-csi-driver.sigs.k8s.io/getting-started/installation) y las [notas oficiales de v1.1.2](https://github.com/kubernetes-sigs/secrets-store-csi-driver/releases/tag/v1.1.2). No se encontró en esas fuentes una matriz que vincule ese binario con Kubernetes 1.35. No se extrapola una política actual de minors mantenidos a cualquier release histórico.

Gatekeeper y Tigera pueden tener versión conocida y conservar compatibilidad UNKNOWN si sus catálogos no acreditan un rango aplicable. Una imagen con sufijo no normalizable se conserva como versión declarada y VERSION_FORMAT_UNVERIFIED, sin convertirla en versión desconocida ni forzar soporte. Una imagen por digest sin versión declarada sigue sin demostrar SemVer.

La evidencia completa opcional sigue limitada al inventario examinado: no evita RBAC, timeouts, páginas pendientes ni --platform-limit. Los reportes con errores verdaderos no pasan a NOT_DETECTED por conveniencia. La existencia de una fuente fallida no demuestra un cluster eliminado ni un error de identidad.

No se consultaron clústeres reales. Los fixtures no acreditan las versiones efectivas de Gatekeeper/Tigera del HTML recibido; es necesaria una ejecución nueva para capturar sus imágenes. No se modificó el archivo original del usuario, ni se emitió una garantía de upgrade seguro o de preparación para producción.
