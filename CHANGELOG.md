# Changelog

All notable changes to Gridfinity Toolkit. Dates are YYYY-MM-DD.

## [1.0.0] – 2026-11-01

First public release.

### Added
- Windows program (`Gridfinity Toolkit.exe`, no Python needed) built with PyInstaller via
  `packaging/build_exe.bat`; user data is kept next to the .exe.
- Combined Grid, 3D view: option **"Grey out other levels"** (on by default). Bins that do not
  start on the current level are drawn grey and see-through, so you can see what is below them.
- Export option **"Single files"** in the Combined Grid and the Baseplate tab (off by default),
  plus `--single-files` on the command line.
- Disclaimer in the README that the project is vibe coded; this changelog.

### Changed
- Stacking: a bin may now stand on **several** bins (e.g. a 2x1 on two 1x1), as long as every
  cell has a stacking lip at the right height below it **and** lips grip it on two opposite sides
  (every row left and right, or every column front and back). A 1x1 on a 3x3 is no longer allowed
  (it was before, although it cannot hold). Moving, resizing, changing the height and deleting
  handle bins that bridge several supports.
- Folder layout: project data now lives in `projects/<project>/` (and `projects/bin_types.json`);
  `output/<project>/` only gets the assembly sheet and the file with all print plates. Single
  files go to `output/<project>/Single_files/` only when the option is on. The Baseplate tab writes
  `Baseplates_Bambu_all_plates.3mf`, so it no longer overwrites the planner's print plates.
- Projects of older versions are moved from `output/` to `projects/` on the first start; their old
  single-file folders go to the recycle bin.
