# Optional ALACarte artist top-songs extension

**Prepared, not installed.** This is a patch for the separate ALACarte service,
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

Validation: patch applies cleanly; new normalization tests and route syntax check
pass. A live read-only request through this patched ALACarte client returned ten
ranked Kanye West tracks, including Can't Tell Me Nothing (1451903287, parent
1451901307), All Falls Down (1412873019, parent 1412872568), and Homecoming
(1451904360, parent 1451901307). No download was submitted by this check.
The full ALACarte regression suite and deployed HTTP route have not yet been
validated. Installing requires rebuilding ALACarte and can conflict with future
upstream changes. It is optional; the current deployment is unchanged.

To review/apply in an isolated ALACarte checkout:

```sh
git apply --check /path/to/top-songs.patch
git apply /path/to/top-songs.patch
cd backend
npm ci
npm test
```

Octocarte's `getTopSongs` adapter is the next step after choosing this service
extension. It should preserve Apple ranking and substitute matching local
Navidrome tracks, support artist-name requests and the OpenSubsonic artist-ID
extension, and fall back gracefully when stock ALACarte lacks this route.
It must not present ordinary search results as popularity-ranked songs.

Sources: [ALACarte](https://github.com/sosjalapeno/alacarte),
[Apple artist views](https://developer.apple.com/documentation/applemusicapi/artists/views-data.dictionary),
[OpenSubsonic getTopSongs](https://opensubsonic.netlify.app/docs/endpoints/gettopsongs/).

Other possible discovery additions are similar artists (fits artist-info
responses), latest releases and album categories (artist browsing), then charts
and editorial playlists (client support varies). These are proposals, not
implemented features. Each needs a verified ALACarte HTTP contract first.
