# Kubernetes CRD Compatibility Validator

Clúster: offline:mixed\-crds\.json · 1\.34\.8 → 1\.35\.9

Fecha UTC: 2026\-11\-04T16:18:34\.859271\+00:00 · Estado general: **FAIL**

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
| HIGH | 6 |
| MEDIUM | 3 |
| LOW | 1 |
| INFO | 0 |

## Upgrade Readiness Score

0.0/100 · BLOCKED

Worst finding per category\. PASS=100%, WARN=50%, UNKNOWN/FAIL/ERROR=0%; N/A excluded and remaining weights normalized\.

El score es una ayuda de revisión; READY exige ausencia de bloqueos, avisos y evidencia pendiente en todo el informe\.

## Cluster Platform Compatibility — OPERATOR COMPATIBILITY ANALYSIS

| Producto | Versiones | Origen | Compatibilidad | Resultado |
|---|---|---|---|---|
| Argo CD | v3\.2\.0, 3\.2\.0 | Helm, deployments\.apps | No verificada | UNKNOWN |
| Istio | 1\.21\.1 | deployments\.apps | No | FAIL |
| Gatekeeper | v3\.17\.0 | deployments\.apps | No verificada | UNKNOWN |

AKS: \{"detected": false, "target\_version": "1\.35\.9", "current\_version": null, "node\_image\_versions": \[\], "node\_kubelet\_versions": \[\], "addons": \[\], "limitations": \["Metadata AKS observada; la versión efectiva y soporte de cada add\-on se evalúan por separado\.", "Una versión Kubernetes soportada upstream no acredita disponibilidad de upgrade, región, canal LTS ni soporte del add\-on administrado en AKS\.", "Node images se inventarían; no se infiere compatibilidad futura por su nombre\."\]\}


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
### OPERATOR\-NO\-MATRIX · UNKNOWN · INFO

Objetivo fuera de las versiones probadas; esto no demuestra incompatibilidad\.

Categoría: operator\_compatibility · Relación: documented · Método: static

Evidencia: \{"product": "Argo CD", "installed\_version": "v3\.2\.0", "target": "1\.35\.9", "matrix": \{"version": "3\.2\.x", "min\_kubernetes": "1\.31\.0", "max\_kubernetes": "1\.34\.x", "matrix\_type": "tested", "exclusive": false, "source": "https://argo\-cd\.readthedocs\.io/en/release\-3\.2/operator\-manual/tested\-kubernetes\-versions/", "reviewed\_on": "2026\-11\-04", "valid\_until": "2027\-02\-02", "evidence": "La tabla de la rama release\-3\.2 enumera Kubernetes 1\.31 a 1\.34 como probados\. Fuera de esa lista no se acredita incompatibilidad ni soporte\."\}\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://argo-cd.readthedocs.io/en/release-3.2/operator-manual/tested-kubernetes-versions/>)

### OPERATOR\-NO\-MATRIX · UNKNOWN · INFO

Objetivo fuera de las versiones probadas; esto no demuestra incompatibilidad\.

Categoría: operator\_compatibility · Relación: documented · Método: static

Evidencia: \{"product": "Argo CD", "installed\_version": "3\.2\.0", "target": "1\.35\.9", "matrix": \{"version": "3\.2\.x", "min\_kubernetes": "1\.31\.0", "max\_kubernetes": "1\.34\.x", "matrix\_type": "tested", "exclusive": false, "source": "https://argo\-cd\.readthedocs\.io/en/release\-3\.2/operator\-manual/tested\-kubernetes\-versions/", "reviewed\_on": "2026\-11\-04", "valid\_until": "2027\-02\-02", "evidence": "La tabla de la rama release\-3\.2 enumera Kubernetes 1\.31 a 1\.34 como probados\. Fuera de esa lista no se acredita incompatibilidad ni soporte\."\}\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://argo-cd.readthedocs.io/en/release-3.2/operator-manual/tested-kubernetes-versions/>)

### OPERATOR\-END\-OF\-SUPPORT · WARN · MEDIUM

Versión fuera de mantenimiento según la fecha oficial registrada\.

Categoría: operator\_compatibility · Relación: documented · Método: static

Evidencia: \{"product": "Istio", "installed\_version": "1\.21\.1", "target": "1\.35\.9", "matrix": \{"version": "1\.21\.x", "min\_kubernetes": "1\.26\.0", "max\_kubernetes": "1\.29\.x", "matrix\_type": "supported", "exclusive": true, "end\_of\_support": "2024\-09\-27", "source": "https://istio\.io/latest/docs/releases/supported\-releases/", "reviewed\_on": "2026\-11\-04", "valid\_until": "2027\-02\-02", "evidence": "Fila 1\.21: Kubernetes soportados 1\.26 a 1\.29; EOL 27 septiembre 2024\."\}\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://istio.io/latest/docs/releases/supported-releases/>)

### OPERATOR\-NOT\-COMPATIBLE · FAIL · HIGH

Objetivo fuera del rango de soporte explícito del proveedor; no se recomienda este upgrade con la versión instalada\.

Categoría: operator\_compatibility · Relación: documented · Método: static

Evidencia: \{"product": "Istio", "installed\_version": "1\.21\.1", "target": "1\.35\.9", "matrix": \{"version": "1\.21\.x", "min\_kubernetes": "1\.26\.0", "max\_kubernetes": "1\.29\.x", "matrix\_type": "supported", "exclusive": true, "end\_of\_support": "2024\-09\-27", "source": "https://istio\.io/latest/docs/releases/supported\-releases/", "reviewed\_on": "2026\-11\-04", "valid\_until": "2027\-02\-02", "evidence": "Fila 1\.21: Kubernetes soportados 1\.26 a 1\.29; EOL 27 septiembre 2024\."\}\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://istio.io/latest/docs/releases/supported-releases/>)

### OPERATOR\-NO\-MATRIX · UNKNOWN · INFO

No existe una única fila de matriz oficial revisada para esta versión\.

Categoría: operator\_compatibility · Relación: limitation · Método: static

Evidencia: \{"product": "Gatekeeper", "installed\_version": "v3\.17\.0", "target": "1\.35\.9", "matrix": \{\}\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://open-policy-agent.github.io/gatekeeper/>)

### PLATFORM\-DISCOVERY · PASS · INFO

Cobertura del descubrimiento de plataformas\.

Categoría: operator\_compatibility · Relación: tested · Método: snapshot

Evidencia: \{"errors": \[\], "products\_detected": 3\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

- Límite: Detectores por repositorios y charts conocidos\. Mirrors privados, productos no catalogados y planos administrados pueden no ser visibles\.
- Límite: La versión de tag/Helm es evidencia declarada, no una verificación del binario por digest\.
- Límite: Las listas de workloads se descargan completas dentro del timeout y se examinan hasta el límite configurado\.
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

