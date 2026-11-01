"""
Help window: explains the open tab, so the tabs themselves stay free of explanation texts.
Texts are English (translated via i18n); a line starting with "## " is a heading.
"""

import tkinter as tk
from tkinter import ttk

from .. import i18n
from ..i18n import T
from . import theme

BASEPLATE_HELP = """## Baseplate
Plans the baseplate for a drawer: enter the inner size of the drawer, the tool splits it into plates that fit your print bed and fills the rest with filler strips.

## Shortened cells
If the drawer is not a multiple of 42 mm, one row or column of cells gets shorter. Choose on which side they sit, or click a shortened cell in the picture to move it to the other side.

## Styles
'thin' needs the least material. 'skeletonized' and 'weighted' are thicker and have holes for 6 x 2 mm magnets.

## Saving
Saving creates a project. The Bin tab uses its partial cells, and the Combined Grid plans on its grid."""

BIN_HELP = """## Bin or plate
Type 'Bin' builds a stackable box. Type 'Plate' builds a flat plate on the normal feet: on level 0 of the Combined Grid it closes cells, on a stacking surface it is a lid. A stackable plate has a stacking lip on top, so bins can stand on it.

## Size
Width and depth in cells of 42 mm, half cells like 1.5 are allowed. A partial cell adds a shortened cell in mm, e.g. for an edge strip. 'Grid from baseplate' takes over the partial cells of a project.

## Height
Enter the height in mm (e.g. what you measured) or in units of 7 mm. The next larger half unit is used. The stacking lip comes on top.

## Options
Infill: solid walls or hexagon cut-outs that save material. Compartments: dividers in X and Y. Label shelf: shelf at the back for a label. Scoop: rounded ramp at the front of every compartment. Smooth floor: closes the hollow feet at the top, so the inside floor is flat instead of showing the grid. Magnet holes: for 6 x 2 mm magnets, match the 'skeletonized' and 'weighted' baseplates.

## Saving and the Combined Grid
'Save (STL + 3MF)' saves this one part. 'Send to Combined Grid' adds it as a type for planning. If you edit a type from the Combined Grid, the button updates it there, including all placed parts.

## 3D view
Left drag = rotate, right drag = pan, wheel = zoom, double-click = reset. Green lines = grid cells of the part."""

PLANNER_HELP = """## Combined Grid
Plan a whole drawer: place bins and plates on the grid of a baseplate project, stack them and export everything ready to print.

## Types
New types come from the Bin tab ('Send to Combined Grid'), plates too. The search field above the list filters by name or details (e.g. '2x1', 'hexagon'). Click a type to select it, double-click its name to rename it, double-click its second row to change size, infill and colour. 'Edit' loads it back into the Bin tab. Without a selected type a click does nothing; dragging over free cells creates a bin with the current settings of the Bin tab.

## In the grid
Click a free cell: place the selected type (key R: rotated).
Drag over free cells: new bin of that size with its own name (drag back to the start cell for 1x1).
Click a bin: select it. Ctrl+click: select several. Esc or a click beside the grid: deselect everything, the type too.
Drag a bin: move it, bins stacked on it move along.
Drag the handles of the selected bin: resize it.
Double-click a bin: rename it. If other bins share its type (e.g. pasted copies), it becomes a type of its own, just like when you resize it or change its height.
Right-click or Del: remove it. Bins stacked on it stay on their level; without anything below them they get a red frame and a hint (export still works).
Ctrl+C / Ctrl+V: copy the selected bins, then click where the copy goes.
Ctrl+Z / Ctrl+Y: undo / redo.

## Height
The height field (mm or units) changes the selected type, or only the bins selected in the grid. Selected bins become a new type unless they are all bins of their type. Plates have a fixed height.

## Levels and stacking
The level is the height of the bin bottom in units. On a level above 0 every cell of a bin needs a bin with stacking lip below whose top is exactly at that level; it may stand on several bins (e.g. a 2x1 on two 1x1), but stacking lips must grip it on two opposite sides (a 1x1 cannot stand on a 3x3). In the grid: light dashed = stacking surface of this level, red hatched = sticks through this level, faint = below or above, honeycomb = hexagon infill. A plate on a stacking surface is a lid.

## Drawer height
Optional. With it the box at the bottom shows how much room is left above the current level and turns red when something is too high; the export warns too.

## Export
Every part once as STL/3MF plus print plates for your printer and an assembly sheet (PDF). 'Type colours as filaments' gives every type colour its own filament in the Bambu project and puts each colour on its own plates.

## 3D view
Left drag = rotate, right drag = pan, wheel = zoom. Green = grid of the current level."""

