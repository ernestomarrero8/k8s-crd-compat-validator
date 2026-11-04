# k8s-crd-compat-validator

CLI de solo lectura para evaluar CRDs y sus dependencias antes de un upgrade Kubernetes. Python 3.12+, Windows y Linux; biblioteca estándar en ejecución. No instala servicios, no modifica el clúster. En LIVE también ejecuta Pluto como detector externo de APIs deprecadas.

Desde v0.3 también descubre plataformas/operadores mediante Helm, workloads, pods y CRDs; evalúa matrices oficiales curadas y muestra un resumen ejecutivo con Upgrade Readiness Score. El mismo análisis se incorpora al HTML consolidado de varios contextos.

El repositorio incluye validaciones estáticas, consultas LIVE acotadas, un motor de reglas JSON, reportes JSON/Markdown/HTML y pruebas con kubectl simulado. La transición revisada inicialmente es **1.34 → 1.35**. Los números de parche se comparan, pero el catálogo no promete cubrir todos los cambios de cada parche o distribución, incluido AKS.

## Inicio rápido

No hace falta instalar paquetes para ejecutar la herramienta desde este directorio:

```sh
python main.py --input fixtures/valid-crds.json --current 1.34.8 --target 1.35.9 --output reports/demo
```

El ejemplo válido produce `UNKNOWN`: tiene estructura válida, pero no aporta una matriz de soporte del operador ni pruebas sobre sus instancias. Un resultado incompleto nunca se transforma en una garantía de compatibilidad.

Para instalar pytest y ejecutar las pruebas:

