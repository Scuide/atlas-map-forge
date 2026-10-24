# Linux browser edition (experimental)

The Linux download bundles Python and the map generator into an executable. The graphical interface
opens in your existing web browser. All map generation runs locally. This download targets x86_64
desktop Linux with glibc 2.35 or newer; it is not an ARM or Alpine/musl build.

## Download and start

1. On the [releases page](https://github.com/Scuide/atlas-map-forge/releases), download
   `AtlasMapForge-linux-x86_64.tar.gz` and its `.sha256` file when available.
   Experimental builds are also available as the **AtlasMapForge-linux-x86_64** artifact in a
   successful [linux-app workflow run](https://github.com/Scuide/atlas-map-forge/actions/workflows/linux-app.yml).
   GitHub requires sign-in to download workflow artifacts. Unzip that artifact first to get the tarball
   and checksum. Only use builds whose **test** jobs succeeded, not just the **build** job.
2. In the download folder:

   ```sh
   sha256sum -c AtlasMapForge-linux-x86_64.tar.gz.sha256
   tar -xzf AtlasMapForge-linux-x86_64.tar.gz
   cd AtlasMapForge-linux-x86_64
   ./AtlasMapForge
   ```

3. If no browser tab opens, paste the full local address printed in the terminal into your browser.
4. Enter your author name in Settings, choose a template and build a map.
5. Keep the terminal open while using the app. Press **Ctrl+C** there to stop it. Closing the browser
   tab alone does not stop the program. The first launch can take a few seconds while it unpacks.

No `sudo`, Python installation or native webview packages are needed. If the executable permission
was lost during extraction, run `chmod +x AtlasMapForge`.

## Files and Zero-K

- Maps: `~/AtlasMapForge`; saved projects: `~/AtlasMapForge/projects`.
- Settings: `~/.config/atlas-map-forge/config.json` (or under `XDG_CONFIG_HOME`).
- Cache: `~/.cache/atlas-map-forge` (or under `XDG_CACHE_HOME`).
- Common Steam installations, `~/.spring` and `~/Zero-K` are detected. If your setup is not detected,
  enter the Zero-K **data folder** in Settings (the parent of `maps/`), or disable installation and
  copy the `.sdz` into your game's `maps/` folder. Flatpak setups may need manual configuration.
- Turn off **Only show featured maps** in the Zero-K lobby to see local maps.
- Browser mode has no native folder picker. Type or paste folder paths into Settings.

If `GLIBC_x.y not found` appears, the distribution is too old for this binary. Use the Python
installation below. If `/tmp` is mounted with `noexec`, select an executable temporary directory:

```sh
mkdir -p "$HOME/.cache/atlasforge-tmp"
TMPDIR="$HOME/.cache/atlasforge-tmp" ./AtlasMapForge
```

## Run from Python instead

Requires Python 3.9+, Git and venv support:

```sh
python3 -m venv ~/atlasforge-venv
. ~/atlasforge-venv/bin/activate
python -m pip install git+https://github.com/Scuide/atlas-map-forge
atlasforge app --browser
```

## Building and publishing

The `linux-app` workflow builds on Ubuntu 22.04 with Python 3.12, packages the executable with
PyInstaller, and archives it with executable permissions, licenses, the source commit and a SHA-256
checksum. Tests on Ubuntu 22.04 and 24.04 extract the actual archive, run a packed preview and full
map build, and verify browser launch and the rendered interface in headless Chromium.

Branch pushes, pull requests, version tags and manual runs produce workflow artifacts. They do not
publish a release automatically. Once the code is reviewed and the workflow is on the default branch,
run **Actions > linux-app > Run workflow** and enter an **existing** release tag to attach the tested
Linux archive and checksum. Leave the tag empty for an artifact-only run. Publishing checks that
`atlasforge/` and `pyproject.toml` match the release tag; packaging and documentation can differ.
Existing assets are not overwritten. Windows packaging is unchanged.

These checks cover the listed Ubuntu versions, not every desktop distribution. Please report your
distribution/version and terminal error in [GitHub Issues](https://github.com/Scuide/atlas-map-forge/issues)
if startup or map generation fails.
