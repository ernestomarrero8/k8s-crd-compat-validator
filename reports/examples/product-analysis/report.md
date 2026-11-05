# Kubernetes CRD Compatibility Validator

Clúster: offline:product\-crds\.json · 1\.34\.8 → 1\.35\.9

Fecha UTC: 2026\-11\-05T14:51:23\.187735\+00:00 · Estado general: **FAIL**

CRDs: 3 · Consultas kubectl: 0

| Estado | CRDs |
|---|---:|
| PASS | 0 |
| UNKNOWN | 2 |
| WARN | 0 |
| FAIL | 1 |
| ERROR | 0 |

| Severidad de riesgos | Hallazgos |
|---|---:|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 1 |
| LOW | 0 |
| INFO | 0 |

## Upgrade Readiness Score

78.4/100 · BLOCKED

One unit per product/technical CRD/storage CRD and one Pluto unit\. Weighted compatibility over evaluated PASS=100%, WARN=50%, FAIL=0% units only; UNKNOWN/ERROR excluded from compatibility, retained in coverage\. Evidence coverage = evaluated/applicable units\. PRODUCT\_SUPPORT references have zero additional weight\.

El score es una ayuda de revisión; READY exige ausencia de bloqueos, avisos y evidencia pendiente en todo el informe\.

Cobertura de evidencia: 80.0% · Compatibilidad de unidades evaluadas: 78.4/100


## Cluster Platform Compatibility — OPERATOR COMPATIBILITY ANALYSIS

| Producto | Versiones | Origen | Compatibilidad | Resultado |
|---|---|---|---|---|
| Argo CD | v3\.2\.0 | deployments\.apps | No verificada | UNKNOWN |
| Istio | 1\.30\.7 | deployments\.apps, istioctl control plane | Sí, según evidencia documentada | PASS |
| Cert Manager | v1\.16\.0 | deployments\.apps | No | FAIL |

AKS: \{"detected": false, "target\_version": "1\.35\.9", "current\_version": null, "node\_image\_versions": \[\], "node\_kubelet\_versions": \[\], "addons": \[\], "limitations": \["Metadata AKS observada; la versión efectiva y soporte de cada add\-on se evalúan por separado\.", "Una versión Kubernetes soportada upstream no acredita disponibilidad de upgrade, región, canal LTS ni soporte del add\-on administrado en AKS\.", "Node images se inventarían; no se infiere compatibilidad futura por su nombre\."\]\}


| CRD | Producto | Soporte producto | Riesgo upgrade |
|---|---|---|---|
| virtualservices\.networking\.istio\.io | Istio | PASS | INFO |
| appprojects\.argoproj\.io | Argo CD | UNKNOWN | INFO |
| certificates\.cert\-manager\.io | Cert Manager | FAIL | HIGH |

## Alcance y limitaciones

- PASS solo acredita las comprobaciones realizadas, no garantiza el upgrade\.
- La detección de APIs nativas se delega en Pluto; consultar su sección y estado\.
- No se prueban escrituras, reconciliación, CEL completo ni versiones persistidas por objeto\.
- La cobertura documental y los hashes del catálogo se registran en este informe\.
- No se exportan cuerpos de Custom Resources, annotations completas, kubeconfig, certificados ni stderr de kubectl\.

## Catálogos utilizados

\{"coverage\_catalog\_version": "2026\.11\.04\.1", "coverage\_sha256": "01c7959a428e1d9bd32229cc54106f3c99561db1d83601b8558cb8108c6b16fb", "rule\_catalogs": \{"files": \[\{"file": "kubernetes\.json", "sha256": "84fb46082fe596ffab851a394a6a45db6ff757f8247a3fb7a4a4135df3dd0dbc", "catalog\_version": "2026\.11\.05\.1"\}\], "rules\_sha256": "64f5de123ca9fb3a2bf2fe631926b3ded16231175dabcc19b0c6e8f45dcb6e07"\}\}

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
### NO\_SUPPORT\_DATA · UNKNOWN · INFO

Objetivo fuera de las versiones probadas; esto no demuestra incompatibilidad\.

Categoría: operator\_compatibility · Relación: documented · Método: static