HELP = (("Baseplate", BASEPLATE_HELP), ("Bin", BIN_HELP), ("Combined Grid", PLANNER_HELP))

# German texts live here instead of i18n.py because of their length; they are registered in i18n.DE
i18n.DE.update({
    BASEPLATE_HELP: """## Grundplatte
Plant die Grundplatte für eine Schublade: Innenmaß der Schublade eingeben, das Tool teilt sie in Platten, die auf dein Druckbett passen, und füllt den Rest mit Füllstreifen.

## Verkürzte Zellen
Ist die Schublade kein Vielfaches von 42 mm, wird eine Reihe oder Spalte Zellen kürzer. Wähle, auf welcher Seite sie liegt, oder klicke im Bild auf eine verkürzte Zelle, um sie auf die andere Seite zu legen.

## Stile
'dünn' braucht am wenigsten Material. 'skelettiert' und 'beschwert' sind dicker und haben Löcher für Magnete 6 x 2 mm.

## Speichern
Speichern legt ein Projekt an. Der Behälter-Reiter nutzt seine Teilzellen, das Kombiraster plant auf seinem Raster.""",
    BIN_HELP: """## Behälter oder Platte
Art 'Behälter' baut eine stapelbare Box. Art 'Platte' baut eine flache Platte auf den normalen Füßen: auf Ebene 0 im Kombiraster schließt sie Zellen, auf einer Stapelfläche ist sie ein Deckel. Eine stapelbare Platte hat oben einen Stapelrand, darauf lassen sich Behälter stellen.

## Größe
Breite und Tiefe in Zellen zu 42 mm, halbe Zellen wie 1.5 sind erlaubt. Eine Teilzelle hängt eine verkürzte Zelle in mm an, z. B. für einen Randstreifen. 'Raster aus Grundplatte' übernimmt die Teilzellen eines Projekts.

## Höhe
Höhe in mm (z. B. gemessen) oder in HE zu 7 mm eingeben. Verwendet wird die nächste größere halbe HE. Der Stapelrand kommt oben dazu.

## Optionen
Füllung: geschlossene Wände oder Sechseck-Ausschnitte, die Material sparen. Fächer: Trennwände in X und Y. Beschriftungslasche: Ablage hinten für ein Etikett. Griffmulde: gerundete Rampe vorne in jedem Fach. Glatter Boden: schließt die hohlen Füße oben, sodass der Boden innen eben ist statt das Raster zu zeigen. Magnetlöcher: für Magnete 6 x 2 mm, passend zu den Grundplatten 'skelettiert' und 'beschwert'.

## Speichern und Kombiraster
'Speichern (STL + 3MF)' speichert dieses eine Teil. 'Ins Kombiraster übernehmen' legt es dort als Typ zum Planen an. Bearbeitest du einen Typ aus dem Kombiraster, aktualisiert der Knopf ihn dort, samt aller platzierten Teile.

## 3D-Ansicht
Links ziehen = drehen, rechts ziehen = verschieben, Mausrad = zoomen, Doppelklick = zurücksetzen. Grüne Linien = Rasterzellen des Teils.""",
    PLANNER_HELP: """## Kombiraster
Plane eine ganze Schublade: Behälter und Platten auf dem Raster eines Grundplatten-Projekts platzieren, stapeln und alles druckfertig exportieren.

## Typen
Neue Typen kommen aus dem Behälter-Reiter ('Ins Kombiraster übernehmen'), Platten genauso. Das Suchfeld über der Liste filtert nach Name oder Angaben (z. B. '2x1', 'Sechseck'). Klick auf einen Typ wählt ihn aus, Doppelklick auf den Namen benennt ihn um, Doppelklick auf die zweite Zeile ändert Größe, Füllung und Farbe. 'Bearbeiten' lädt ihn zurück in den Behälter-Reiter. Ist kein Typ gewählt, passiert bei einem Klick nichts; Ziehen über freie Zellen legt einen Behälter mit den aktuellen Einstellungen des Behälter-Reiters an.

## Im Raster
Klick in eine freie Zelle: gewählten Typ platzieren (Taste R: gedreht).
Ziehen über freie Zellen: neuer Behälter in dieser Größe mit eigenem Namen (zurück auf die Startzelle ziehen für 1x1).
Klick auf einen Behälter: auswählen. Strg+Klick: mehrere auswählen. Esc oder Klick neben das Raster: alles abwählen, auch den Typ.
Behälter ziehen: verschieben, darauf gestapelte wandern mit.
Griffe am ausgewählten Behälter ziehen: Größe ändern.
Doppelklick auf einen Behälter: umbenennen. Teilen sich weitere Behälter seinen Typ (z. B. eingefügte Kopien), wird er ein eigener Typ, genau wie beim Größe-Ziehen oder Ändern der Höhe.
Rechtsklick oder Entf: entfernen. Darauf gestapelte Behälter bleiben auf ihrer Ebene; ohne Unterbau werden sie rot umrandet und gemeldet (Export geht trotzdem).
Strg+C / Strg+V: ausgewählte Behälter kopieren, dann dorthin klicken, wo die Kopie hin soll.
Strg+Z / Strg+Y: rückgängig / wiederholen.

## Höhe
Das Höhenfeld (mm oder HE) ändert den gewählten Typ oder nur die im Raster ausgewählten Behälter. Ausgewählte Behälter werden ein neuer Typ, außer es sind alle Behälter ihres Typs. Platten haben eine feste Höhe.

## Ebenen und Stapeln
Die Ebene ist die Höhe der Behälter-Unterkante in HE. Auf einer Ebene über 0 braucht jede Zelle eines Behälters darunter einen Behälter mit Stapelrand, dessen Oberkante genau auf dieser Ebene liegt; er darf auf mehreren Behältern stehen (z. B. ein 2x1 auf zwei 1x1), muss aber an zwei gegenüberliegenden Seiten von Stapelrändern gehalten werden (ein 1x1 auf einem 3x3 geht nicht). Im Raster: hell gestrichelt = Stapelfläche dieser Ebene, rot schraffiert = ragt durch diese Ebene, blass = darunter oder darüber, Waben = Sechseck-Füllung. Eine Platte auf einer Stapelfläche ist ein Deckel.

## Schubladenhöhe
Optional. Damit zeigt der Kasten unten, wie viel Platz über der aktuellen Ebene noch ist, und wird rot, wenn etwas zu hoch ist; auch der Export warnt.

## Export
Jedes Teil einmal als STL/3MF, dazu Druckplatten für deinen Drucker und ein Aufbauplan (PDF). 'Typfarben als Filamente' gibt jeder Typfarbe im Bambu-Projekt ein eigenes Filament und legt jede Farbe auf eigene Platten.

## 3D-Ansicht
Links ziehen = drehen, rechts ziehen = verschieben, Mausrad = zoomen. Grün = Raster der aktuellen Ebene.""",
})