```sh
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Linux:

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

Se usa directamente el intérprete del entorno para evitar depender de scripts de activación. `pytest` es la única dependencia de desarrollo. No es necesario instalar este proyecto como paquete.

## Modos de ejecución

### LIVE

Requiere `kubectl` y `pluto` en PATH, un kubeconfig ya configurado y permisos de lectura. La herramienta toma **serverVersion.gitVersion**, nunca la versión del cliente. Fija el contexto activo al inicio para que un cambio posterior de contexto no redirija consultas.

```sh
python main.py --target 1.35.9
python main.py --context production --target 1.35.9
python main.py --context production --target 1.35.9 --output reports/production --format all
python main.py --target 1.35.9 --include-instances --timeout 30 --max-queries 200
```

`--current` en LIVE es opcional y debe coincidir con el servidor. Se aceptan `1.34.8`, `v1.34.8` y sufijos de proveedor como `v1.34.8-aks.1`; se comparan los tres números. Se rechazan versiones iguales, downgrades, formatos inválidos y prereleases alpha/beta/rc. Los saltos minor generan un aviso y enumeran versiones intermedias; esto no autoriza un salto que el proveedor no soporte.

### OFFLINE

```sh
kubectl get crds -o json > crds.json
python main.py --input crds.json --current 1.34.8 --target 1.35.9
```

Admite un CRD individual, `List` o `CustomResourceDefinitionList`, en UTF-8 (con o sin BOM) y UTF-16 con BOM para exportaciones de Windows PowerShell 5. No ejecuta kubectl ni Pluto, ni accede a Internet. `--include-instances` registra `UNKNOWN` en este modo. No permite combinar offline con contextos o `--verify-sources`.

### TARGET VALIDATION: observaciones de lectura

```sh
python main.py --context production --target 1.35.9 --target-context validation-cluster
```

El segundo servidor debe ejecutar exactamente el número major/minor/patch solicitado y usar otro nombre de contexto. Lee CRDs ya instalados, compara `spec` y comprueba discovery de versiones servidas si la definición coincide. No instala ni altera definiciones. La igualdad es estricta; diferencias por defaults o configuración producen `UNKNOWN`.

**No ejecuta admisión ni dry-run.** Este modo acredita observaciones sobre un API Server real, no aceptación de nuevas escrituras ni funcionamiento del operador. Pruebas de creación, actualización y conversión con datos representativos deben realizarse mediante un procedimiento separado, autorizado, en un entorno aislado. Los alias de contexto no demuestran aislamiento; aquí no hay escrituras incluso si dos alias apuntan al mismo clúster.

## Qué se comprueba

| Área | Estático / offline | Con acceso LIVE |
|---|---|---|
| Estructura | Identidad, nombres, scope, versiones, tipos de campos, condiciones disponibles | Exportación actual de CRDs |
| Almacenamiento | Una versión storage, served, consistencia de storedVersions, migración pendiente de revisión | No lee etcd ni modifica storage |
| OpenAPI | Tipos, raíz, arrays, required, límites contradictorios, ramas lógicas, extensiones list/map/int-or-string/unknown-fields | Sin compilación de esquemas en servidor |
| CEL | Forma de reglas, detección y regla de diagnóstico en 1.35 | Compilación, coste y updates permanecen sin verificar |
| Conversión | Estrategia, protocolos, destino, puerto, HTTPS, parseo de CA | Service y EndpointSlices, con caché |
| Operadores | Indicios de labels/Helm y catálogo revisado opcional | Ownership OLM y Deployments del release Helm |
| Instancias | No verificables | LIST paginado por versión servida y validación parcial del contenido |
| Clúster objetivo | No verificable | Definiciones preinstaladas y discovery |

Un nombre de API personalizada como `v1alpha1` o `v1beta1` no genera un aviso de deprecación. `ConversionReview/v1beta1` tampoco se confunde con la API nativa retirada de definición de CRDs. Las comprobaciones de representación de entrada se limitan a los CRDs que interpreta esta herramienta.

Los problemas estáticos se marcan `preexisting`: ya están presentes en la entrada, sin afirmar cuándo aparecieron. Un esquema que viola requisitos puede fallar al registrar o modificar la definición; un CRD heredado ya almacenado puede tener excepciones. El informe no convierte ese defecto automáticamente en una caída causada por 1.35.

## Resultados y CI/CD

| Estado | Interpretación |
|---|---|
| PASS | La comprobación concreta pasó dentro de sus límites |
| WARN | Riesgo potencial o intervención que requiere revisión |
| FAIL | Defecto demostrado por la comprobación; revisar su relación con el upgrade |
| UNKNOWN | Evidencia ausente, verificación no realizada o permisos insuficientes en lecturas auxiliares |
| ERROR | No pudo completarse una validación por un fallo de ejecución o una estructura no interpretable |

Cada hallazgo tiene severidad independiente `CRITICAL/HIGH/MEDIUM/LOW/INFO`, evidencia, recomendación, fuente, método y relación: `preexisting`, `upgrade`, `release_change`, `limitation`, `documented` o `tested`.

La agregación por CRD y global usa `ERROR > FAIL > WARN > UNKNOWN > PASS`. Un FAIL no elimina los UNKNOWN del detalle. El estado global también considera hallazgos de cobertura. Los conteos por severidad cuentan hallazgos WARN/FAIL/ERROR, no CRDs únicos. La evidencia de instancias identifica conteos por versión, que **no deben sumarse** porque pueden corresponder a los mismos objetos.

| Código | Significado |
|---|---|
| 0 | Ningún estado coincide con la política de bloqueo; no implica compatibilidad total |
| 1 | Se encontró al menos un estado seleccionado en `--fail-on` |
| 2 | Error de argumentos, entrada, configuración, acceso esencial o ejecución de validación |

Por defecto se bloquea por `FAIL,ERROR`. `--fail-on` selecciona estados **exactos**, no umbrales de severidad, y evalúa todos los hallazgos. ERROR siempre devuelve 2, incluso con `--fail-on NONE`.

```sh
python main.py --context production --target 1.35.9 --fail-on FAIL,WARN,UNKNOWN,ERROR --format json
```

La política anterior será estricta también con cobertura parcial o no revisada y Pluto no ejecutado en offline. Es intencional: la versión inicial no puede certificar exhaustividad. Para gates de hallazgos demostrados, use la política predeterminada y revise los UNKNOWN mediante el informe.

## Límites de consultas y datos

`--timeout` limita cada proceso kubectl (el timeout externo añade 2 segundos). `--max-queries` limita invocaciones por contexto, incluyendo descubrimiento y dependencias. Cuando se agota el presupuesto auxiliar, se informa `UNKNOWN`; si no puede obtenerse el inventario inicial, devuelve 2.

Las instancias usan `kubectl get --raw /apis/<group>/<version>/<plural>?limit=...&continue=...`:

- `--page-size 100`: tamaño solicitado por página.
- `--max-pages 5`: máximo por CRD y versión servida.
- `--max-instances 500`: máximo de objetos examinados por CRD y versión.
- Un límite alcanzado produce conteo parcial y WARN; RBAC insuficiente, UNKNOWN; otros errores, ERROR.
- La respuesta puede haber pasado por conversión. Su `apiVersion` no demuestra la versión persistida.
- El análisis de instancias cubre tipos, required, enum, límites numéricos y tamaños; no replica toda la semántica de validación del API Server.

El inventario inicial de CRDs y las listas auxiliares de OLM/Deployments/EndpointSlices se descargan completas dentro del timeout; el límite de páginas de la CLI solo corresponde a Custom Resources. `kubectl` puede realizar peticiones internas adicionales, por lo que el contador mide procesos, no solicitudes HTTP físicas. El tiempo total puede llegar al presupuesto de consultas multiplicado por su timeout.

## Operadores y evidencia del proveedor

No se suministra una matriz ficticia. La herramienta relaciona:

- `app.kubernetes.io/name` y `app.kubernetes.io/version` como indicios.
- `meta.helm.sh/release-name` y `release-namespace` con Deployments del release.
- CSVs de OLM cuyos `spec.customresourcedefinitions.owned` mencionen exactamente el CRD; conserva `spec.version` y `minKubeVersion` como evidencia.

Un chart, un Deployment Running o el mínimo de OLM no prueban soporte máximo. No se infiere versión del operador desde un tag de imagen ambiguo. Sin coincidencia única con evidencia revisada, el resultado de soporte es UNKNOWN.

`--operator-catalog catalog.json` admite una lista de registros curados con estos campos:

| Campo | Contenido requerido |
|---|---|
| `crds` | Lista de nombres exactos de CRDs |
| `operator`, `operator_version` | Identidad y versión exactas observadas |
| `kubernetes_min`, `kubernetes_max` | Versiones inclusivas completas `major.minor.patch` |
| `source` | URL HTTPS oficial del proveedor o repositorio del proyecto |
| `source_sha256` | SHA256 de los bytes del documento revisado, 64 dígitos hexadecimales |
| `reviewed_on` | Fecha de revisión |
| `evidence` | Resumen de la afirmación de soporte y su ubicación en la fuente |

Si el proveedor solo publica versiones minor, el revisor debe documentar cómo traduce el rango a límites completos; no inventar un máximo. No incorporar credenciales o datos de clientes en estos registros.

En LIVE, `--verify-sources` consulta las URLs HTTPS registradas y compara sus hashes; limita cada documento a 2 MB y no sigue redirecciones. No envía datos del clúster. Un documento inaccesible o cambiado produce UNKNOWN. Una coincidencia del hash verifica la vigencia del documento revisado, **no interpreta su semántica**. Sin este flag, la fuente se considera evidencia local del revisor y el informe indica que no se verificó online. Fuera de un rango documentado se genera WARN, porque ausencia de soporte acreditado no equivale a un fallo técnico demostrado.

## Reglas externas

`--rules-path archivo.json` o `--rules-path directorio` agrega reglas a las incluidas. IDs duplicados o archivos inválidos abortan con código 2. No ejecuta expresiones Python ni código externo. Solo JSON, sin dependencias YAML.

Estructura de archivo: `{"schema_version": 1, "rules": [...]}`. Cada regla exige `rule_id`, `category`, `description`, `severity`, `status`, `source`, `recommendation`, `relation`, `validation_type`, `evidence`, `condition` y `applicability`. Consulte [las reglas incluidas](rules/kubernetes.json) para ejemplos reales.

`applicability` permite límites inclusivos `current_min/current_max/target_min/target_max`, y `crosses` para evaluar únicamente cuando `current < crosses <= target`. Las condiciones admiten `all`, `any`, o `path/op/value`, con operadores `exists`, `absent`, `equals`, `contains` (listas) y `count_gt` (número de nodos seleccionados). Rutas separadas por punto: `*` selecciona hijos y `**` recorre descendientes. No se soportan claves que contengan puntos en este selector simple; para ello se necesita una validación de código.

Una regla declara su fuente y evidencia, pero el motor no puede certificar que el autor interpretó correctamente la documentación. Solo use archivos de reglas revisados. Las validaciones básicas permanecen en módulos Python; agregar condiciones declarativas sobre campos existentes no requiere cambiarlos.

## Investigación de Kubernetes 1.34 → 1.35

Revisión inicial: 29 de octubre de 2026. Las reglas de transición incluidas son:

| ID | Evidencia oficial | Resultado |
|---|---|---|
| `K135-CEL-ERROR-VALUES` | [PR 132798](https://github.com/kubernetes/kubernetes/pull/132798) | WARN LOW si hay CEL: revisar consumidores de errores y tratamiento de valores en logs |
| `K135-CONDITION-GENERATION` | [Notas 1.35, PR 134984](https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.35.md) | PASS INFO: cambio aditivo en condiciones; no demuestra una incompatibilidad |
| `K135-STATUS-SCHEMA-FIX` | [Notas 1.35, PR 133721](https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.35.md) | PASS INFO para CRDs con subresource status: corrección relevante, sin atribuir vulnerabilidad al parche de origen |

El catálogo no inventa una ruptura general de CRDs en 1.35. La revisión también identificó cambios de diagnóstico sobre formatos numéricos; no se clasifican como incompatibilidad de esquema. Los backports pueden hacer que una corrección ya exista en 1.34.8. Las APIs nativas de migración y otras deprecaciones permanecen en el ámbito de Pluto.

Bases técnicas adicionales:

- [Esquemas y extensiones de CRDs, documentación 1.35](https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/).
- [Versiones, conversión y almacenamiento, documentación 1.35](https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/).
- [Validación upstream fijada a v1.35.0](https://github.com/kubernetes/kubernetes/blob/v1.35.0/staging/src/k8s.io/apiextensions-apiserver/pkg/apis/apiextensions/validation/validation.go).
- [Semántica CEL en Kubernetes](https://kubernetes.io/docs/reference/using-api/cel/).
- [Ownership de CRDs en OLM](https://olm.operatorframework.io/docs/concepts/crds/clusterserviceversion/).

No se incluye una matriz de feature gates ni diferencias entre versiones efectivas de emulación del API Server. El catálogo de cobertura explicita las áreas pendientes aunque el número de servidor coincida con el objetivo.

## Permisos y seguridad

Lecturas esenciales: GET de versión del servidor y LIST de `customresourcedefinitions.apiextensions.k8s.io`. Según las opciones y CRDs encontrados, se necesitan GET de Services, LIST de EndpointSlices, CSVs OLM, Deployments y recursos personalizados; las listas globales requieren permisos en los namespaces correspondientes. Discovery del objetivo requiere GET sobre `/apis/...`. El análisis propio de CRDs no requiere Secrets ni nodos. Pluto puede necesitar leer Secrets de releases Helm y otros recursos para completar detect-all-in-cluster; sus permisos deben corresponder al alcance de la evaluación.

Para kubectl solo existen comandos `get`, `version` y `config current-context`; adicionalmente se ejecuta `pluto detect-all-in-cluster`. No hay apply, delete, patch, migraciones, reinicios o actualizaciones. Las herramientas de autenticación exec de kubectl pueden ejecutarse conforme al kubeconfig del usuario; utilice un kubeconfig de confianza.

Se omiten kubeconfig, tokens, bundles CA, cuerpos de CRs, mensajes del servidor y annotations completas. Se conservan contexto, nombres de CRDs, versiones, rutas de campos e indicios de identidad de operadores, por lo que el informe sigue siendo información operativa. HTML escapa contenido, usa una CSP sin scripts y no carga recursos remotos. Los informes se escriben como UTF-8 y reemplazan `report.json`, `report.md` y `report.html` en el directorio elegido.

## Archivos y ejemplos

```text
main.py
validator/                 # CLI, colector, analizadores, reglas y reportes
rules/kubernetes.json       # Reglas de transición documentadas
tests/                     # Pruebas sin clúster
fixtures/valid-crds.json    # CRD sintético sin defectos estáticos
fixtures/mixed-crds.json    # Casos sintéticos válidos, CEL, storage y webhook
reports/examples/          # JSON, Markdown y HTML generados
requirements.txt           # Solo pytest para desarrollo
```

Reproducir ejemplos:

```sh
python fixtures/generate_examples.py
python main.py --input fixtures/mixed-crds.json --current 1.34.8 --target 1.35.9 --output reports/examples --format all
```

El segundo comando devuelve **1** por los defectos deliberados del fixture. No son resultados de producción. El fixture válido y el mixto usan un operador ficticio sin matriz; sus datos nunca se presentan como soporte real.

## Limitaciones conocidas

La validación estática es un subconjunto conservador de API Machinery. No compila CEL, calcula su coste, valida regex RE2/defaults/formatos completamente, ni prueba ratcheting o subresources scale. No ejecuta reconciliación de operadores, admission webhooks generales, escrituras o TLS real desde el API Server. Parsear una CA no prueba SAN, caducidad, cadena o accesibilidad de red. EndpointSlices son una observación puntual.

Las pruebas automatizadas no requieren ni validan un clúster real. Antes de aprobar un upgrade, revisar hallazgos, completar evidencia de operadores y ejecutar las pruebas funcionales del entorno de validación conforme al procedimiento de la organización.

## Verificación de esta entrega

El 29 de octubre de 2026 se ejecutaron **93 pruebas, todas aprobadas**, en Windows con Python 3.13.6 y pytest 8.3.4. Se desactivó la carga automática de plugins pytest instalados globalmente mediante `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`; el proyecto no necesita plugins. Las pruebas incluyen rutas completas de CLI LIVE y TARGET con subprocess simulado, aislamiento offline, reglas externas, redacción de datos sensibles y generación de los tres formatos.

El comando del fixture mixto generó los reportes incluidos y terminó con código 1 esperado: **3 FAIL, 2 WARN, 1 UNKNOWN, 0 ERROR**. Se verificó también la ayuda CLI. No se consultó ningún clúster real ni se ejecutaron escrituras. La portabilidad Linux se basa en biblioteca estándar y comandos sin shell; no se ejecutó una prueba de integración en Linux durante esta entrega.


## Cambios de v0.2: mantenimiento y Pluto

No se agrega CI automático. Las pruebas se ejecutan localmente con `python -m pytest -q`.

### Pluto en el reporte

En LIVE se ejecuta automáticamente este comando, fijando el mismo contexto de origen y el objetivo de la CLI:

```sh
pluto detect-all-in-cluster -o wide --kube-context production --target-versions k8s=v1.35.9 --ignore-deprecations=false --ignore-removals=false --ignore-unavailable-replacements=false
```

Las opciones adicionales impiden evaluar accidentalmente otro contexto/objetivo u ocultar resultados. Se eliminan las variables heredadas `PLUTO_*` del proceso para evitar filtros implícitos; se conservan KUBECONFIG y las variables de autenticación habituales. El programa no cambia el contexto activo. `--pluto-timeout 120` controla el tiempo total del proceso; el presupuesto de consultas kubectl no limita las lecturas internas de Pluto.

La sección **Pluto** en JSON, Markdown y HTML contiene el comando, contexto, objetivo, código de salida, estado y tabla wide con saltos de línea preservados. Los resultados son globales, no se atribuyen artificialmente a un CRD. El JSON conserva también si hubo stderr y si la salida fue truncada. Se omite stderr y la salida de procesos fallidos para evitar publicar diagnósticos con credenciales; se redactan patrones comunes de secretos en stdout. La tabla puede contener nombres operativos y debe tratarse como información del clúster. Se limita el texto publicado a 200000 caracteres, pero la captura de subprocess se realiza en memoria.

Según los [códigos documentados de Pluto](https://pluto.docs.fairwinds.com/advanced/): 0 se registra PASS, 2 WARN (deprecadas), 3 FAIL (eliminadas), 4 WARN (reemplazo no disponible). Otros códigos, binario ausente o timeout producen ERROR. Siempre se genera el reporte de CRDs si Pluto falla; la CLI devuelve 2. `--fail-on` considera el hallazgo de Pluto junto a los demás. En offline no se inicia el proceso y se informa UNKNOWN.

Mantener Pluto actualizado es parte del mantenimiento: su catálogo de APIs es independiente de nuestras reglas. La detección basada en metadatos tiene las [limitaciones descritas por Fairwinds](https://pluto.docs.fairwinds.com/faq/). Un código 0 no certifica la cobertura de una versión futura.

### Catálogo de cobertura

`rules/coverage.json` contiene una versión de catálogo, revisiones por rangos de origen/objetivo y protocolos ConversionReview documentados. `--coverage-path archivo.json` permite reemplazarlo por un catálogo revisado, sin cambiar Python. Los rangos son inclusivos. Cada registro exige fecha, revisor y fuente HTTPS.

Los registros `reviews` enumeran categorías, limitaciones y uno de estos estados:

- `partial`: hay revisión, pero queda alcance pendiente; se emite UNKNOWN.
- `reviewed_changes`: se revisaron cambios relevantes para las categorías declaradas.
- `reviewed_no_changes`: se revisó el alcance declarado y no se encontraron cambios relevantes.

La ausencia de registro significa **unreviewed**, nunca PASS. En saltos minor se evalúa cada tramo intermedio; un tramo ausente o parcial mantiene UNKNOWN. PASS en cobertura solo acredita revisión documental de las categorías indicadas. No acredita operadores, distribución ni ejecución del upgrade. La cobertura inicial sigue siendo parcial: no se amplió ficticiamente a versiones futuras.

`conversion_protocols` define `target_min`, `target_max` y `versions`, además de fuente y revisión. Si no hay un único registro aplicable, la comprobación del protocolo devuelve UNKNOWN en lugar de asumir compatibilidad. Se conservaron las comprobaciones independientes de sintaxis, TLS y endpoints.

Las reglas de transición usan `crosses` para indicar cuándo se introduce un cambio. Sus efectos pueden seguir siendo relevantes al saltar a versiones posteriores: las reglas incluidas ya no expiran al acabar 1.35. Un `target_max` en futuras reglas solo debe expresar un fin de aplicabilidad demostrado; la falta de investigación se registra en cobertura. Para correcciones y backports, definir rangos precisos y probar sus límites. Cambios que excedan los predicados disponibles siguen requiriendo un nuevo validador Python.

Los tres reportes incluyen versión de herramienta, versión y SHA256 del archivo de cobertura, versión/hash de cada archivo de reglas y hash de las reglas efectivas. Se conserva el soporte para reglas externas anteriores, identificadas como `unversioned` si no declaran `catalog_version`. El esquema JSON del informe es ahora 1.1 (campos aditivos `knowledge` y `pluto`).

### Procedimiento para incorporar otra versión

1. Revisar documentación oficial y cambios relevantes para CRDs, incluyendo parches y backports. Registrar revisor, fecha y referencias fijadas a tags/commits cuando existan.
2. Agregar reglas y pruebas positivas, negativas y de límites; registrar explícitamente cambios ausentes o revisión parcial.
3. Actualizar cobertura y protocolos solo dentro del alcance acreditado; mantener el catálogo del operador por separado.
4. Ejecutar las pruebas locales y, cuando corresponda, pruebas funcionales en un laboratorio aislado autorizado. Esta entrega no crea clústeres ni ejecuta pruebas mutantes.
5. Incrementar versiones de catálogo/herramienta y publicar una revisión con su evidencia. Conservar los archivos y hashes usados por cada evaluación.

La validación de v0.2 el 4 de noviembre de 2026 completó **111 pruebas aprobadas** en Windows con Python 3.13.6, con subprocess simulado para Pluto; no se consultó un clúster real.

## Varios contextos: detalle individual y HTML consolidado

La shell `crd-compat-validator.sh` ejecuta el nuevo runner `batch.py`. Por defecto enumera todos los contextos del kubeconfig mediante `kubectl config get-contexts -o name`. No necesita kubectx ni cambia el contexto activo. Cada contexto se pasa explícitamente a main.py, que también lo utiliza para Pluto.

```sh
bash crd-compat-validator.sh --target 1.35.9
```

El intérprete predeterminado es python3.12. Para usar otro:

```sh
PYTHON_BIN=python3 bash crd-compat-validator.sh --target 1.35.9
```

También se puede ejecutar directamente en Windows o Linux, seleccionando contextos concretos:

```sh
python batch.py --target 1.35.9 --context production --context tools --output reports
```

El resultado tiene esta estructura; cada ejecución recibe una carpeta nueva con fecha UTC e identificador único:

```text
reports/run-<fecha>-<id>/
  consolidated.html
  contexts.json
  001-production-<hash>/
    report.html
    report.json
    report.md
    console.txt
  002-tools-<hash>/
    report.html
    report.json
    report.md
    console.txt
