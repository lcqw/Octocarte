# ALACarte integration

The standard [Octocarte Compose package](../../README.md) includes a prepared
ALACarte image. Artist photos and Apple-ranked top songs work after normal setup;
users do not apply patches or copy session cookies. This directory records the
source changes used to build that image, for maintenance and attribution.

ALACarte remains a separate service. Its Apple authentication, acquisition,
metadata, lyrics, artwork, library index and scan implementation stay in ALACarte.
Octocarte communicates through HTTP and leaves preferences under ALACarte's control.

## Included changes

- **Artist photos:** use ALACarte's existing artist-detail API; no ALACarte patch.
- **Ranked top songs:** `top-songs.patch` adds authenticated
  `GET /api/artist/:id/top-songs?limit=50`, reusing ALACarte's Apple client and saved
  storefront, language and rating preferences. Results retain Apple's order and
  parent-album identifiers. Octocarte replaces matches with native Navidrome tracks.
- **Unattended access:** `service-auth.patch` adds a scoped, deployment-owned token
  for catalog reads and album or song submission. The package provisions it automatically.
  See [authentication details](SERVICE_AUTH.md) for scope, rotation and revocation.
- **Wrapper image selection:** `wrapper-image.patch` lets ALACarte's existing
  sign-in flow use the exact wrapper image included in the package. It changes
  only image selection; the default remains compatible with upstream ALACarte.

The build helper applies these changes to sosjalapeno/alacarte revision
`ef9b677c21b024a0acbf4f88d47c4ebff24802fa`. ALACarte and these patches are
AGPL-3.0-only; the license is preserved here, and modified ALACarte source ships
with release artifacts. Build dependencies are resolved to image digests and
recorded in its manifest. Future upstream updates need patch and contract tests.

- **Source offer:** `source-offer.patch` adds a visible download link on the login
  screen and application. Future images serve their matching patched source
  archive at `/octocarte-source.tar.gz` without requiring an account. This fixed
  build artifact contains no runtime settings, music or credentials.

## Development and compatibility

CI applies the patches to the pinned source and tests the catalog/authentication
contracts. The top-songs adapter supports artist names and IDs, JSON/XML,
`topSongsByArtistId`, and a bounded five-minute cache. Local matches are queried
afresh. Ordinary search results are never presented as popularity rankings.

For development, apply the patches in the order listed above and run the ALACarte
backend tests. The package build performs patching automatically.

Sources: [ALACarte](https://github.com/sosjalapeno/alacarte),
[Apple artist views](https://developer.apple.com/documentation/applemusicapi/artists/views-data.dictionary),
[OpenSubsonic getTopSongs](https://opensubsonic.netlify.app/docs/endpoints/gettopsongs/).

## Modification notice

Octocarte integration changes, 2026-09-07: ranked top-song catalog reads, scoped
service authentication wrapper-image selection and source availability. The patches modify the pinned
ALACarte version identified above and remain AGPL-3.0-only. Later changes are
dated in Git history. No warranty is provided; see [LICENSE](LICENSE).

Public distribution and the modified service's source offer still require the
work recorded in the [distribution review](../../docs/development/LICENSING.md).


Single-song access added 2026-09-08: the scoped token also permits ALACarte's
existing song-download endpoint, accepting only a numeric song ID. ALACarte's
downloader and library implementation remain unchanged.
