# Optional ALACarte artist top-songs extension

**Installed locally with user approval (2026-09-07).** This is a patch for the separate ALACarte service,
not Apple API code compiled into Octocarte. It applies to sosjalapeno/alacarte
`ef9b677c21b024a0acbf4f88d47c4ebff24802fa`. ALACarte and this patch are
AGPL-3.0-only; its license is preserved alongside the patch.

The patch adds authenticated, read-only `GET /api/artist/:id/top-songs?limit=50`
(maximum 50). It calls Apple's actual artist `top-songs` view through ALACarte's
existing Apple client. It uses ALACarte's saved storefront, language and rating
preference, retains ranked order, and returns song/artist/parent-album IDs,
duration and artwork in the same vocabulary as ALACarte search. Missing parent
IDs stay unresolved for the existing song-link lookup. No downloader, Apple
authentication, settings, lyrics, scan or library-index code changes.

Validation: patch applies cleanly; normalization and HTTP route tests pass, and the full ALACarte
backend suite passes (142 tests). A live read-only request through this patched ALACarte client returned ten
ranked Kanye West tracks, including Can't Tell Me Nothing (1451903287, parent
1451901307), All Falls Down (1412873019, parent 1412872568), and Homecoming
(1451904360, parent 1451901307). No download was submitted by this check.
The deployed endpoint returned ten ranked songs, and anonymous access returned
HTTP 401. Existing public preferences were verified unchanged. Octocarte's
JSON/XML adapter and local replacement passed unit and running-container tests.
This extension is optional for other installations; stock ALACarte falls back
to Navidrome's existing top-songs behavior.

The local installation uses image `octocarte-alacarte:top-songs`, built as a
three-file overlay on the existing `alacarte-test-web` image after confirming
that both modified files exactly matched the inspected source. The original
image and source checkout are retained. No existing ALACarte source files or
credentials were modified. The local Compose override is currently at
`work/alacarte-extension.compose.yml` in the task workspace; an equivalent
portable override is [compose.image.yml](compose.image.yml). Include the override
after ALACarte's existing Compose file when recreating the web service, with
`--no-build` to select the already built patched image. Starting only the
original Compose file can revert the extension. Roll back by recreating only
the `web` service from the original Compose file with `--no-build`; do not remove
its data volumes. Perform any restart while the acquisition queue is idle.

Installing from source requires rebuilding ALACarte and can conflict with future
upstream changes. CI reapplies this patch to the pinned source and tests its
HTTP contract on each Octocarte milestone.

To review/apply in an isolated ALACarte checkout:

```sh
git apply --check /path/to/top-songs.patch
git apply /path/to/top-songs.patch
cd backend
npm ci
npm test
```

Octocarte's `getTopSongs` adapter preserves Apple ranking and substitutes
matching local Navidrome tracks. It supports artist-name and artist-ID requests,
advertises `topSongsByArtistId` alongside Navidrome's existing extensions, and
falls back gracefully when stock ALACarte lacks this route. Ranked metadata is
cached for five minutes in bounded memory; native matches are queried afresh.
It never presents ordinary search results as popularity-ranked songs.

Sources: [ALACarte](https://github.com/sosjalapeno/alacarte),
[Apple artist views](https://developer.apple.com/documentation/applemusicapi/artists/views-data.dictionary),
[OpenSubsonic getTopSongs](https://opensubsonic.netlify.app/docs/endpoints/gettopsongs/).

Other possible discovery additions are similar artists (fits artist-info
responses), latest releases and album categories (artist browsing), then charts
and editorial playlists (client support varies). These are proposals, not
implemented features. Each needs a verified ALACarte HTTP contract first.

For the candidate unattended integration credential, see [SERVICE_AUTH.md](SERVICE_AUTH.md). It is developed separately from the installed catalog extension.
