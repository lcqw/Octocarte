# Attribution
Octocarte derives from [Octo-Fiesta](https://github.com/V1ck3s/octo-fiesta).
Its Git history, original README, copyright notices and GPL-3.0 license are retained.

YouTube streaming components and yt-dlp-shim are adapted from
[Octo](https://github.com/winters27/octo), revision
f9cf6f4c5eef795909335dbe52fe8e43fd739666, under its GPL-3.0 license.
Ported files carry their original comments; Octocarte modifications are recorded
in Git history. See LICENSE for the complete license text.

[ALACarte](https://github.com/sosjalapeno/alacarte) is an independent HTTP service.
No Apple authentication, decryption, downloading, tagging, lyrics or library
management implementation is incorporated from it.

The prepared ALACarte image includes maintained catalog, service-authentication
and wrapper-image selection patches under ALACarte's AGPL-3.0-only license in
`integrations/alacarte`, with its full license and attribution. It extends the separate service and is not compiled into
Octocarte. Apple authentication and acquisition remain owned by ALACarte.
