# Licenses and source distribution

Octocarte is derived from Octo-Fiesta and includes streaming code adapted from
Octo. Both projects use GPLv3. ALACarte runs as a separate AGPLv3 service;
Octocarte's ALACarte integration patches retain that license.

| Component | License | Attribution |
|---|---|---|
| Octocarte and Octo-Fiesta code | [GPLv3](../../LICENSE) | [Project notices](../../NOTICE.md) |
| Octo streaming and yt-dlp shim | [GPLv3](../../yt-dlp-shim/LICENSE) | [Shim notices](../../yt-dlp-shim/NOTICE.md) |
| ALACarte integration | [AGPLv3](../../integrations/alacarte/LICENSE) | [Integration documentation](../../integrations/alacarte/README.md) |

Retain copyright notices, license text and notices identifying modifications
when distributing covered code. Binary distributions must meet the applicable
source-distribution requirements. Modified ALACarte deployments must also provide
network users the source offer required by AGPLv3 section 13.

The release builder produces matching Octocarte and patched ALACarte source
archives, together with an image manifest and checksums. It includes the ALACarte
archive in the prepared image and adds a source-download link to its web UI.
Preserve that link when changing the integration.

Bundled dependencies keep their own licenses. When adding or updating them,
check the applicable notice and source-distribution requirements alongside the
component's build inputs. The project license does not replace dependency licenses.

For upstream revisions and modification details, see [NOTICE.md](../../NOTICE.md).
For release packaging, see [Building a release](RELEASING.md).
