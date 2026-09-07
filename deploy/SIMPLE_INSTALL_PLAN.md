# Simple Compose prerelease

Based on the tested five-service deployment and ALACarte's existing wrapper lifecycle:
- Add a small one-shot initialization image. Use Docker-managed state volumes so normal Compose startup can create containers before initialization finishes, without missing host-directory mounts.
- Provide a default full stack and an add-on Compose file for an existing Navidrome project. Both include prepared catalog/auth features and use one short .env.
- Retain the working NAS preview and original upstream example separately. Application playback/acquisition code stays unchanged.
- Extend the existing pinned-source builder for versioned GHCR images and source artifacts. Replace upstream-derived version inference with an explicit Octocarte VERSION and tag match.
- Verify full-stack and add-on installation, unchanged existing Navidrome, token persistence, real catalog features and native playback. Publish private registry images and create a private prerelease only after checks pass. Public visibility remains a separate decision.
