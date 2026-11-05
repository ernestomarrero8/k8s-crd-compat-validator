# Kubernetes CRD Compatibility Validator

Clúster: offline:valid\-crds\.json · 1\.34\.8 → 1\.35\.9

Fecha UTC: 2026\-11\-05T14:51:23\.134688\+00:00 · Estado general: **FAIL**

CRDs: 1 · Consultas kubectl: 0

| Estado | CRDs |
|---|---:|
| PASS | 0 |
| UNKNOWN | 1 |
| WARN | 0 |
| FAIL | 0 |
| ERROR | 0 |

| Severidad de riesgos | Hallazgos |
|---|---:|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 0 |
| INFO | 0 |

## Upgrade Readiness Score

75.8/100 · BLOCKED

One unit per product/technical CRD/storage CRD and one Pluto unit\. Weighted compatibility over evaluated PASS=100%, WARN=50%, FAIL=0% units only; UNKNOWN/ERROR excluded from compatibility, retained in coverage\. Evidence coverage = evaluated/applicable units\. PRODUCT\_SUPPORT references have zero additional weight\.

El score es una ayuda de revisión; READY exige ausencia de bloqueos, avisos y evidencia pendiente en todo el informe\.

Cobertura de evidencia: 50.0% · Compatibilidad de unidades evaluadas: 75.8/100


## Cluster Platform Compatibility — OPERATOR COMPATIBILITY ANALYSIS

| Producto | Versiones | Origen | Compatibilidad | Resultado |
|---|---|---|---|---|
| Istio | 1\.24\.1 | istioctl control plane, pods | No | FAIL |
| Gatekeeper | v3\.18\.0 | deployments\.apps | No verificada | UNKNOWN |
| Calico | v3\.31\.2 | pods | Sí, según evidencia documentada | PASS |
| Azure Disk CSI Driver | v1\.34\.7\-7 | pods | No verificada | UNKNOWN |
| Azure File CSI Driver | v1\.35\.11\-6 | pods | No verificada | UNKNOWN |

AKS: \{"detected": false, "target\_version": "1\.35\.9", "current\_version": null, "node\_image\_versions": \[\], "node\_kubelet\_versions": \[\], "addons": \[\], "limitations": \["Metadata AKS observada; la versión efectiva y soporte de cada add\-on se evalúan por separado\.", "Una versión Kubernetes soportada upstream no acredita disponibilidad de upgrade, región, canal LTS ni soporte del add\-on administrado en AKS\.", "Node images se inventarían; no se infiere compatibilidad futura por su nombre\."\]\}


| CRD | Producto | Soporte producto | Riesgo upgrade |
|---|---|---|---|
| widgets\.example\.com | — | — | INFO |

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
### VERSION\_EOL · WARN · MEDIUM

Versión fuera de mantenimiento según la evidencia oficial registrada\.

Categoría: operator\_compatibility · Relación: documented · Método: static

