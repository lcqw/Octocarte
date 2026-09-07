# Complete Compose package plan

- Reuse the validated proxy/shim and merge the tested service-auth change through PR #1.
- Build pinned ALACarte source with the catalog/auth patches automatically; preserve its source/license in the package. Allow its existing wrapper login helper to select the package's versioned wrapper image through one environment setting; keep its login implementation intact.
- Ship one five-service Compose project with shared music storage, separate persisted data, automatically provisioned service token, and local images recorded by immutable image ID. Normal Apple/Navidrome setup remains in their UIs.
- Keep stock/external-service Compose as an advanced path. Root documentation describes included artist photos/top songs and unattended auth, with build/installation steps and honest NAS validation status.
- Build distinct candidate images, validate fresh isolated startup/catalog/auth/restarts/storage wiring, run existing HTTP streaming tests, and submit a focused packaging PR. Do not replace running services or change NAS state.