def show(root, tab):
    """Open (or bring to the front) the help for tab index 'tab'."""
    title, text = HELP[tab] if 0 <= tab < len(HELP) else HELP[0]
    for child in root.winfo_children():
        if isinstance(child, tk.Toplevel) and getattr(child, "is_help", False):
            child.destroy()
    win = tk.Toplevel(root)
    win.is_help = True
    win.title(T("Help") + " – " + T(title))
    win.transient(root)
    win.geometry(f"560x600+{root.winfo_rootx() + 80}+{root.winfo_rooty() + 60}")
    frame = ttk.Frame(win, padding=(14, 12))
    frame.pack(fill="both", expand=True)
    bar = ttk.Scrollbar(frame, orient="vertical")
    txt = tk.Text(frame, wrap="word", relief="flat", borderwidth=0, background=theme.BG, padx=4, pady=4,
                  font=(theme.FONT, 10), yscrollcommand=bar.set, cursor="arrow")
    bar.configure(command=txt.yview)
    bar.pack(side="right", fill="y")
    txt.pack(side="left", fill="both", expand=True)
    txt.tag_configure("h", font=(theme.FONT, 12, "bold"), spacing1=12, spacing3=4)
    txt.tag_configure("p", spacing3=3)
    for line in T(text).splitlines():
        if line.startswith("## "):
            txt.insert("end", line[3:] + "\n", "h")
        elif line.strip():
            txt.insert("end", line + "\n", "p")
    txt.configure(state="disabled")
    win.bind("<Escape>", lambda _: win.destroy())
    win.focus_set()
