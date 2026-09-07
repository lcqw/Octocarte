# Distribution review — 2026-09-07

Status: **public distribution is not cleared**. This is a source/artifact review,
not a legal certification. Repository organization can proceed while the items
below are resolved. Do not describe bundled images as fully license-compliant
based solely on the top-level GPL and AGPL files.

## Source licenses and retained notices

| Component | Inspected evidence | Treatment |
|---|---|---|
| Octo-Fiesta | GPLv3 LICENSE at base `c4d0f5734d1868b8f3f4c031566b705480c32efd` | Retain LICENSE, source notices, modification notice and history |
| Octo streaming/shim | GPLv3 LICENSE at `f9cf6f4c5eef795909335dbe52fe8e43fd739666` | Retain source notices and identify imported revision in NOTICE.md |
| ALACarte and integration patches | AGPLv3 LICENSE and backend/package.json `AGPL-3.0-only` at `ef9b677c21b024a0acbf4f88d47c4ebff24802fa` | Keep separate service, full license, dated change notice and matching patched source |

GPLv3 sections 4–6 cover retained notices, dated modification notices and
Corresponding Source when conveying modified source or object code. AGPLv3 has
those requirements plus section 13's prominent source offer to users interacting
with the modified program over a network. A private GitHub link is insufficient
for a user who cannot access it. Git history is useful provenance, not a substitute
for a license, applicable notices, or a usable source offer.

The old upstream README contains no unique copyright notice. Its acknowledgments
are carried into NOTICE.md. Old Compose/env examples and installation guides are
retired from the current tree; the original versions remain in history. Source,
build instructions, tests, licenses and integration patches remain available.

## Open items

1. **Modified ALACarte source offer.** This branch adds a visible source link before
   and after login, backed by an unauthenticated fixed-file download of the exact
   patched source archive baked into future ALACarte images. The archive comes
   from tracked build inputs, not runtime configuration. The next image release
   must include it; already published alpha images are unchanged. Source completeness
   for bundled third-party binaries remains subject to items 2–3.
2. **Wrapper binary provenance and third-party permissions.** ALACarte's
   `wrapper/README.md` identifies a prebuilt executable and Android rootfs from
   WorldObservationLog/wrapper releases, without identifying the exact release in
   that file. Its Dockerfile copies both into our image. The inspected rootfs
   includes `libstoreservicescore.so`, `libmediaplatform.so` and Apple-named ICU
   libraries as well as open-source libraries. The current wrapper repository
   advertises MIT, but that does not establish the license or matching source of
   this older binary, nor grant rights to unrelated bundled libraries. Resolve
   exact provenance, retain applicable notices and establish redistribution rights;
   otherwise exclude/replace affected artifacts or obtain permission.
3. **Downloader and image dependency coverage.** ALACarte's backend image derives
   from `ghcr.io/zhaarey/apple-music-downloader`; it contains `apple-music-dl`,
   MP4Box/libgpac, and other runtime components. The shim also distributes yt-dlp,
   Deno and FFmpeg. Match shipped versions to their licenses, notices and any
   required Corresponding Source. A base-image digest records identity, not rights.
4. **Notices inside distributed images.** This branch adds license/notice copies
   to future app/shim images and the prepared ALACarte image. The already shipped
   alpha images are unchanged. Third-party executable/library notices still need
   the complete inventory in items 2–3; these additions do not resolve that work.
5. **Full history and artifact review.** Before changing repository or package
   visibility, review all reachable history and actual release assets for secrets,
   installation-specific data, license terms and source completeness. Removing a
   file from the latest checkout does not remove it from Git history.

Keep the published alpha tags immutable. Corrections to images need a new version.
This cleanup does not publish new images or change repository/package visibility.

## Primary sources

- [Octo-Fiesta LICENSE](https://github.com/V1ck3s/octo-fiesta/blob/dev/LICENSE)
- [Octo LICENSE](https://github.com/winters27/octo/blob/main/LICENSE)
- [Pinned ALACarte source](https://github.com/sosjalapeno/alacarte/tree/ef9b677c21b024a0acbf4f88d47c4ebff24802fa)
- [Local retained AGPLv3 text](../../integrations/alacarte/LICENSE) — sections 4, 5, 6, 13
- [Wrapper repository](https://github.com/WorldObservationLog/wrapper)
- [Downloader repository](https://github.com/zhaarey/apple-music-downloader)