Evidencia: \{"product": "Istio", "installed\_version": "1\.24\.1", "target": "1\.35\.9", "matrix": \{"version": "1\.24\.x", "min\_kubernetes": "1\.28\.0", "max\_kubernetes": "1\.31\.x", "matrix\_type": "supported", "exclusive": true, "end\_of\_support": "2025\-06\-24", "source": "https://istio\.io/latest/docs/releases/supported\-releases/", "reviewed\_on": "2026\-11\-04", "valid\_until": "2027\-02\-02", "evidence": "Fila oficial 1\.24: soporte Kubernetes 1\.28–1\.31; EOL 24 junio 2025\.", "support\_state": "supported"\}, "detected\_version": "1\.24\.1", "version\_confidence": "server\_cli", "catalog\_lookup": \{"catalog\_present": true, "files": \["istio\.json"\], "paths": \["catalogs/support/istio\.json"\], "available\_selectors": \["1\.30\.x", "1\.29\.x", "1\.28\.x", "1\.27\.x", "1\.26\.x", "1\.25\.x", "1\.24\.x", "1\.23\.x", "1\.22\.x", "1\.21\.x"\], "matched\_selectors": \["1\.24\.x"\], "selected\_selector": "1\.24\.x", "normalized\_version": "1\.24\.1", "reason": "matched"\}, "distribution\_revision": null, "reviewed\_on": "2026\-11\-04", "catalog\_limitations": \[\], "detection\_sources": \[\{"from": "pods", "namespace": "istio\-system", "name": "istiod\-example", "repository": "docker\.io/istio/pilot", "declared\_tag": "1\.24\.1", "revision": null, "identity\_basis": "catalog\_repository", "confidence": "image\_tag", "activity": "active", "observed\_status": \{\}, "version\_label": null, "version\_basis": "pod\_image\_tag"\}, \{"from": "istioctl control plane", "component": "pilot", "revision": null, "activity": "active"\}\], "resolution\_sources": \["istioctl control plane"\], "resolved\_versions": \["1\.24\.1"\], "raw\_detected\_versions": \["1\.24\.1"\]\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://istio.io/latest/docs/releases/supported-releases/>)

### NOT\_COMPATIBLE · FAIL · HIGH

Objetivo fuera del rango de soporte explícito del proveedor; no se recomienda este upgrade con la versión instalada\.

Categoría: operator\_compatibility · Relación: documented · Método: static

Evidencia: \{"product": "Istio", "installed\_version": "1\.24\.1", "target": "1\.35\.9", "matrix": \{"version": "1\.24\.x", "min\_kubernetes": "1\.28\.0", "max\_kubernetes": "1\.31\.x", "matrix\_type": "supported", "exclusive": true, "end\_of\_support": "2025\-06\-24", "source": "https://istio\.io/latest/docs/releases/supported\-releases/", "reviewed\_on": "2026\-11\-04", "valid\_until": "2027\-02\-02", "evidence": "Fila oficial 1\.24: soporte Kubernetes 1\.28–1\.31; EOL 24 junio 2025\.", "support\_state": "supported"\}, "detected\_version": "1\.24\.1", "version\_confidence": "server\_cli", "catalog\_lookup": \{"catalog\_present": true, "files": \["istio\.json"\], "paths": \["catalogs/support/istio\.json"\], "available\_selectors": \["1\.30\.x", "1\.29\.x", "1\.28\.x", "1\.27\.x", "1\.26\.x", "1\.25\.x", "1\.24\.x", "1\.23\.x", "1\.22\.x", "1\.21\.x"\], "matched\_selectors": \["1\.24\.x"\], "selected\_selector": "1\.24\.x", "normalized\_version": "1\.24\.1", "reason": "matched"\}, "distribution\_revision": null, "reviewed\_on": "2026\-11\-04", "catalog\_limitations": \[\], "detection\_sources": \[\{"from": "pods", "namespace": "istio\-system", "name": "istiod\-example", "repository": "docker\.io/istio/pilot", "declared\_tag": "1\.24\.1", "revision": null, "identity\_basis": "catalog\_repository", "confidence": "image\_tag", "activity": "active", "observed\_status": \{\}, "version\_label": null, "version\_basis": "pod\_image\_tag"\}, \{"from": "istioctl control plane", "component": "pilot", "revision": null, "activity": "active"\}\], "resolution\_sources": \["istioctl control plane"\], "resolved\_versions": \["1\.24\.1"\], "raw\_detected\_versions": \["1\.24\.1"\]\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://istio.io/latest/docs/releases/supported-releases/>)

### NO\_SUPPORT\_DATA · UNKNOWN · INFO

No existe una única fila de matriz oficial revisada para esta versión\.

Categoría: operator\_compatibility · Relación: limitation · Método: static

Evidencia: \{"product": "Gatekeeper", "installed\_version": "3\.18\.0", "target": "1\.35\.9", "matrix": \{\}, "detected\_version": "3\.18\.0", "version\_confidence": "image\_tag", "catalog\_lookup": \{"catalog\_present": true, "files": \["gatekeeper\.json"\], "paths": \["catalogs/support/gatekeeper\.json"\], "available\_selectors": \[\], "matched\_selectors": \[\], "selected\_selector": null, "normalized\_version": "3\.18\.0", "reason": "no\_numeric\_rows"\}, "distribution\_revision": null, "reviewed\_on": null, "catalog\_limitations": \["La política general de versiones soportadas no prueba una matriz de cada binario antiguo\. Sin fila revisada se informa UNKNOWN\."\], "detection\_sources": \[\{"from": "deployments\.apps", "namespace": "gatekeeper\-system", "name": "gatekeeper\-controller\-manager", "repository": "openpolicyagent/gatekeeper", "declared\_tag": "v3\.18\.0", "revision": null, "identity\_basis": "catalog\_repository", "confidence": "image\_tag", "activity": "active", "observed\_status": \{\}, "version\_label": null, "version\_basis": "workload\_template\_image\_tag"\}\], "resolution\_sources": \["deployments\.apps"\], "resolved\_versions": \["3\.18\.0"\], "raw\_detected\_versions": \["v3\.18\.0"\]\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://github.com/open-policy-agent/gatekeeper/blob/master/docs/Release_Management.md>)

### COMPATIBLE · PASS · INFO

Objetivo dentro del rango documentado; consultar si la evidencia acredita soporte o pruebas upstream\.

Categoría: operator\_compatibility · Relación: documented · Método: static

Evidencia: \{"product": "Calico", "installed\_version": "3\.31\.2", "target": "1\.35\.9", "matrix": \{"version": "3\.31\.x", "supported\_kubernetes": \{"min": "1\.32", "max": "1\.35"\}, "matrix\_type": "tested", "exclusive": false, "support\_state": "supported", "source": "https://raw\.githubusercontent\.com/tigera/docs/master/calico\_versioned\_docs/version\-3\.31/\_includes/partials/\_system\-requirements\.mdx", "reviewed\_on": "2026\-11\-04", "evidence": "Requisitos de Calico 3\.31: versiones activamente probadas 1\.32, 1\.33, 1\.34 y 1\.35\. Otras pueden funcionar; no es un máximo de soporte estricto\.", "min\_kubernetes": "1\.32", "max\_kubernetes": "1\.35", "valid\_until": "2027\-02\-02"\}, "detected\_version": "3\.31\.2", "version\_confidence": "image\_tag", "catalog\_lookup": \{"catalog\_present": true, "files": \["calico\.json"\], "paths": \["catalogs/support/calico\.json"\], "available\_selectors": \["3\.31\.x", "3\.32\.x"\], "matched\_selectors": \["3\.31\.x"\], "selected\_selector": "3\.31\.x", "normalized\_version": "3\.31\.2", "reason": "matched"\}, "distribution\_revision": null, "reviewed\_on": "2026\-11\-04", "catalog\_limitations": \["No se pudo verificar la documentación archivada 3\.30: permanece sin rango\. Tigera Operator tiene su propia versión, distinta de Calico\."\], "detection\_sources": \[\{"from": "pods", "namespace": "calico\-system", "name": "calico\-example", "repository": "docker\.io/calico/node", "declared\_tag": "v3\.31\.2", "revision": null, "identity\_basis": "catalog\_repository", "confidence": "image\_tag", "activity": "active", "observed\_status": \{\}, "version\_label": null, "version\_basis": "pod\_image\_tag"\}\], "resolution\_sources": \["pods"\], "resolved\_versions": \["3\.31\.2"\], "raw\_detected\_versions": \["v3\.31\.2"\]\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://raw.githubusercontent.com/tigera/docs/master/calico_versioned_docs/version-3.31/_includes/partials/_system-requirements.mdx>)

### NO\_SUPPORT\_DATA · UNKNOWN · INFO

No existe una única fila de matriz oficial revisada para esta versión\.

Categoría: operator\_compatibility · Relación: limitation · Método: static

Evidencia: \{"product": "Azure Disk CSI Driver", "installed\_version": "v1\.34\.7\-7", "target": "1\.35\.9", "matrix": \{\}, "detected\_version": "v1\.34\.7\-7", "version\_confidence": "image\_tag", "catalog\_lookup": \{"catalog\_present": true, "files": \["azure\-disk\.json"\], "paths": \["catalogs/support/azure\-disk\.json"\], "available\_selectors": \["1\.34\.5", "1\.33\.11", "1\.36\.0"\], "matched\_selectors": \[\], "selected\_selector": null, "normalized\_version": "1\.34\.7", "reason": "family\_not\_catalogued"\}, "distribution\_revision": "7", "reviewed\_on": null, "catalog\_limitations": \["No se extrapolan filas exactas a toda la familia 1\.34\.x\. Los tags con revisión de distribución se conservan; su soporte requiere vendor\_versions documentadas\."\], "detection\_sources": \[\{"from": "pods", "namespace": "kube\-system", "name": "azure\-disk\-example", "repository": "mcr\.microsoft\.com/oss/v2/kubernetes\-csi/azuredisk\-csi", "declared\_tag": "v1\.34\.7\-7", "revision": null, "identity\_basis": "catalog\_repository", "confidence": "image\_tag", "activity": "active", "observed\_status": \{\}, "version\_label": null, "version\_basis": "pod\_image\_tag"\}\], "resolution\_sources": \["pods"\], "resolved\_versions": \["v1\.34\.7\-7"\], "raw\_detected\_versions": \["v1\.34\.7\-7"\]\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://github.com/kubernetes-sigs/azuredisk-csi-driver>)

### NO\_SUPPORT\_DATA · UNKNOWN · INFO

No existe una única fila de matriz oficial revisada para esta versión\.

Categoría: operator\_compatibility · Relación: limitation · Método: static

Evidencia: \{"product": "Azure File CSI Driver", "installed\_version": "v1\.35\.11\-6", "target": "1\.35\.9", "matrix": \{\}, "detected\_version": "v1\.35\.11\-6", "version\_confidence": "image\_tag", "catalog\_lookup": \{"catalog\_present": true, "files": \["azure\-file\.json"\], "paths": \["catalogs/support/azure\-file\.json"\], "available\_selectors": \["1\.35\.7", "1\.34\.8", "1\.33\.10"\], "matched\_selectors": \[\], "selected\_selector": null, "normalized\_version": "1\.35\.11", "reason": "family\_not\_catalogued"\}, "distribution\_revision": "6", "reviewed\_on": null, "catalog\_limitations": \["No se encontró una matriz para v1\.35\.11\-6\. No se sustituye su versión detectada por UNKNOWN ni se extiende el soporte de 1\.35\.7 por similitud de minor\."\], "detection\_sources": \[\{"from": "pods", "namespace": "kube\-system", "name": "azure\-file\-example", "repository": "mcr\.microsoft\.com/oss/v2/kubernetes\-csi/azurefile\-csi", "declared\_tag": "v1\.35\.11\-6", "revision": null, "identity\_basis": "catalog\_repository", "confidence": "image\_tag", "activity": "active", "observed\_status": \{\}, "version\_label": null, "version\_basis": "pod\_image\_tag"\}\], "resolution\_sources": \["pods"\], "resolved\_versions": \["v1\.35\.11\-6"\], "raw\_detected\_versions": \["v1\.35\.11\-6"\]\}

Recomendación: Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade\.

Fuente: [Referencia técnica](<https://github.com/kubernetes-sigs/azurefile-csi-driver>)

### PLATFORM\-DISCOVERY · PASS · INFO

Cobertura del descubrimiento de plataformas\.

Categoría: operator\_compatibility · Relación: tested · Método: snapshot

Evidencia: \{"errors": \[\], "required\_errors": \[\], "detector\_errors": \[\], "inventory\_sources": \[\{"source": "deployments\.apps", "completed": true, "authorized": true, "error": null, "items\_scanned": 1, "required": true\}, \{"source": "daemonsets\.apps", "completed": true, "authorized": true, "error": null, "items\_scanned": 0, "required": true\}, \{"source": "statefulsets\.apps", "completed": true, "authorized": true, "error": null, "items\_scanned": 0, "required": true\}, \{"source": "pods", "completed": true, "authorized": true, "error": null, "items\_scanned": 4, "required": true\}, \{"source": "nodes", "completed": true, "authorized": true, "error": null, "items\_scanned": 0, "required": true\}, \{"source": "Helm", "completed": true, "authorized": true, "error": null, "items\_scanned": 0, "required": false\}\], "products\_detected": 5\}

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

### NO\_PRODUCT\_OWNER · UNKNOWN · INFO

No existe una asociación explícita entre este CRD y un producto detectado\.

Categoría: operator · Relación: limitation · Método: static

Evidencia: \{\}

Recomendación: Registrar ownership documentado y detectar la versión del producto; no inferirla por labels o por la existencia del CRD\.

Fuente: [Referencia técnica](<https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>)

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

