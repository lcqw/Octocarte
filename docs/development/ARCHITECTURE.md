# Architecture

A Subsonic client connects to Octocarte, which authenticates and proxies local
library operations through an independently managed Navidrome server. ALACarte
provides Apple's catalog over HTTP. Its prepared image includes the integration
patches; users do not install them separately.

External IDs identify Apple songs/albums/artists. Search merges local matches
with catalog results. Unowned playback resolves YouTube audio through the shim
and returns AAC/M4A with truthful metadata and byte-range handling. An independent
bounded queue submits the whole parent album to ALACarte. A short in-memory guard
reduces duplicate bursts; ALACarte owns persistent duplicate detection, partial
completion and its library index. HTTP 409 already-present is a normal no-op.

ALACarte owns Apple sign-in, preferences, acquisition, output format, metadata,
lyrics, artwork, filesystem layout and Navidrome scans. Octocarte does not pass
preference overrides. Once indexed, native Navidrome matches replace placeholders,
including playback requested through an older external ID.

Artist photos use ALACarte's existing artist endpoint. Top songs use its maintained
ranked-catalog endpoint. The service token grants only catalog reads and whole-album
submission; it cannot administer ALACarte. See the [integration contract](../../integrations/alacarte/README.md).

The inherited .NET project names remain to avoid unrelated code/build churn.
Inherited non-Apple provider code remains available in source but has not received
Octocarte end-to-end acceptance testing. It is not part of the supported default
installation. Soulseek/slskd and their acquisition system were not imported.
