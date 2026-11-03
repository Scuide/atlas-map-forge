Atlas Map Forge: experimental Linux browser edition (x86_64)

Requires a desktop Linux system with glibc 2.35 or newer (Ubuntu 22.04 or
newer, or a compatible distribution) and a modern web browser. Python,
GTK and Qt do not need to be installed. Alpine/musl and ARM are not supported
by this download. Other distributions still need user testing.

1. Extract the .tar.gz archive into a folder you can write to.
2. Open a terminal in that folder and run:

   ./AtlasMapForge

   If the executable permission was lost, run chmod +x AtlasMapForge first.
   Do not run with sudo.
3. Your browser opens the local interface. If it does not, copy the full
   http://127.0.0.1:.../?t=... address printed in the terminal into a browser.
4. Enter an author name in Settings, choose a template and build a map.
5. Keep the terminal open while using the app. Press Ctrl+C in that terminal
   to stop the app; closing the browser tab alone does not stop it.

The first start may take a few seconds while the program unpacks.
The interface and map generation run on your computer, not on a website.
An Internet connection is not required to generate maps.

Maps:       ~/AtlasMapForge
Projects:   ~/AtlasMapForge/projects
Settings:   ${XDG_CONFIG_HOME:-~/.config}/atlas-map-forge/config.json
Cache:      ${XDG_CACHE_HOME:-~/.cache}/atlas-map-forge

The app detects common Steam Zero-K folders, ~/.spring and ~/Zero-K.
If detection fails (including some Flatpak installations), set the Zero-K
data folder in Settings. This is the folder that contains maps/, not maps/
itself. Alternatively, disable installation and copy the generated .sdz
from ~/AtlasMapForge into your Zero-K maps/ folder yourself.
Disable "Only show featured maps" in the Zero-K lobby to see local maps.

Browser mode has no native folder picker: type or paste filesystem paths
into the corresponding settings fields.

If startup fails with GLIBC_x.y not found, your distribution is too old for
this binary. Use the Python installation described in the project README.
On a system with a noexec /tmp, use an executable temporary folder, e.g.:

   mkdir -p "$HOME/.cache/atlasforge-tmp"
   TMPDIR="$HOME/.cache/atlasforge-tmp" ./AtlasMapForge

Project and bug reports: https://github.com/Scuide/atlas-map-forge
License: GPL-2.0-or-later. See LICENSE and THIRD-PARTY-LICENSES.txt.
SOURCE.txt records the exact source commit used for this build.
