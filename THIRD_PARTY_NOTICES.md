# Third-Party Notices

WriteOnSide includes or depends on third-party open-source software. The
copyright notices and license texts for these components are provided in the
[`licenses/`](licenses/) directory.

This document applies to WriteOnSide source version `0.0.42` and to Windows
executables produced from that source using `WriteOnSide.spec`.

## Runtime components

| Component | Version | Purpose | License text |
|---|---:|---|---|
| Python | 3.12 | Application runtime and standard library | [`python-PSF.txt`](licenses/python-PSF.txt) |
| Tcl/Tk | 8.6 | Tkinter GUI runtime | [`tcl-tk-license.txt`](licenses/tcl-tk-license.txt) |
| keyboard | 0.13.5 | Global keyboard shortcuts | [`keyboard-MIT.txt`](licenses/keyboard-MIT.txt) |
| Pillow | 12.2.0 | Image loading, rendering, and icon generation | [`pillow-MIT-CMU.txt`](licenses/pillow-MIT-CMU.txt) |
| pystray | 0.19.5 | Windows system tray integration | [`pystray-LGPL-3.0.txt`](licenses/pystray-LGPL-3.0.txt) |
| six | 1.17.0 | Compatibility dependency used by pystray | [`six-MIT.txt`](licenses/six-MIT.txt) |
| tkinterdnd2 | 0.5.0 | Tkinter drag-and-drop wrapper | [`tkinterdnd2-MIT.txt`](licenses/tkinterdnd2-MIT.txt) |
| tkDnD | 2.9.x | Native drag-and-drop extension bundled by tkinterdnd2 | [`tkdnd-license.txt`](licenses/tkdnd-license.txt) |
| watchdog | 6.0.0 | File-system change monitoring for note vault refreshes | [`watchdog-Apache-2.0.txt`](licenses/watchdog-Apache-2.0.txt) |

pystray is licensed under GNU LGPL version 3. The LGPL incorporates terms from
GNU GPL version 3, whose full text is included at
[`GPL-3.0.txt`](licenses/GPL-3.0.txt).

WriteOnSide does not modify pystray. The corresponding upstream source is
available from the [pystray repository](https://github.com/moses-palmer/pystray)
and the exact version used by this project is declared in
[`requirements.txt`](requirements.txt).

## Build tool

WriteOnSide executables are produced with PyInstaller. PyInstaller is licensed
under GPL-2.0-or-later with a special exception that permits generated
executables to be distributed under the application author's chosen license,
subject to the licenses of bundled dependencies.

PyInstaller is a build-time tool and is not listed as a runtime component in
this directory. Its license and exception are available from the
[PyInstaller documentation](https://pyinstaller.org/en/stable/license.html).

The icon export helper uses PyMuPDF. The development environment used for
source version `0.0.42` contains PyMuPDF `1.27.2.3`, which declares dual
licensing under GNU AGPL version 3 or an Artifex commercial license. PyMuPDF is
used only while generating PNG and ICO assets from the SVG logo sources; it is
not imported by the WriteOnSide application at runtime. See the
[PyMuPDF licensing documentation](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright).

## No endorsement

The names of third-party projects and contributors are used only for
attribution. They do not imply endorsement of WriteOnSide.

## WriteOnSide license

WriteOnSide's original source code is licensed under the MIT License. See
[`LICENSE`](LICENSE) in the repository root.