```

`consolidated.html` es un archivo autónomo: contiene una tabla ejecutiva por contexto, versión actual/objetivo, estado, cantidad de CRDs, resultado de Pluto, código de salida y decisión orientativa. Los enlaces de la tabla llevan al detalle completo dentro del mismo HTML, incluyendo hallazgos, evidencia, catálogos y tabla de Pluto. Se puede copiar o enviar ese único archivo sin las carpetas individuales.

La recomendación respeta la evidencia: FAIL requiere resolver bloqueos, WARN requiere revisión, UNKNOWN indica evidencia insuficiente y ERROR una evaluación incompleta. No se declara adecuado un upgrade con verificaciones pendientes. Un resultado PASS solo acredita el alcance evaluado.

Un fallo de un contexto no detiene los siguientes. Los contextos sin JSON válido, con JSON de otro contexto/objetivo o con timeout aparecen como ERROR en el consolidado. Solo se incluyen resultados de la ejecución actual; no se buscan archivos antiguos. `contexts.json` registra las rutas relativas y códigos de salida. Los nombres de carpeta usan un prefijo seguro y hash para evitar colisiones o rutas fuera del directorio de salida.

El runner devuelve 2 si hubo errores o timeout; en otro caso devuelve 1 si algún análisis devolvió 1 según su política `--fail-on`, o 0. `--context-timeout` limita el proceso completo por contexto (1800 segundos por defecto). Al vencer puede conservarse detalle parcial, marcado ERROR.

Se pueden pasar `--include-instances`, `--verbose`, `--verify-sources`, `--rules-path`, `--coverage-path`, `--operator-catalog`, `--timeout`, `--pluto-timeout`, `--max-queries`, `--page-size`, `--max-pages`, `--max-instances` y `--fail-on` a main.py mediante el runner. Escribir cada opción y valor separados por espacio. El runner fija `--format all` y los directorios individuales para poder consolidar. Modo offline y `--target-context` siguen disponibles mediante main.py, no mediante este runner de varios contextos.

Ejemplo sintético de consolidación: `reports/examples/consolidated.html`. Se regenera con `python fixtures/generate_consolidated_example.py` y no representa clústeres reales. Las pruebas del runner simulan subprocess; la entrega no ejecuta análisis sobre clústeres reales.

Verificación de esta ampliación: **118 pruebas aprobadas**; sintaxis de la shell comprobada con Bash. Incluye casos con contextos inaccesibles, timeout, JSON inválido, detalle de Pluto, nombres de contexto que colisionan tras normalización y aislamiento entre ejecuciones.

## v0.3: Cluster Platform Compatibility

```sh
python main.py --context aks-tools-prod-ceeb --target-version 1.35.9 --output reports/aks-tools
bash crd-compat-validator.sh --target-version 1.35.9
```

`--target-version` es un alias de `--target` tanto en main.py como en batch.py. En LIVE el descubrimiento de plataformas es automático. La categoría `operator_compatibility`, presentada como **OPERATOR COMPATIBILITY ANALYSIS**, agrega hallazgos globales al informe y a la política `--fail-on`. Los hallazgos de operadores asociados a CRDs ya existentes se conservan como una comprobación adicional de ownership; no equivalen al nuevo inventario de plataformas.

### Productos detectables

El catálogo `catalogs/operators/detectors.json` incluye Argo CD, Argo Workflows, Istio, Gatekeeper, Calico, Tigera Operator, Dapr, Secrets Store CSI Driver, Azure Policy Add-on, Defender for Cloud, Cluster Autoscaler, Karpenter, Cert Manager, NGINX Ingress Controller, AGIC, External DNS, Velero, Snapshot Controller, Prometheus Operator, OpenTelemetry Operator, FluxCD y Kyverno. Incluye además OMS Agent / AMA, Azure Key Vault CSI Driver y los drivers CSI de Azure Disk/File. Se distingue ingress-nginx comunitario del controlador F5 NGINX; sus versiones y matrices no son intercambiables.

Las identidades se basan en repositorios de imagen conocidos, nombres exactos de charts y CRDs específicos. No se busca por una subcadena genérica del nombre del Deployment. Mirrors privados o repositorios no catalogados pueden requerir actualizar los detectores; un producto ausente en el inventario no prueba ausencia absoluta en el clúster.

### Fuentes de versión y límites

- `helm list -A -o json --kube-context <contexto>`: se conserva chart y `app_version`; no se usa la versión del chart como versión de producto. Tigera es una excepción explícita: appVersion puede identificar Calico, no al operador.
- Deployments, DaemonSets, StatefulSets y Pods: se observan repositorio y tag de containers/initContainers. Los pods permiten detectar versiones anteriores que aún coexisten con el nuevo template. Se conservan namespaces, fuentes y revisiones Istio.
- CRDs: acreditan una API instalada, no que su operador esté activo. Si solo hay CRDs y no versión verificable, UNKNOWN.
- Calico: se consulta `clusterinformations.crd.projectcalico.org` y su campo `spec.calicoVersion`; también se leen TigeraStatus e Installation cuando sus CRDs existen. Estos últimos pueden no declarar ninguna versión de binario.
- Dapr: se observan imágenes, Helm y configuraciones de su API cuando existe; una versión de formato de configuración no se usa como versión runtime.
- Istio: cuando se detecta su instalación se intenta `istioctl version --context <contexto> -o json`. Se leen las versiones de control/data plane; se ignora la versión local del cliente. La falta del binario se registra como cobertura pendiente. Para Argo CD se utilizan las imágenes y Helm, evitando depender de una sesión de argocd CLI que pudiera apuntar a otro servidor.
- Flux: las versiones de source-controller, helm-controller y otros componentes no se convierten en una versión ficticia de la distribución Flux. Sin evidencia de su release, se informa UNKNOWN.

Tags `latest`, prereleases, versiones no reconocidas o imágenes solo por digest producen UNKNOWN. Un tag numérico es evidencia declarada de versión; no se verifica el contenido del binario mediante digest ni se infiere soporte porque el pod esté Running. Se muestran todas las versiones observadas, incluso mezcladas. Una observación sin versión impide acreditar compatibilidad completa de esa instalación.

`--platform-limit 2000` limita objetos examinados por fuente y evidencia publicada a 30 observaciones por producto/namespace. Las listas kubectl se descargan completas dentro de su timeout, y Helm solicita como máximo ese límite. Alcanzarlo genera UNKNOWN por cobertura. No hay una consulta por producto: se comparten inventarios y caché. Las consultas kubectl consumen `--max-queries`; Helm, istioctl y Azure CLI son procesos externos con `--timeout` por proceso. Errores RBAC, fuentes ausentes y datos incompletos generan hallazgos de cobertura; no se ocultan como productos inexistentes.

### Matrices documentadas

`catalogs/operators/` contiene archivos por producto. `--platform-catalog <directorio-o-json>` reemplaza las matrices incluidas, conservando los detectores. Es distinto del catálogo histórico `--operator-catalog` que relaciona ownership de CRDs.

Cada archivo requiere `product`, `catalog_version` y una lista `versions`. Cada registro requiere:

| Campo | Significado |
|---|---|
| `version` | Versión o familia de producto, por ejemplo `3.2.x` |
| `min_kubernetes`, `max_kubernetes` | Rango inclusivo; se admite `1.35.x` para toda esa minor |
| `matrix_type` | `supported` o `tested`, según la afirmación real del proveedor |
| `exclusive` | Solo true cuando la matriz delimita explícitamente las versiones soportadas; nunca para una mera lista de pruebas |
| `source`, `evidence` | URL oficial y resumen verificable de la fila/afirmación |
| `reviewed_on`, `valid_until` | Fechas ISO de revisión y vencimiento de la evidencia local |
| `end_of_support` | Opcional: fecha oficial de fin de mantenimiento |

El catálogo se valida antes de consultar el clúster. Las revisiones vencidas y las coincidencias de versión ambiguas producen UNKNOWN. Cada informe incluye hashes SHA256 de archivos y de los detectores para reproducibilidad. Se consultan las matrices **locales curadas con fuentes oficiales**; no se scrapea ni interpreta automáticamente HTML de proveedores durante una evaluación. Las consultas online de `--verify-sources` siguen correspondiendo únicamente al catálogo histórico de ownership. Actualizar estas matrices requiere revisar la fuente y sus fechas, no ampliar rangos por suposición.

Reglas de resultados:

| ID | Resultado |
|---|---|
| `OPERATOR-COMPATIBLE` | PASS: objetivo dentro de una matriz vigente de soporte o pruebas; el tipo de evidencia se muestra en el detalle |
| `OPERATOR-END-OF-SUPPORT` | WARN: se superó una fecha oficial de fin de mantenimiento |
| `OPERATOR-NOT-COMPATIBLE` | FAIL: objetivo fuera del rango explícito de soporte; no implica que se haya reproducido una caída |
| `OPERATOR-NO-MATRIX` | UNKNOWN: fila inexistente, ambigua, vencida o fuera de una mera lista de versiones probadas |
| `OPERATOR-VERSION-UNKNOWN` | UNKNOWN: no se obtuvo una versión inequívoca de producto |

Se conserva cada hallazgo: un producto puede tener PASS para un rango de Kubernetes y WARN por fin de mantenimiento. Los bloqueos prevalecen sobre otras versiones compatibles; UNKNOWN permanece visible como evidencia pendiente.

La primera revisión incorpora rangos de Istio 1.21, 1.28, 1.29 y 1.30, y versiones probadas de Argo CD 3.2, a partir de sus matrices oficiales consultadas el 4 de noviembre de 2026. Los archivos de Gatekeeper, Calico y Dapr registran fuentes y límites sin inventar rangos numéricos; los demás productos también permanecen UNKNOWN hasta contar con una matriz revisada para la versión instalada. Un detector disponible no equivale a una matriz disponible.

Fuentes iniciales: [Istio](https://istio.io/latest/docs/releases/supported-releases/), [Argo CD 3.2](https://argo-cd.readthedocs.io/en/release-3.2/operator-manual/tested-kubernetes-versions/), [Gatekeeper](https://github.com/open-policy-agent/gatekeeper/blob/master/docs/Release_Management.md), [Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements) y [Dapr](https://docs.dapr.io/operations/support/support-release-policy/). Los rangos de los ejemplos de requisitos no se toman como evidencia: por ejemplo, la tabla de Argo CD 3.2 enumera 1.31–1.34 como probadas; 1.35 se clasifica UNKNOWN.

### Metadata AKS

Se inventarían provider IDs de nodos, versiones kubelet y la label `kubernetes.azure.com/node-image-version`. Si todos los nodos permiten obtener una identidad Azure única, se consulta `az aks list` en esa suscripción para asociar exactamente el node resource group, y después `az aks show` con nombre, resource group y suscripción explícitos. No se modifica la cuenta activa ni el kubeconfig. La asociación debe ser única y la versión AKS coincidir con el servidor analizado; de otro modo se conserva UNKNOWN.

Del resultado solo se publican versión Kubernetes, add-ons habilitados, Defender, autoscaling y perfiles CSI/snapshot. No se exportan IDs de suscripción, datos de autenticación, configuración completa de add-ons, identities, env de contenedores ni manifiestos. Azure CLI es opcional; falta de acceso o de metadata produce UNKNOWN.

Los productos administrados pueden no tener Pods visibles, por ejemplo Cluster Autoscaler. En tal caso la metadata acredita su habilitación, pero no determina versión efectiva: UNKNOWN. Las matrices upstream no acreditan soporte de la distribución administrada de AKS. La versión/región/canal disponibles para el upgrade y la relación futura de node images/add-ons requieren evidencia específica de Microsoft; `AKS-SUPPORT-UNVERIFIED` permanece UNKNOWN. No se inventa una matriz de add-ons a partir de que estén habilitados.

### Upgrade Readiness Score y tabla ejecutiva

El HTML muestra producto/namespace, versiones observadas, fuente de detección, compatibilidad con el objetivo, resultado y enlaces oficiales. Incluye metadata de AKS, evidencia de detección, matrices y el score. El consolidado añade score y decisión por contexto, y conserva el detalle íntegro dentro del mismo archivo.

Pesos: operadores 40%, CRDs 25%, Pluto 15%, add-ons AKS 10% y storage/snapshot 10%. Cada producto se asigna a una categoría principal para evitar duplicar su peso. Storage incluye comprobaciones de almacenamiento de CRDs y productos CSI/snapshot/backup. El estado más conservador de la categoría determina puntos: PASS=100%, WARN=50%, UNKNOWN/FAIL/ERROR=0%. Las categorías sin componentes aplicables y con inventario completo se marcan N/A y se normaliza el peso restante; inventario incompleto nunca obtiene N/A por mera ausencia.

`READY` requiere score >=90 y ausencia de FAIL, ERROR, WARN o UNKNOWN en todo el informe, incluidas cobertura, instancias y soporte administrado. Un solo FAIL/ERROR da `BLOCKED`; cualquier evidencia pendiente da `ATTENTION REQUIRED`. Muchos PASS no diluyen un bloqueo. El score es una ayuda de revisión y no una garantía absoluta de upgrade. Su fórmula y pesos se publican en JSON/HTML/Markdown.

### Offline y ejemplos

```sh
python main.py --input fixtures/mixed-crds.json --platform-input fixtures/platform-inventory.json --current 1.34.8 --target-version 1.35.9 --output reports/examples --format all
python fixtures/generate_consolidated_example.py
```

El snapshot sintético demuestra Argo CD, Gatekeeper e Istio con evidencia diferenciada; el comando devuelve 1 por bloqueos deliberados. Sin `--platform-input`, offline registra que no hay inventario, sin ejecutar herramientas ni acceder a la red. Un snapshot requiere `schema_version: 1`, `kubernetes_version` igual a `--current` y listas JSON con claves `deployments.apps`, `daemonsets.apps`, `statefulsets.apps`, `pods`, `nodes` y `helm`. Puede incluir las claves de APIs específicas usadas en el fixture y metadata `aks`. Las fuentes omitidas generan UNKNOWN. En LIVE, un snapshot debe declarar además `context` idéntico al contexto fijado.

Se preservan los modos anteriores y la ausencia de CI automático. Las pruebas de descubrimiento, Azure, scoring, catálogos y reportes usan respuestas simuladas; no se ha verificado un clúster de producción ni se han ejecutado escrituras.

Verificación de v0.3: **167 pruebas aprobadas** localmente. Incluyen un caso de detección por imagen para cada producto, separación chart/appVersion y Calico/Tigera, versiones mezcladas, tags desconocidos, RBAC, asociación de AKS, vigencia de matrices, fin de soporte, aislamiento offline, comandos con contexto explícito y score que no oculta bloqueos. El informe JSON pasa al esquema 1.2 con campos aditivos `platform` y `readiness`.
