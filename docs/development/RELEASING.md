# Building a release

The release workflow is manually dispatched on a tag matching `VERSION`. It
builds pinned sources, tests independently managed Navidrome integration, publishes versioned images,
pulls them back for another startup check, and creates a draft prerelease with
source archives, the Compose configuration and the image manifest. An existing published
version must not be overwritten. A failed partial publication needs inspection
before choosing a new version or recovery procedure.

The release attachment is named `env.example` because GitHub normalizes filenames
that begin with a dot. Copy it to `.env` when installing from release attachments.
The repository retains the usual `.env.example` filename.
