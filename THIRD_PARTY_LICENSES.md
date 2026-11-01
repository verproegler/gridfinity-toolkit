# Third-party licenses

Gridfinity Toolkit itself is MIT licensed (see `LICENSE`). This file lists the third-party work
it is based on or ships with.

## gridfinity-rebuilt-openscad

Source: https://github.com/kennetek/gridfinity-rebuilt-openscad (commit 910e22d, 2025-08-31)

Used for: baseplate profile and styles (thin, skeletonized, weighted), bin base profile, lite
(hollow) base, stacking lip with fillet and support, magnet holes, all related dimensions. The
geometry was re-implemented in Python (`gridfinity_toolkit/bins.py`, `gridfinity_toolkit/baseplate.py`);
no files of that repository are included. The license below also contains the notice of the
original Gridfinity by Zack Freedman and Voidstar Lab LLC.

```
MIT License

Copyright (c) 2023 Kenneth Hodson

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


This repository is based on Gridfinity:

MIT License

Copyright (c) 2023 Zachary Freedman and Voidstar Lab LLC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Bambu Studio printer settings

Files: `assets/bambu_template_*.config`

Printer and process settings exported from Bambu Studio (https://github.com/bambulab/BambuStudio,
version 02.07.00.55). Bambu Studio and its bundled profiles are licensed under the
GNU Affero General Public License v3.0 (https://www.gnu.org/licenses/agpl-3.0.html). These files
are not covered by the MIT license of Gridfinity Toolkit; they are only used as a template when
writing Bambu multi-plate project files.

## Python packages

Installed separately via `requirements.txt` and not included in this repository. If you
distribute a bundled build (e.g. an .exe), include their license texts.

| Package | License |
| --- | --- |
| numpy | BSD-3-Clause (with bundled parts under 0BSD, MIT, Zlib, CC0-1.0) |
| manifold3d | Apache-2.0 |
| Pillow | MIT-CMU (HPND) |
| PyOpenGL | BSD-style |
| pyopengltk | MIT |
