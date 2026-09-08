# Building a release

The release workflow is manually dispatched on a tag matching `VERSION`. It
builds pinned sources, tests independently managed Navidrome integration, publishes versioned images,
pulls them back for another startup check, and creates a draft release with
source archives, the Compose configuration and the image manifest. An existing published
version must not be overwritten. A failed partial publication needs inspection
before choosing a new version or recovery procedure.

The release attachment is named `env.example` because GitHub normalizes filenames
that begin with a dot. Copy it to `.env` when installing from release attachments.
The repository retains the usual `.env.example` filename.

## Versioning

Every published runtime update gets a new version, matching the `VERSION` file,
`vVERSION` Git tag, release notes and all five image tags. Never replace an image
under an existing release tag. Bug fixes increment the patch version (for example,
`0.0.6` to `0.0.7`); feature releases increment the minor version. Releases before
`1.0.0` may still introduce breaking changes, which must be explained in their notes.
Documentation-only changes can be merged between releases without rebuilding images.

A numeric version such as `0.0.6` creates a regular release. A suffixed version
such as `0.1.0-beta.1` creates a prerelease. The workflow leaves either as a draft
until the release assets and installation checks are reviewed. Publish the draft
only after those checks pass. Repository and container visibility are managed
separately from release status.

## Checking an existing release

Run the **CI** workflow manually to pull all five images from the current
repository owner's registry namespace. This read-only check compares their
image IDs and registry digests with the published release manifest. It does not
build, publish or change package visibility. It is useful after an account rename
or changes to package access. Normal pushes and pull requests run the application
checks instead.
