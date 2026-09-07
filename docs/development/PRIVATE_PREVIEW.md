# Private prerelease access

The short installation flow assumes access to the repository and registry images.
During the private preview, repository collaborators must authenticate Git and
Docker with GitHub. A repository clone does not authenticate the Docker registry.

For Docker, use a GitHub personal access token (classic) with `read:packages` and
access to these packages. Run `docker login ghcr.io -u YOUR_GITHUB_USERNAME` and
enter the token at the password prompt. Never put the token in Compose, `.env`,
a command-line argument, screenshots or logs. Follow your host's normal credential
storage practices. Repository access must also be configured through GitHub's
normal Git authentication.

Once the images are explicitly made public, pulling them requires no GitHub
login. Publishing a prerelease inside a private repository does not make either
the repository or its images public. Container publication and visibility changes
are separate operations.

The release workflow is manually dispatched on a tag matching `VERSION`. It
builds pinned sources, tests independently managed Navidrome integration, publishes versioned images,
pulls them back for another startup check, and creates a draft prerelease with
source archives, the Compose configuration and the image manifest. An existing published
version must not be overwritten. A failed partial publication needs inspection
before choosing a new version or recovery procedure.

The release attachment is named `env.example` because GitHub normalizes filenames
that begin with a dot. Copy it to `.env` when installing from release attachments.
The repository retains the usual `.env.example` filename.
