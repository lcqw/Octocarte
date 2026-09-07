# Attribution and modification notice

Octocarte is a modified work derived from [Octo-Fiesta](https://github.com/V1ck3s/octo-fiesta),
with YouTube streaming adapted from [Octo](https://github.com/winters27/octo).
Their GPLv3 license and existing source copyright notices are retained.
See [LICENSE](LICENSE). The software is provided without warranty as stated there.

Octocarte changes began on 2026-09-07 and include the ALACarte catalog adapter,
asynchronous album submission, temporary YouTube streaming integration, client
metadata mapping, service authentication and deployment configuration. Dated
commits identify subsequent changes. Upstream history remains in Git.

Imported Octo revision: `f9cf6f4c5eef795909335dbe52fe8e43fd739666`.
Original Octo-Fiesta base: `c4d0f5734d1868b8f3f4c031566b705480c32efd`.

[ALACarte](https://github.com/sosjalapeno/alacarte) remains a separate HTTP service.
Its catalog, Apple authentication, acquisition, tagging, artwork, lyrics and library
management are implemented there. The maintained integration patches are
AGPL-3.0-only, with the full license and change notice in
[integrations/alacarte](integrations/alacarte/README.md).

The original Octo-Fiesta README acknowledged Navidrome, Deezer, Qobuz, SquidWTF,
Yandex Music and the Subsonic API. Those acknowledgments are retained here;
they are not claims of endorsement or of Octocarte support for every provider.

Dependencies retain their own licenses. This notice does not relicense third-party
binaries. See the [distribution review](docs/development/LICENSING.md) for evidence
and unresolved requirements before public image publication.