Evidencia: \{"product": "Argo CD", "installed\_version": "3\.2\.0", "target": "1\.35\.9", "matrix": \{"version": "3\.2\.x", "min\_kubernetes": "1\.31\.0", "max\_kubernetes": "1\.34\.x", "matrix\_type": "tested", "exclusive": false, "source": "https://argo\-cd\.readthedocs\.io/en/release\-3\.2/operator\-manual/tested\-kubernetes\-versions/", "reviewed\_on": "2026\-11\-04", "valid\_until": "2027\-02\-02", "evidence": "La tabla de la rama release\-3\.2 enumera Kubernetes 1\.31 a 1\.34 como probados\. Fuera de esa lista no se acredita incompatibilidad ni soporte\.", "support\_state": "supported"\}, "detected\_version": "3\.2\.0", "version\_confidence": "image\_tag", "catalog\_lookup": \{"catalog\_present": true, "files": \["argocd\.json"\], "paths": \["catalogs/support/argocd\.json"\], "available\_selectors": \["3\.2\.x"\], "matched\_selectors": \["3\.2\.x"\], "selected\_selector": "3\.2\.x", "normalized\_version": "3\.2\.0", "reason": "matched"\}, "distribution\_revision": null, "reviewed\_on": "2026\-11\-04", "catalog\_limitations": \[\], "detection\_sources": \[\{"from": "deployments\.apps", "namespace": "argocd", "name": "argocd\-server", "repository": "quay\.io/argoproj/argocd", "declared\_tag": "v3\.2\.0", "revision": null, "identity\_basis": "catalog\_repository", "confidence": "image\_tag", "activity": "active", "observed\_status": \{\}, "version\_label": null, "version\_basis": "workload\_template\_image\_tag"\}\], "resolution\_sources": \["deployments\.apps"\], "resolved\_versions": \["3\.2\.0"\], "raw\_detected\_versions": \["v3\.2\.0"\]\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://argo-cd.readthedocs.io/en/release-3.2/operator-manual/tested-kubernetes-versions/>)

### COMPATIBLE · PASS · INFO

Objetivo dentro del rango documentado; consultar si la evidencia acredita soporte o pruebas upstream\.

Categoría: operator\_compatibility · Relación: documented · Método: static

Evidencia: \{"product": "Istio", "installed\_version": "1\.30\.7", "target": "1\.35\.9", "matrix": \{"version": "1\.30\.x", "min\_kubernetes": "1\.32\.0", "max\_kubernetes": "1\.36\.x", "matrix\_type": "supported", "exclusive": true, "source": "https://istio\.io/latest/docs/releases/supported\-releases/", "reviewed\_on": "2026\-11\-04", "valid\_until": "2027\-02\-02", "evidence": "Fila 1\.30: Kubernetes soportados 1\.32 a 1\.36; evaluar también vigencia de mantenimiento\.", "support\_state": "supported"\}, "detected\_version": "1\.30\.7", "version\_confidence": "server\_cli", "catalog\_lookup": \{"catalog\_present": true, "files": \["istio\.json"\], "paths": \["catalogs/support/istio\.json"\], "available\_selectors": \["1\.30\.x", "1\.29\.x", "1\.28\.x", "1\.27\.x", "1\.26\.x", "1\.25\.x", "1\.24\.x", "1\.23\.x", "1\.22\.x", "1\.21\.x"\], "matched\_selectors": \["1\.30\.x"\], "selected\_selector": "1\.30\.x", "normalized\_version": "1\.30\.7", "reason": "matched"\}, "distribution\_revision": null, "reviewed\_on": "2026\-11\-04", "catalog\_limitations": \[\], "detection\_sources": \[\{"from": "deployments\.apps", "namespace": "istio\-system", "name": "istiod", "repository": "docker\.io/istio/pilot", "declared\_tag": "1\.30\.7", "revision": null, "identity\_basis": "catalog\_repository", "confidence": "image\_tag", "activity": "active", "observed\_status": \{\}, "version\_label": null, "version\_basis": "workload\_template\_image\_tag"\}, \{"from": "istioctl control plane", "component": "pilot", "revision": null, "activity": "active"\}\], "resolution\_sources": \["istioctl control plane"\], "resolved\_versions": \["1\.30\.7"\], "raw\_detected\_versions": \["1\.30\.7"\]\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://istio.io/latest/docs/releases/supported-releases/>)

### VERSION\_EOL · WARN · MEDIUM

Versión fuera de mantenimiento según la evidencia oficial registrada\.

Categoría: operator\_compatibility · Relación: documented · Método: static

Evidencia: \{"product": "Cert Manager", "installed\_version": "1\.16\.0", "target": "1\.35\.9", "matrix": \{"version": "1\.16\.x", "supported\_kubernetes": \{"min": "1\.25", "max": "1\.32"\}, "support\_state": "eol", "end\_of\_support": "2025\-06\-10", "source": "https://cert\-manager\.io/docs/releases/", "reviewed\_on": "2026\-11\-04", "evidence": "La tabla oficial de releases antiguas enumera compatibilidad 1\.25–1\.32 y EOL 10 junio 2025\.", "min\_kubernetes": "1\.25", "max\_kubernetes": "1\.32", "matrix\_type": "supported", "exclusive": true, "valid\_until": "2027\-02\-02"\}, "detected\_version": "1\.16\.0", "version\_confidence": "image\_tag", "catalog\_lookup": \{"catalog\_present": true, "files": \["cert\-manager\.json"\], "paths": \["catalogs/support/cert\-manager\.json"\], "available\_selectors": \["1\.16\.x", "1\.18\.x", "1\.19\.x", "1\.20\.x", "1\.21\.x"\], "matched\_selectors": \["1\.16\.x"\], "selected\_selector": "1\.16\.x", "normalized\_version": "1\.16\.0", "reason": "matched"\}, "distribution\_revision": null, "reviewed\_on": "2026\-11\-04", "catalog\_limitations": \[\], "detection\_sources": \[\{"from": "deployments\.apps", "namespace": "cert\-manager", "name": "cert\-manager", "repository": "quay\.io/jetstack/cert\-manager\-controller", "declared\_tag": "v1\.16\.0", "revision": null, "identity\_basis": "catalog\_repository", "confidence": "image\_tag", "activity": "active", "observed\_status": \{\}, "version\_label": null, "version\_basis": "workload\_template\_image\_tag"\}\], "resolution\_sources": \["deployments\.apps"\], "resolved\_versions": \["1\.16\.0"\], "raw\_detected\_versions": \["v1\.16\.0"\]\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://cert-manager.io/docs/releases/>)

### NOT\_COMPATIBLE · FAIL · HIGH

Objetivo fuera del rango de soporte explícito del proveedor; no se recomienda este upgrade con la versión instalada\.

Categoría: operator\_compatibility · Relación: documented · Método: static

Evidencia: \{"product": "Cert Manager", "installed\_version": "1\.16\.0", "target": "1\.35\.9", "matrix": \{"version": "1\.16\.x", "supported\_kubernetes": \{"min": "1\.25", "max": "1\.32"\}, "support\_state": "eol", "end\_of\_support": "2025\-06\-10", "source": "https://cert\-manager\.io/docs/releases/", "reviewed\_on": "2026\-11\-04", "evidence": "La tabla oficial de releases antiguas enumera compatibilidad 1\.25–1\.32 y EOL 10 junio 2025\.", "min\_kubernetes": "1\.25", "max\_kubernetes": "1\.32", "matrix\_type": "supported", "exclusive": true, "valid\_until": "2027\-02\-02"\}, "detected\_version": "1\.16\.0", "version\_confidence": "image\_tag", "catalog\_lookup": \{"catalog\_present": true, "files": \["cert\-manager\.json"\], "paths": \["catalogs/support/cert\-manager\.json"\], "available\_selectors": \["1\.16\.x", "1\.18\.x", "1\.19\.x", "1\.20\.x", "1\.21\.x"\], "matched\_selectors": \["1\.16\.x"\], "selected\_selector": "1\.16\.x", "normalized\_version": "1\.16\.0", "reason": "matched"\}, "distribution\_revision": null, "reviewed\_on": "2026\-11\-04", "catalog\_limitations": \[\], "detection\_sources": \[\{"from": "deployments\.apps", "namespace": "cert\-manager", "name": "cert\-manager", "repository": "quay\.io/jetstack/cert\-manager\-controller", "declared\_tag": "v1\.16\.0", "revision": null, "identity\_basis": "catalog\_repository", "confidence": "image\_tag", "activity": "active", "observed\_status": \{\}, "version\_label": null, "version\_basis": "workload\_template\_image\_tag"\}\], "resolution\_sources": \["deployments\.apps"\], "resolved\_versions": \["1\.16\.0"\], "raw\_detected\_versions": \["v1\.16\.0"\]\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://cert-manager.io/docs/releases/>)

### PLATFORM\-DISCOVERY · PASS · INFO

Cobertura del descubrimiento de plataformas\.

Categoría: operator\_compatibility · Relación: tested · Método: snapshot

Evidencia: \{"errors": \[\], "required\_errors": \[\], "detector\_errors": \[\], "inventory\_sources": \[\{"source": "deployments\.apps", "completed": true, "authorized": true, "error": null, "items\_scanned": 3, "required": true\}, \{"source": "daemonsets\.apps", "completed": true, "authorized": true, "error": null, "items\_scanned": 0, "required": true\}, \{"source": "statefulsets\.apps", "completed": true, "authorized": true, "error": null, "items\_scanned": 0, "required": true\}, \{"source": "pods", "completed": true, "authorized": true, "error": null, "items\_scanned": 0, "required": true\}, \{"source": "nodes", "completed": true, "authorized": true, "error": null, "items\_scanned": 0, "required": true\}, \{"source": "Helm", "completed": true, "authorized": true, "error": null, "items\_scanned": 0, "required": false\}\], "products\_detected": 3\}

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

## virtualservices\.networking\.istio\.io — UNKNOWN / INFO

### STRUCTURE\-BASIC · PASS · INFO

Identidad, scope, nombres y versiones con estructura válida\.

Categoría: structure · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### STORAGE\-CONSISTENT · PASS · INFO

Declaraciones served, storage y storedVersions coherentes\.

Categoría: storage · Relación: preexisting · Método: static

Evidencia: \{"served": \["v1"\], "storage": \["v1"\], "stored\_versions": \["v1"\]\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

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

### PRODUCT\_SUPPORT · PASS · INFO

Compatibilidad del producto propietario evaluada una vez en el registro de plataformas\.

Categoría: operator · Relación: documented · Método: static

Evidencia: \{"product": "Istio", "installed\_versions": \["1\.30\.7"\], "resolved\_versions": \["1\.30\.7"\], "resolution\_sources": \["istioctl control plane"\], "reviewed\_on": \["2026\-11\-04"\], "target": "1\.35\.9", "product\_registry\_ref": "istio", "score\_weight": 0, "counted\_in": "operators", "support\_status": "PASS", "support\_findings": \["COMPATIBLE"\]\}

Recomendación: Consultar el detalle único de la matriz del producto; resolver por separado los defectos técnicos del CRD\.

Fuente: [Referencia técnica](<https://istio.io/latest/docs/releases/supported-releases/>)

- Límite: El soporte del producto no prueba que la definición, conversión o datos persistidos del CRD sean correctos\.
### K135\-CONDITION\-GENERATION · PASS · INFO

1\.35 incorpora observedGeneration en condiciones de CRDs\.

Categoría: structure · Relación: release\_change · Método: static

Evidencia: \{"basis": "Cambio aditivo documentado en las notas 1\.35, PR 134984\.", "applicability": \{"crosses": "1\.35\.0"\}, "condition\_matched": true\}

Recomendación: Revisar deserializadores estrictos en clientes propios que consuman condiciones de CRDs\.

Fuente: [Referencia técnica](<https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.35.md>)

- Límite: No se inspecciona el código del operador; este cambio no es un bloqueo por sí mismo\.
### INSTANCES\-NOT\-REQUESTED · UNKNOWN · INFO

Instancias no inspeccionadas; usar \-\-include\-instances para lectura limitada\.

Categoría: instances · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)


## appprojects\.argoproj\.io — UNKNOWN / INFO

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

### PRODUCT\_SUPPORT · UNKNOWN · INFO

Compatibilidad del producto propietario evaluada una vez en el registro de plataformas\.

Categoría: operator · Relación: documented · Método: static

Evidencia: \{"product": "Argo CD", "installed\_versions": \["3\.2\.0"\], "resolved\_versions": \["3\.2\.0"\], "resolution\_sources": \["deployments\.apps"\], "reviewed\_on": \["2026\-11\-04"\], "target": "1\.35\.9", "product\_registry\_ref": "argocd", "score\_weight": 0, "counted\_in": "operators", "support\_status": "UNKNOWN", "support\_findings": \["NO\_SUPPORT\_DATA"\]\}

Recomendación: Consultar el detalle único de la matriz del producto; resolver por separado los defectos técnicos del CRD\.

Fuente: [Referencia técnica](<https://argo-cd.readthedocs.io/en/release-3.2/operator-manual/tested-kubernetes-versions/>)

- Límite: El soporte del producto no prueba que la definición, conversión o datos persistidos del CRD sean correctos\.
### K135\-CONDITION\-GENERATION · PASS · INFO

1\.35 incorpora observedGeneration en condiciones de CRDs\.

Categoría: structure · Relación: release\_change · Método: static

Evidencia: \{"basis": "Cambio aditivo documentado en las notas 1\.35, PR 134984\.", "applicability": \{"crosses": "1\.35\.0"\}, "condition\_matched": true\}

Recomendación: Revisar deserializadores estrictos en clientes propios que consuman condiciones de CRDs\.

Fuente: [Referencia técnica](<https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.35.md>)

- Límite: No se inspecciona el código del operador; este cambio no es un bloqueo por sí mismo\.
### INSTANCES\-NOT\-REQUESTED · UNKNOWN · INFO

Instancias no inspeccionadas; usar \-\-include\-instances para lectura limitada\.

Categoría: instances · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)


## certificates\.cert\-manager\.io — FAIL / HIGH

### STRUCTURE\-BASIC · PASS · INFO

Identidad, scope, nombres y versiones con estructura válida\.

Categoría: structure · Relación: preexisting · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

### STORAGE\-CONSISTENT · PASS · INFO

Declaraciones served, storage y storedVersions coherentes\.

Categoría: storage · Relación: preexisting · Método: static

Evidencia: \{"served": \["v1"\], "storage": \["v1"\], "stored\_versions": \["v1"\]\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/>)

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

### PRODUCT\_SUPPORT · FAIL · HIGH

Compatibilidad del producto propietario evaluada una vez en el registro de plataformas\.

Categoría: operator · Relación: documented · Método: static

Evidencia: \{"product": "Cert Manager", "installed\_versions": \["1\.16\.0"\], "resolved\_versions": \["1\.16\.0"\], "resolution\_sources": \["deployments\.apps"\], "reviewed\_on": \["2026\-11\-04"\], "target": "1\.35\.9", "product\_registry\_ref": "cert\-manager", "score\_weight": 0, "counted\_in": "operators", "support\_status": "FAIL", "support\_findings": \["VERSION\_EOL", "NOT\_COMPATIBLE"\]\}

Recomendación: Consultar el detalle único de la matriz del producto; resolver por separado los defectos técnicos del CRD\.

Fuente: [Referencia técnica](<https://cert-manager.io/docs/releases/>)

- Límite: El soporte del producto no prueba que la definición, conversión o datos persistidos del CRD sean correctos\.
### K135\-CONDITION\-GENERATION · PASS · INFO

1\.35 incorpora observedGeneration en condiciones de CRDs\.

Categoría: structure · Relación: release\_change · Método: static

Evidencia: \{"basis": "Cambio aditivo documentado en las notas 1\.35, PR 134984\.", "applicability": \{"crosses": "1\.35\.0"\}, "condition\_matched": true\}

Recomendación: Revisar deserializadores estrictos en clientes propios que consuman condiciones de CRDs\.

Fuente: [Referencia técnica](<https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.35.md>)

- Límite: No se inspecciona el código del operador; este cambio no es un bloqueo por sí mismo\.
### INSTANCES\-NOT\-REQUESTED · UNKNOWN · INFO

Instancias no inspeccionadas; usar \-\-include\-instances para lectura limitada\.

Categoría: instances · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Revisar la evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

