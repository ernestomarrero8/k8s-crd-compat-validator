# Kubernetes CRD Compatibility Validator

Clúster: offline:mixed\-crds\.json · 1\.34\.8 → 1\.35\.9

Fecha UTC: 2026\-11\-04T13:35:38\.716062\+00:00 · Estado general: **FAIL**

CRDs: 6 · Consultas kubectl: 0

| Estado | CRDs |
|---|---:|
| PASS | 0 |
| UNKNOWN | 1 |
| WARN | 2 |
| FAIL | 3 |
| ERROR | 0 |

| Severidad de riesgos | Hallazgos |
|---|---:|
| CRITICAL | 0 |
| HIGH | 5 |
| MEDIUM | 2 |
| LOW | 1 |
| INFO | 0 |

## Alcance y limitaciones

- PASS solo acredita las comprobaciones realizadas, no garantiza el upgrade\.
- La detección de APIs nativas se delega en Pluto; consultar su sección y estado\.
- No se prueban escrituras, reconciliación, CEL completo ni versiones persistidas por objeto\.
- La cobertura documental y los hashes del catálogo se registran en este informe\.
- No se exportan cuerpos de Custom Resources, annotations completas, kubeconfig, certificados ni stderr de kubectl\.

## Catálogos utilizados

\{"coverage\_catalog\_version": "2026\.11\.04\.1", "coverage\_sha256": "01c7959a428e1d9bd32229cc54106f3c99561db1d83601b8558cb8108c6b16fb", "rule\_catalogs": \{"files": \[\{"file": "kubernetes\.json", "sha256": "cce532134940543b129e563ec8b27f20a2fea82d72553738d4193731bd9fca78", "catalog\_version": "2026\.11\.04\.1"\}\], "rules\_sha256": "84bf20919b949d4bb9141c0fb86710f5147ecd1e00116d18e9b0a7654936ff5e"\}\}

## Pluto

UNKNOWN: Pluto no se ejecuta en modo offline\.

Comando: No ejecutado

<pre></pre>


## Hallazgos globales

### RULE\-COVERAGE · UNKNOWN · INFO

Cobertura documental del trayecto solicitado; el alcance se limita a las categorías registradas\.

Categoría: rules · Relación: documented · Método: static

Evidencia: \{"catalog\_version": "2026\.11\.04\.1", "sha256": "01c7959a428e1d9bd32229cc54106f3c99561db1d83601b8558cb8108c6b16fb", "reviews": \[\{"current\_min": "1\.34\.0", "current\_max": "1\.34\.999", "target\_min": "1\.35\.0", "target\_max": "1\.35\.999", "status": "partial", "categories": \["schema", "structure", "conversion\_webhook", "storage"\], "reviewed\_on": "2026\-10\-29", "reviewer": "Initial project implementation", "source": "https://github\.com/kubernetes/kubernetes/blob/v1\.35\.0/CHANGELOG/CHANGELOG\-1\.35\.md", "limitations": \["Selección de cambios minor; parches exactos, backports, feature gates y proveedores no revisados exhaustivamente\."\]\}\], "steps": \[\{"current": "1\.34\.8", "target": "1\.35\.9", "status": "partial"\}\]\}

Recomendación: Revisar categorías, parches y distribuciones pendientes antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

- Límite: Una revisión sin cambios relevantes no equivale a ausencia de revisión ni certifica compatibilidad completa\.
### PLUTO\-SCAN · UNKNOWN · INFO

Pluto no se ejecuta en modo offline\.

Categoría: native\_api\_deprecations · Relación: limitation · Método: external\_tool

Evidencia: \{"exit\_code": null, "executed": false\}

Recomendación: Revisar la sección Pluto y mantener actualizado el binario y su catálogo de APIs\.

