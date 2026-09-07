# Add Octocarte to an existing Navidrome project

`compose.existing-navidrome.yml` supplies Octocarte, ALACarte and its wrapper, the
YouTube shim, and automatic credential initialization. It does not define a
Navidrome service or mount its database. This installation uses the same prepared
images and included catalog features as the full-stack example.

1. Copy `compose.existing-navidrome.yml` beside your existing Compose file.
2. Add these values to your existing `.env` (retain its other settings):

   ```dotenv
   MUSIC_DIR=/absolute/path/to/your/music
   HOST_BIND=your-private-LAN-address
   NAVIDROME_URL=http://navidrome:4533
   OCTOCARTE_VERSION=0.0.5-alpha.1
   ```

   `MUSIC_DIR` must be the host folder your Navidrome already reads. Adjust
   `NAVIDROME_URL` if its Docker service has a different name. A server on another
   host needs shared music storage; a scan does not transfer files.

3. From that project directory, start the combined configuration:

   ```sh
   docker compose -f docker-compose.yml -f compose.existing-navidrome.yml up -d
   ```

   Replace `docker-compose.yml` with your existing filename if different. Keep
   using both files when managing this combined project.

4. Open ALACarte at port `7373`, complete Apple sign-in and preferences, and
   enable its Navidrome integration using the same internal URL plus scan
   credentials. Connect your music client to Octocarte on port `5274`, using
   its existing Navidrome account.

For a UI that accepts one Compose file, merge the add-on's service entries under
`services` and its volume declarations under `volumes`, retaining your existing
entries and project name. Include its `x-logging` definition as well. The `.env`
values can be entered through the project's environment settings.

If Octo-Fiesta currently uses port `5274`, stop/remove that service or choose a
different `OCTOCARTE_PORT` before starting. Only one ALACarte wrapper may use the
name `alacarte-wrapper` on this Docker host.

A separate Compose project is also possible: set `NAVIDROME_URL` to an address
reachable from the Octocarte container and keep the shared music path consistent.
A container's `127.0.0.1` refers to itself, not the Docker host.
