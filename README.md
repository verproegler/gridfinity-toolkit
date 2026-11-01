# Gridfinity Toolkit

*[Deutsche Anleitung](README.de.md)*

A desktop tool for [Gridfinity](https://gridfinity.xyz/) storage that takes you from an empty
drawer to ready-to-print plates:

1. **Baseplate** – cuts Gridfinity baseplates to the exact size of your drawer.
2. **Bin** – designs stackable bins (any size, solid or with hexagon cut-outs) with a live 3D preview.
3. **Combined Grid** – plans the whole drawer: place bins on the baseplate grid, stack them,
   look at it in 3D and export print plates for your printer plus an assembly sheet.

The geometry is based on [Gridfinity](https://gridfinity.xyz/) by Zack Freedman and on
[gridfinity-rebuilt-openscad](https://github.com/kennetek/gridfinity-rebuilt-openscad) by
kennetek (both MIT, see [License and credits](#license-and-credits)).

The interface is available in **German and English** (click the flags at the top right; the
choice is remembered). Every field and button has a short explanation – just rest the mouse on it.

---

## Contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [Tab 1: Baseplate](#tab-1-baseplate)
- [Tab 2: Bin](#tab-2-bin)
- [Tab 3: Combined Grid](#tab-3-combined-grid)
- [What gets exported](#what-gets-exported)
- [Terms](#terms)
- [Tips and troubleshooting](#tips-and-troubleshooting)
- [Command line](#command-line)
- [For developers](#for-developers)
- [License and credits](#license-and-credits)

---

## Installation

You need **Python 3.10 or newer** (tested with Python 3.14 on Windows 11).

```
pip install -r requirements.txt
```

This installs numpy, [manifold3d](https://github.com/elalish/manifold) (geometry), Pillow
(images/PDF) and pyopengltk + PyOpenGL (3D view).

Start the program:

- **Windows:** double-click `Start Gridfinity Toolkit.bat`
- **any system:** `python -m gridfinity_toolkit` in this folder

On first start the window adjusts its height so that no tab needs scrolling (as far as your
screen allows).

---

## Quick start

1. **Baseplate tab:** enter the inner size of your drawer, choose your printer, check the
   picture, click **Send to Bin & Combined Grid**.
2. **Bin tab:** design a bin (size, height, infill), click **Send to Combined Grid**. Repeat for
   every kind of bin you want.
3. **Combined Grid tab:** pick a bin type on the left, click into the grid to place it. Stack
   bins by raising the level. Click **Export print-ready**.
4. Open `Print_plate_Bambu_all_plates.3mf` (Bambu printers) or the single plate files in your
   slicer and print. The `Assembly_sheet.pdf` shows where every part goes.

---

## Tab 1: Baseplate

Here you describe the drawer. The tool computes how many 42 mm Gridfinity cells fit, splits the
area into plates that fit your printer and fills the leftover space.

### Drawer

| Field | Meaning |
| --- | --- |
| **Name** | Project name, used as folder name and shown in the other tabs. It follows the drawer size (`Drawer_500x380`) until you type your own name. |
| **Width X (mm)** | Inner width of the drawer, left to right. |
| **Depth Y (mm)** | Inner depth of the drawer, bottom to top in the picture (front to back in the drawer). |
| **Total tolerance (mm)** | Subtracted from width and depth so the plates do not jam. 1 mm is a good start; use more for wooden drawers that swell. |
| **Min. partial cell (mm)** | Leftover space narrower than this does not become a shortened cell (see below) but a filler strip or stays empty. Default 12 mm, minimum 8 mm. |
| **Baseplate style** | Shape of the plates, as in gridfinity-rebuilt: **thin** (outline only, 5 mm high, least material – default), **skeletonized** (11.75 mm, magnet holes, centre cut out) or **weighted** (11.4 mm, magnet holes, room for a weight underneath). |

### Printer

| Field | Meaning |
| --- | --- |
| **Printer** | Your printer. It determines the largest plate (bed minus 6 mm margin) and is used everywhere: bed checks for bins and the print-plate export. The choice is remembered. |
| **Custom plate size (mm)** | Only active when the printer is set to *Custom*: longest plate edge in mm. |

The line below shows the resulting largest plate and the bed size.

### Partial cells

A drawer is rarely a multiple of 42 mm. The remainder becomes a **partial cell**: a shortened
cell with a proper wall. Partial cells always sit on one side per axis.

| Field | Meaning |
| --- | --- |
| **Remainder from 3 mm as filler strip** | Remainders between 3 mm and the minimum partial cell become flat filler strips so the plates cannot slide. |
| **Partial cells in X / Y** | Which side the shortened cells (and filler strips) are on: left/right and bottom/top. **Shortcut:** click a light (shortened) cell in the picture to move it to the other side. |
| **Output folder** | Where the plate files are written (default `output/`). |

The picture shows the drawer from above: every colour is one plate type (A, B, …), lighter
cells are partial cells, grey stripes are filler strips. The text box lists all plates to print.

### Buttons (bottom left)

- **Send to Bin & Combined Grid** – saves the grid as a project *without* generating plates.
  It then appears in the project lists of the other two tabs. Use this while planning.
- **Generate files** – also writes the baseplates: one file with all print plates for your
  printer plus intermediate files (see [What gets exported](#what-gets-exported)).

---

## Tab 2: Bin

Design one bin and see it in 3D. The bins follow gridfinity-rebuilt: thin walls, by default
hollow feet ("lite"), and a **stacking lip** on top so another bin can sit on it.

### Name and size

| Field | Meaning |
| --- | --- |
| **Name** | Name of the bin, shown in the Combined Grid and used in file names. Default names count up (`Bin 1`, `Bin 2`, …). |
| **Width X / Depth Y (cells)** | Size in 42 mm cells. The arrows step by whole cells; you can type half cells like `1.5`. |
| **+ partial cell mm** | An additional shortened cell (12–41 mm) on that axis, e.g. to fill the edge strip of a drawer. `0` = none. |
| **Height (mm)** | Height without the lip in mm, e.g. what you measured. The next larger height in units (steps of 3.5 mm) is used. |
| **Height (units)** | Height in Gridfinity units without the lip (6 units = 42 mm, plus about 3.55 mm lip). Changing it sets the mm field. |
| **Stacking lip (stackable)** | The top rim the next bin locks into. Without it the bin is lower but not stackable. |
| **Base** | **lite** (hollow feet, least material – default) or **standard** (solid base), as in gridfinity-rebuilt. |

### Grid from baseplate

A scrollable list of all projects you sent from the Baseplate tab. Select one to see its
partial cells and use the buttons below:

- **+ Add edge strip X / Y (… mm)** – adds that partial cell to your current bin (the bin gets
  bigger). Click the button again (**− Remove …**) to take it off again.
- **+ Add corner cell** – adds both partial cells.
- **single** – makes a bin consisting only of that strip (e.g. a narrow 39 mm bin); the length
  stays adjustable.
- **Remove partial cells** – sets both partial cells back to 0.
- **Delete project** – moves the selected project folder to the recycle bin (after asking).

### Infill and advanced

| Field | Meaning |
| --- | --- |
| **Solid** | Closed walls. |
| **Hexagon cut-outs** | Walls with hexagon holes – saves material and weight. |
| **Hole size / Web (mm)** | Width across flats of the hexagons and the material between two holes. |
| **Also perforate floor** | The floor gets hexagon holes too. |
| **Wall thickness (mm)** | Default 0.8 mm = two lines with a 0.4 mm nozzle. The info box tells you which nozzles print the wall in whole lines. |
| **Magnet holes (6 x 2 mm)** | Four holes per whole cell in the bottom (6.5 mm wide, 2.4 mm deep, 8 mm from the cell edge, as in gridfinity-rebuilt). They line up with the holes of the *skeletonized* and *weighted* baseplates. Off by default. |
| **Output folder** | Where a single bin is saved (default `output/bins`). |

Invalid values are marked **red** and explained in the info box (e.g. a partial cell below
12 mm or a height that is too small). The info box also shows the outer size, weight estimate and
a warning if the bin does not fit your print bed.

### 3D preview

Left drag = rotate, right drag = pan, mouse wheel = zoom, double-click = reset. The grid below
the bin shows its cells in green (partial cells with their real width).

### Buttons (bottom left)

- **Send to Combined Grid** – adds the bin as a *bin type* to the Combined Grid. If you change
  anything afterwards, the name counts up automatically so you do not overwrite the type you
  just sent.
- **Save (STL + 3MF)** – saves this one bin.

**Editing a type:** in the Combined Grid, select a type and click **Edit**. It opens here with
a yellow note; the button now reads **Update type '…'** and updates the type and all bins of that
type already placed. **Stop editing** returns to the Combined Grid without changes.

---

## Tab 3: Combined Grid

Plan the complete drawer on the grid of a baseplate project.

### Project

The list of baseplate projects (scrollable, with **Delete project**). Below it: drawer size,
number of cells and partial cells.

### Levels (stacking)

**Level (units above floor)** is the height of the bin *bottom*:

- **Level 0** – bins standing on the baseplate.
- **Higher levels** – stacked bins. A bin on level *L* needs a bin below with a stacking lip
  whose top is exactly *L* and which supports its whole footprint.

The arrows ▼▲ jump between the existing stacking surfaces (listed below the field).
In the 2D grid on a higher level:

- **light, dashed** bins are stacking surfaces you can place on,
- **red** bins stick through this level (you cannot stack there),
- the bins of the current level are drawn in full colour.

### Bin types

Every type shows its name and, below it, size, height and infill.

| Control | Meaning |
| --- | --- |
| click a type | selects it: clicking a free cell places this type, and all bins of this type are **highlighted yellow** in the grid |
| **rotated (key R)** | swaps width and depth when placing |
| **Edit** | opens the type in the Bin tab (see above) |
| **Remove type** | deletes the type from the list; bins already placed stay |
| **Height (units)** | changes the height – see below |
| **Duplicate** | copy of the type with a new name, e.g. to try another height |

**Changing the height:**

- With a **type** selected (click in the list), the height applies to the type and **all its
  placed bins**.
- With a **single bin** selected (click it in the grid), only that bin changes; it becomes its
  own type with a new name.
- Bins stacked on a changed bin move up or down with it. If that would collide with something,
  the bin stays unchanged and the status line tells you.

The line below the height field always says what the change applies to.

### Working in the grid

| Action | Result |
| --- | --- |
| click a free cell | places the selected type (green frame = fits, red = does not fit) |
| drag over free cells | creates a **new bin with its own name** of exactly that size (it becomes a new type) |
| click a bin | selects this single bin (yellow frame); **Esc** deselects |
| right-click or **Del** | removes the bin; bins stacked on it stay (red frame if nothing is below them) |
| **Fill empty cells with type** | fills all free spots of the current level |
| **Clear level** | removes all bins of the current level (with everything stacked on them) |

Bins placed on a partial cell automatically get that cell's width. The small numbers at the
bottom and left edge of each bin are its outer size in mm. Everything is saved automatically.

### 2D grid / 3D view

Switch at the top. The 3D view shows the whole drawer including baseplates and stacks; the
green grid marks the current level. Same mouse controls as in the Bin tab.

### Export (bottom left)

- **Include baseplates** – also put the project's baseplates and filler strips on print plates.
- **Export print-ready (STL + 3MF)** – see below.

---

## What gets exported

All parts are laid **flat on the bed** of your printer (stacked bins too), at least 4 mm apart,
rotated if that fits better, keeping the purge/cutter zone of Bambu X1/P1 printers free.

```
projects/<project>/                     project data the tool needs (project.json, layout.json, summary.txt)
projects/bin_types.json                 bin types shared by all projects

output/<project>/
    Print_plate_Bambu_all_plates.3mf    <- open this: every plate already filled
    Assembly_sheet.pdf                  <- where every part goes
    Baseplates_Bambu_all_plates.3mf     only from "Generate files" in the Baseplate tab
    Single_files/                       only with the option "Single files" (default off)
        K1_<name>_Bin_2x1x6_3x.3mf     one 3MF per different part (with count)
        Print_plate_Bins_Plate_1.3mf    single print plates (work in any slicer)
        Bins_summary.txt
        Assembly_sheet.png
        STL/                            all STL files
        Baseplates/                     single files of the Baseplate tab
```

Projects of older versions (data in `output/<project>/`) are moved to `projects/` on the first
start; their old single-file folders go to the recycle bin.

- **Bambu multi-plate file:** only written for printers with a template in `assets/`
  (currently Bambu Lab P1P/P1S). For other printers the single plate files are put directly into
  the export folder instead.
- **Part ids (K1, K2, …):** identical bins (same size up to rotation, same style) are one part.
  The id appears in the file names, on the print plates and in the assembly sheet.
- **Assembly sheet (PDF):** page 1 shows the drawer in 3D and the parts list, page 2 where the
  baseplates A, B, … go, then one page per level with every bin, its id, name and size; bins
  below are drawn faintly so you can see what a stacked bin sits on.
- File names follow the interface language (German: `Druckplatte_…`, `Aufbauplan.pdf`, …).

---

## Terms

| Term | Meaning |
| --- | --- |
| **cell** | 42 × 42 mm Gridfinity grid square |
| **unit (HE)** | 7 mm of height; a 6-unit bin is 42 mm high plus the lip (4.4 mm nominal, about 3.55 mm with the rounded top) |
| **partial cell** | shortened cell at the drawer edge, 8–41 mm wide (bins: 12–41 mm) |
| **filler strip** | flat strip for leftovers too narrow for a partial cell |
| **stacking lip** | rim on top of a bin that the feet of the next bin lock into |
| **level** | height of a bin's bottom in units; 0 = on the baseplate |

---

## Tips and troubleshooting

- **Something went wrong?** Error messages name the log file: `logs/gridfinity_toolkit.log`.
  It contains every action and the full error details.
- **Red fields** always explain themselves in the info box below.
- **3D view black or missing:** without working OpenGL the tool switches to a slower software
  renderer automatically.
- **Changed the drawer later?** Send the baseplate again under the same name; bins that no longer
  fit the new grid are removed from the plan (the status line tells you how many).
- **Deleted a project by mistake?** It is in the recycle bin.
- **Keep data elsewhere:** set the environment variable `GRIDFINITY_TOOLKIT_DATA` to a folder;
  `projects/`, `output/`, `logs/` and `settings.json` are then kept there.

---

## Command line

Without arguments the GUI starts. With arguments:

```
python -m gridfinity_toolkit baseplate 500 380                    # plates for a 500 x 380 mm drawer
python -m gridfinity_toolkit baseplate 418 238 --partial-x left --plan-only
python -m gridfinity_toolkit bin 2 1 6                            # 2 x 1 cells, 6 units high
python -m gridfinity_toolkit bin 0 4 6 --partial-x 39 --hex       # 39 mm edge strip, 4 cells long
python -m gridfinity_toolkit bin 2 2 6 --base standard --magnets  # solid base with magnet holes
python -m gridfinity_toolkit baseplate --help                     # all options
```

---

## For developers

| Module | Purpose |
| --- | --- |
| `baseplate.py` | Builds baseplates with manifold3d after gridfinity-rebuilt-openscad: a block per plate minus one profile cutter per cell (styles thin, skeletonized, weighted). A partial cell gets a narrower cutter, so its edges keep the full profile. |
| `bins.py` | Builds bins with manifold3d after gridfinity-rebuilt-openscad (hulls of rounded rectangles, boolean cut-outs); 42 mm grid, 7 mm units, stacking lip with fillet, lite or standard base, 0.8 mm walls by default. |
| `planner.py` | Grid, stacking rules, part grouping, export, 3D scene. |
| `print_layout.py` | Bed packing (MaxRects with keep-out zones), single plate 3MF and Bambu multi-plate project. |
| `layout_sheet.py` | Assembly sheet PDF. |
| `render.py` | Software renderers (painter's algorithm for the preview fallback, z-buffer for the PDF). |
| `projects.py` | Project folders, layouts, bin types, recycle bin; reads older German file names. |
| `printers.py` | Printer presets, bed sizes, keep-out zones, Bambu templates. |
| `i18n.py` | `T("English text")` – English source strings with German translations in `DE`. |
| `gui/` | Tkinter interface: `app.py` (window, tabs, flags), `theme.py` (flat theme), `widgets.py`, `viewer.py` (OpenGL view), one module per tab. |

**Adding a Bambu printer template:** save any project for that printer in Bambu Studio, take
`Metadata/project_settings.config` out of the 3MF (it is a zip file) and save it as
`assets/bambu_template_<printer name>.config` (non-alphanumeric characters replaced by `_`,
e.g. `bambu_template_Bambu_Lab_A1.config`). The printer must also be listed in `printers.py`.

**Adding a language:** add a dictionary like `DE` in `i18n.py` and register it in `LANGUAGES`
and `TABLES`.

---

## License and credits

Gridfinity Toolkit is released under the [MIT license](LICENSE).

- [Gridfinity](https://gridfinity.xyz/) was created by Zack Freedman (MIT license).
- Baseplate and bin geometry follow
  [gridfinity-rebuilt-openscad](https://github.com/kennetek/gridfinity-rebuilt-openscad) by
  kennetek (MIT license). The profiles and dimensions were re-implemented in Python; the license
  texts are in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
- `assets/bambu_template_*.config` are printer settings exported from Bambu Studio (AGPL-3.0);
  they are not covered by the MIT license of this project.
- Python packages used at runtime (installed via `requirements.txt`, not included here): numpy,
  manifold3d, Pillow, PyOpenGL, pyopengltk – see [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