Fuente: [Referencia técnica](<https://pluto.docs.fairwinds.com/advanced/>)

- Límite: Pluto tiene su propio catálogo de APIs; un resultado limpio no prueba cobertura de versiones futuras\.
- Límite: La detección depende de los objetos y metadatos disponibles para Pluto\.

## widgets\.example\.com — UNKNOWN / INFO

### STRUCTURE\-BASIC · PASS · INFO

Identidad, scope, nombres y versiones con estructura válida\.

Categoría: structure · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### STORAGE\-CONSISTENT · PASS · INFO

Declaraciones served, storage y storedVersions coherentes\.

Categoría: storage · Relación: preexisting · Método: static

Evidencia: \{"served": \["v1alpha1"\], "storage": \["v1alpha1"\], "stored\_versions": \["v1alpha1"\]\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

### SCHEMA\-STATIC · PASS · INFO

No se detectaron errores en el subconjunto estático del esquema\.

Categoría: schema · Relación: preexisting · Método: static

Evidencia: \{"path": "spec\.versions\[v1alpha1\]\.schema\.openAPIV3Schema"\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

- Límite: No valida completamente defaults, regex RE2, formatos, CEL, admisión o datos persistidos\.
### CONVERSION\-NONE · PASS · INFO

Conversión None: no hay dependencia de un webhook\.

Categoría: conversion\_webhook · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

### OPERATOR\-IDENTITY · PASS · INFO

Candidatos a operador responsable\.

Categoría: operator · Relación: documented · Método: static

Evidencia: \{"candidates": \[\{"name": "example\-operator", "version": "2\.0\.0", "basis": "crd\_labels", "confidence": "hint"\}\]\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

- Límite: Labels y Helm son indicios; un release o chart puede no identificar la versión del controlador\.
### OPERATOR\-SUPPORT · UNKNOWN · INFO

No hay una única matriz revisada que coincida con operador, versión y CRD\.

Categoría: operator · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Obtener la matriz oficial del proveedor y registrar evidencia en \-\-operator\-catalog; no inferir soporte por Running\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### K135\-CONDITION\-GENERATION · PASS · INFO

1\.35 incorpora observedGeneration en condiciones de CRDs\.

Categoría: structure · Relación: release\_change · Método: static

Evidencia: \{"basis": "Cambio aditivo documentado en las notas 1\.35, PR 134984\.", "applicability": \{"crosses": "1\.35\.0"\}, "condition\_matched": true\}

Recomendación: Revisar deserializadores estrictos en clientes propios que consuman condiciones de CRDs\.

Fuente: [Referencia técnica](<https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.35.md>)

- Límite: No se inspecciona el cÃ³digo del operador; este cambio no es un bloqueo por sÃ­ mismo\.
### INSTANCES\-NOT\-REQUESTED · UNKNOWN · INFO

Instancias no inspeccionadas; usar \-\-include\-instances para lectura limitada\.

Categoría: instances · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)


## broken\-schemas\.example\.com — FAIL / HIGH

### STRUCTURE\-BASIC · PASS · INFO

Identidad, scope, nombres y versiones con estructura válida\.

Categoría: structure · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### STORAGE\-CONSISTENT · PASS · INFO

Declaraciones served, storage y storedVersions coherentes\.

Categoría: storage · Relación: preexisting · Método: static

Evidencia: \{"served": \["v1alpha1"\], "storage": \["v1alpha1"\], "stored\_versions": \["v1alpha1"\]\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

### SCHEMA\-TYPE · FAIL · HIGH

Tipo ausente o no válido en un nodo estructural\.

Categoría: schema · Relación: preexisting · Método: static

Evidencia: \{"path": "spec\.versions\[v1alpha1\]\.schema\.openAPIV3Schema\.properties\.spec\.properties\.replicas"\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### CONVERSION\-NONE · PASS · INFO

Conversión None: no hay dependencia de un webhook\.

Categoría: conversion\_webhook · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

### OPERATOR\-IDENTITY · PASS · INFO

Candidatos a operador responsable\.

Categoría: operator · Relación: documented · Método: static

Evidencia: \{"candidates": \[\{"name": "example\-operator", "version": "2\.0\.0", "basis": "crd\_labels", "confidence": "hint"\}\]\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

- Límite: Labels y Helm son indicios; un release o chart puede no identificar la versión del controlador\.
### OPERATOR\-SUPPORT · UNKNOWN · INFO

No hay una única matriz revisada que coincida con operador, versión y CRD\.

Categoría: operator · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Obtener la matriz oficial del proveedor y registrar evidencia en \-\-operator\-catalog; no inferir soporte por Running\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### K135\-CONDITION\-GENERATION · PASS · INFO

1\.35 incorpora observedGeneration en condiciones de CRDs\.

Categoría: structure · Relación: release\_change · Método: static

Evidencia: \{"basis": "Cambio aditivo documentado en las notas 1\.35, PR 134984\.", "applicability": \{"crosses": "1\.35\.0"\}, "condition\_matched": true\}

Recomendación: Revisar deserializadores estrictos en clientes propios que consuman condiciones de CRDs\.

Fuente: [Referencia técnica](<https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.35.md>)

- Límite: No se inspecciona el cÃ³digo del operador; este cambio no es un bloqueo por sÃ­ mismo\.
### INSTANCES\-NOT\-REQUESTED · UNKNOWN · INFO

Instancias no inspeccionadas; usar \-\-include\-instances para lectura limitada\.

Categoría: instances · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)


## retired\-versions\.example\.com — FAIL / HIGH

### STRUCTURE\-BASIC · PASS · INFO

Identidad, scope, nombres y versiones con estructura válida\.

Categoría: structure · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### STORED\-INCONSISTENT · FAIL · HIGH

Versiones persistidas y declaradas inconsistentes\.

Categoría: storage · Relación: preexisting · Método: static

Evidencia: \{"stored\_versions": \["v1alpha1", "retired"\], "undeclared\_versions": \["retired"\], "storage": \["v1alpha1"\]\}

Recomendación: Verificar la migración de objetos antes de retirar versiones; no modificar el status sin evidencia\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

### STORED\-MIGRATION · WARN · MEDIUM

El status conserva varias versiones de almacenamiento\.

Categoría: storage · Relación: preexisting · Método: static

Evidencia: \{"stored\_versions": \["v1alpha1", "retired"\]\}

Recomendación: Auditar la migración; cambiar storage no reescribe los objetos existentes\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

- Límite: storedVersions es histórico; no prueba que aún existan objetos en cada versión\.
### SCHEMA\-STATIC · PASS · INFO

No se detectaron errores en el subconjunto estático del esquema\.

Categoría: schema · Relación: preexisting · Método: static

Evidencia: \{"path": "spec\.versions\[v1alpha1\]\.schema\.openAPIV3Schema"\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

- Límite: No valida completamente defaults, regex RE2, formatos, CEL, admisión o datos persistidos\.
### CONVERSION\-NONE · PASS · INFO

Conversión None: no hay dependencia de un webhook\.

Categoría: conversion\_webhook · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

### OPERATOR\-IDENTITY · PASS · INFO

Candidatos a operador responsable\.

Categoría: operator · Relación: documented · Método: static

Evidencia: \{"candidates": \[\{"name": "example\-operator", "version": "2\.0\.0", "basis": "crd\_labels", "confidence": "hint"\}\]\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

- Límite: Labels y Helm son indicios; un release o chart puede no identificar la versión del controlador\.
### OPERATOR\-SUPPORT · UNKNOWN · INFO

No hay una única matriz revisada que coincida con operador, versión y CRD\.

Categoría: operator · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Obtener la matriz oficial del proveedor y registrar evidencia en \-\-operator\-catalog; no inferir soporte por Running\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### K135\-CONDITION\-GENERATION · PASS · INFO

1\.35 incorpora observedGeneration en condiciones de CRDs\.

Categoría: structure · Relación: release\_change · Método: static

Evidencia: \{"basis": "Cambio aditivo documentado en las notas 1\.35, PR 134984\.", "applicability": \{"crosses": "1\.35\.0"\}, "condition\_matched": true\}

Recomendación: Revisar deserializadores estrictos en clientes propios que consuman condiciones de CRDs\.

Fuente: [Referencia técnica](<https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.35.md>)

- Límite: No se inspecciona el cÃ³digo del operador; este cambio no es un bloqueo por sÃ­ mismo\.
### INSTANCES\-NOT\-REQUESTED · UNKNOWN · INFO

Instancias no inspeccionadas; usar \-\-include\-instances para lectura limitada\.

Categoría: instances · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)


## broken\-webhooks\.example\.com — FAIL / HIGH

### STRUCTURE\-BASIC · PASS · INFO

Identidad, scope, nombres y versiones con estructura válida\.

Categoría: structure · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### STORAGE\-CONSISTENT · PASS · INFO

Declaraciones served, storage y storedVersions coherentes\.

Categoría: storage · Relación: preexisting · Método: static

Evidencia: \{"served": \["v1alpha1"\], "storage": \["v1alpha1"\], "stored\_versions": \["v1alpha1"\]\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

### SCHEMA\-STATIC · PASS · INFO

No se detectaron errores en el subconjunto estático del esquema\.

Categoría: schema · Relación: preexisting · Método: static

Evidencia: \{"path": "spec\.versions\[v1alpha1\]\.schema\.openAPIV3Schema"\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

- Límite: No valida completamente defaults, regex RE2, formatos, CEL, admisión o datos persistidos\.
### CONVERSION\-REVIEW · FAIL · HIGH

Ningún protocolo declarado coincide con los documentados para el objetivo\.

Categoría: conversion\_webhook · Relación: upgrade · Método: static

Evidencia: \{"declared": \["v9"\], "supported": \["v1", "v1beta1"\]\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

### CONVERSION\-SERVICE · FAIL · HIGH

Referencia a Service, puerto o path inválidos\.

Categoría: conversion\_webhook · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

### CONVERSION\-CA · FAIL · HIGH

caBundle no contiene certificados PEM válidos codificados en base64\.

Categoría: conversion\_webhook · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

### CONVERSION\-TARGET · UNKNOWN · INFO

Conversión y TLS en el API Server objetivo no demostrados\.

Categoría: conversion\_webhook · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Verificar confianza TLS, SAN, expiración, red y conversiones bidireccionales con datos representativos en un entorno aislado\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

- Límite: Parsear la CA o encontrar endpoints no verifica handshake, cadena, caducidad ni conversión\.
### OPERATOR\-IDENTITY · PASS · INFO

Candidatos a operador responsable\.

Categoría: operator · Relación: documented · Método: static

Evidencia: \{"candidates": \[\{"name": "example\-operator", "version": "2\.0\.0", "basis": "crd\_labels", "confidence": "hint"\}\]\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

- Límite: Labels y Helm son indicios; un release o chart puede no identificar la versión del controlador\.
### OPERATOR\-SUPPORT · UNKNOWN · INFO

No hay una única matriz revisada que coincida con operador, versión y CRD\.

Categoría: operator · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Obtener la matriz oficial del proveedor y registrar evidencia en \-\-operator\-catalog; no inferir soporte por Running\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### K135\-CONDITION\-GENERATION · PASS · INFO

1\.35 incorpora observedGeneration en condiciones de CRDs\.

Categoría: structure · Relación: release\_change · Método: static

Evidencia: \{"basis": "Cambio aditivo documentado en las notas 1\.35, PR 134984\.", "applicability": \{"crosses": "1\.35\.0"\}, "condition\_matched": true\}

Recomendación: Revisar deserializadores estrictos en clientes propios que consuman condiciones de CRDs\.

Fuente: [Referencia técnica](<https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.35.md>)

- Límite: No se inspecciona el cÃ³digo del operador; este cambio no es un bloqueo por sÃ­ mismo\.
### INSTANCES\-NOT\-REQUESTED · UNKNOWN · INFO

Instancias no inspeccionadas; usar \-\-include\-instances para lectura limitada\.

Categoría: instances · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)


## cel\-widgets\.example\.com — WARN / LOW

### STRUCTURE\-BASIC · PASS · INFO

Identidad, scope, nombres y versiones con estructura válida\.

Categoría: structure · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### STORAGE\-CONSISTENT · PASS · INFO

Declaraciones served, storage y storedVersions coherentes\.

Categoría: storage · Relación: preexisting · Método: static

Evidencia: \{"served": \["v1alpha1"\], "storage": \["v1alpha1"\], "stored\_versions": \["v1alpha1"\]\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

### SCHEMA\-CEL\-UNVERIFIED · UNKNOWN · INFO

CEL detectado; compilación, coste y transición no verificados\.

Categoría: schema · Relación: limitation · Método: static

Evidencia: \{"path": "spec\.versions\[v1alpha1\]\.schema\.openAPIV3Schema\.properties\.spec"\}

Recomendación: Probar creación y actualización de objetos representativos en el API Server objetivo\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

- Límite: No se ejecuta CEL ni se publican expresiones o valores de recursos\.
### CONVERSION\-NONE · PASS · INFO

Conversión None: no hay dependencia de un webhook\.

Categoría: conversion\_webhook · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

### OPERATOR\-IDENTITY · PASS · INFO

Candidatos a operador responsable\.

Categoría: operator · Relación: documented · Método: static

Evidencia: \{"candidates": \[\{"name": "example\-operator", "version": "2\.0\.0", "basis": "crd\_labels", "confidence": "hint"\}\]\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

- Límite: Labels y Helm son indicios; un release o chart puede no identificar la versión del controlador\.
### OPERATOR\-SUPPORT · UNKNOWN · INFO

No hay una única matriz revisada que coincida con operador, versión y CRD\.

Categoría: operator · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Obtener la matriz oficial del proveedor y registrar evidencia en \-\-operator\-catalog; no inferir soporte por Running\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### K135\-CEL\-ERROR\-VALUES · WARN · LOW

Kubernetes 1\.35 puede incluir valores simples en errores de validaciÃ³n CEL\.

Categoría: schema · Relación: upgrade · Método: static

Evidencia: \{"basis": "PR 132798 modifica los errores CEL; la definiciÃ³n contiene reglas CEL\.", "applicability": \{"crosses": "1\.35\.0"\}, "condition\_matched": true\}

Recomendación: Revisar consumidores que comparen mensajes textuales y la redacciÃ³n de datos sensibles en logs\.

Fuente: [Referencia técnica](<https://github.com/kubernetes/kubernetes/pull/132798>)

- Límite: Es un cambio de diagnÃ³stico, no una incompatibilidad de la expresiÃ³n CEL demostrada\.
### K135\-CONDITION\-GENERATION · PASS · INFO

1\.35 incorpora observedGeneration en condiciones de CRDs\.

Categoría: structure · Relación: release\_change · Método: static

Evidencia: \{"basis": "Cambio aditivo documentado en las notas 1\.35, PR 134984\.", "applicability": \{"crosses": "1\.35\.0"\}, "condition\_matched": true\}

Recomendación: Revisar deserializadores estrictos en clientes propios que consuman condiciones de CRDs\.

Fuente: [Referencia técnica](<https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.35.md>)

- Límite: No se inspecciona el cÃ³digo del operador; este cambio no es un bloqueo por sÃ­ mismo\.
### INSTANCES\-NOT\-REQUESTED · UNKNOWN · INFO

Instancias no inspeccionadas; usar \-\-include\-instances para lectura limitada\.

Categoría: instances · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)


## migrating\-widgets\.example\.com — WARN / MEDIUM

### STRUCTURE\-BASIC · PASS · INFO

Identidad, scope, nombres y versiones con estructura válida\.

Categoría: structure · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### STORED\-MIGRATION · WARN · MEDIUM

El status conserva varias versiones de almacenamiento\.

Categoría: storage · Relación: preexisting · Método: static

Evidencia: \{"stored\_versions": \["v1alpha1", "v1"\]\}

Recomendación: Auditar la migración; cambiar storage no reescribe los objetos existentes\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

- Límite: storedVersions es histórico; no prueba que aún existan objetos en cada versión\.
### SCHEMA\-STATIC · PASS · INFO

No se detectaron errores en el subconjunto estático del esquema\.

Categoría: schema · Relación: preexisting · Método: static

Evidencia: \{"path": "spec\.versions\[v1alpha1\]\.schema\.openAPIV3Schema"\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

- Límite: No valida completamente defaults, regex RE2, formatos, CEL, admisión o datos persistidos\.
### SCHEMA\-STATIC · PASS · INFO

No se detectaron errores en el subconjunto estático del esquema\.

Categoría: schema · Relación: preexisting · Método: static

Evidencia: \{"path": "spec\.versions\[v1\]\.schema\.openAPIV3Schema"\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

- Límite: No valida completamente defaults, regex RE2, formatos, CEL, admisión o datos persistidos\.
### CONVERSION\-NONE · PASS · INFO

Conversión None: no hay dependencia de un webhook\.

Categoría: conversion\_webhook · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

### OPERATOR\-IDENTITY · PASS · INFO

Candidatos a operador responsable\.

Categoría: operator · Relación: documented · Método: static

Evidencia: \{"candidates": \[\{"name": "example\-operator", "version": "2\.0\.0", "basis": "crd\_labels", "confidence": "hint"\}\]\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

- Límite: Labels y Helm son indicios; un release o chart puede no identificar la versión del controlador\.
### OPERATOR\-SUPPORT · UNKNOWN · INFO

No hay una única matriz revisada que coincida con operador, versión y CRD\.

Categoría: operator · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Obtener la matriz oficial del proveedor y registrar evidencia en \-\-operator\-catalog; no inferir soporte por Running\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### K135\-CONDITION\-GENERATION · PASS · INFO

1\.35 incorpora observedGeneration en condiciones de CRDs\.

Categoría: structure · Relación: release\_change · Método: static

Evidencia: \{"basis": "Cambio aditivo documentado en las notas 1\.35, PR 134984\.", "applicability": \{"crosses": "1\.35\.0"\}, "condition\_matched": true\}

Recomendación: Revisar deserializadores estrictos en clientes propios que consuman condiciones de CRDs\.

Fuente: [Referencia técnica](<https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.35.md>)

- Límite: No se inspecciona el cÃ³digo del operador; este cambio no es un bloqueo por sÃ­ mismo\.
### INSTANCES\-NOT\-REQUESTED · UNKNOWN · INFO

Instancias no inspeccionadas; usar \-\-include\-instances para lectura limitada\.

Categoría: instances · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

