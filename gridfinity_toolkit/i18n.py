"""
Language and settings.

T("English text", **values) returns the text in the selected language. English is the key;
the German translation lives in DE. A missing translation falls back to English (and is
logged once). The chosen language is stored in settings.json.

Adding a language: add a dict like DE, register it in LANGUAGES and TABLES.
"""

import json
import logging

from . import paths

LANGUAGES = {"de": "Deutsch", "en": "English"}
DEFAULT_LANGUAGE = "de"

log = logging.getLogger("gridfinity.i18n")
_lang = DEFAULT_LANGUAGE
_missing = set()

DE = {
    '  -> filler strips':
        '  -> Füllleisten',
    '  -> left empty':
        '  -> bleibt frei',
    '  Filler strip: {n}x  {a} x {b} mm':
        '  Füllleiste: {n}x  {a} x {b} mm',
    '  {l}: {n}x  {sx} x {sy} mm  (cells {c})':
        '  {l}: {n}x  {sx} x {sy} mm  (Zellen {c})',
    ' ({n} holes)':
        ' ({n} Löcher)',
    "'{n}' is not a project folder.":
        "'{n}' ist kein Projektordner.",
    '+ Add corner cell {x} x {y} mm':
        '+ Eckzelle {x} x {y} mm anhängen',
    '+ Add edge strip X ({w} mm)':
        '+ Randstreifen X ({w} mm) anhängen',
    '+ Add edge strip Y ({w} mm)':
        '+ Randstreifen Y ({w} mm) anhängen',
    '+ partial cell mm':
        '+ Teilzelle mm',
    '2D grid':
        '2D-Raster',
    '3D view':
        '3D-Ansicht',
    '3D view failed: {e}':
        '3D-Ansicht fehlgeschlagen: {e}',
    '_hex':
        '_sechseck',
    '_nolip':
        '_ohneRand',
    'Additional shortened cell in mm (12 to 41), e.g. an edge strip. 0 = none.':
        'Zusätzliche gekürzte Zelle in mm (12 bis 41), z. B. ein Randstreifen. 0 = keine.',
    'Adds the bin as a type to the Combined Grid. Settings changed afterwards automatically get a new name.':
        'Übernimmt den Behälter als Typ ins Kombiraster. Danach geänderte Einstellungen bekommen automatisch einen neuen Namen.',
    'Advanced':
        'Erweitert',
    'all_parts':
        'alle_Teile',
    'all_plates':
        'alle_Platten',
    'Also perforate floor':
        'Boden auch lochen',
    "Also puts the project's baseplates and filler strips on their own print plates.":
        'Legt auch die Basis-Platten und Füllleisten des Projekts auf eigene Druckplatten.',
    'another bin':
        'einen anderen Behälter',
    "Applies to: only the selected bin '{n}'":
        "Gilt für: nur den ausgewählten Behälter '{n}'",
    "Applies to: type '{n}' and its {c} placed bins":
        "Gilt für: Typ '{n}' und seine {c} platzierten Behälter",
    'Assembly sheet – {n} bins on {k} level(s), printer {p}':
        'Aufbauplan – {n} Behälter auf {k} Ebene(n), Drucker {p}',
    'Assembly_sheet':
        'Aufbauplan',
    'At least {h} units.':
        'Mindestens {h} HE.',
    'At least {m} mm (one cell).':
        'Mindestens {m} mm (eine Zelle).',
    'At most 12 cells.':
        'Höchstens 12 Zellen.',
    'At most 40 units.':
        'Höchstens 40 HE.',
    'Baseplate':
        'Basis',
    'Baseplates: where plates A, B, ... go':
        'Basis: wohin die Platten A, B, ... gehören',
    'below':
        'darunter',
    'Bin':
        'Behälter',
    'Bin and Combined Grid read projects from\n{d}\nso the project is saved there.':
        'Behälter und Kombiraster lesen Projekte aus\n{d}\nDas Projekt wird deshalb dort gespeichert.',
    "Bin set to {h} units and saved as new type '{n}'.":
        "Behälter auf {h} HE gesetzt und als neuer Typ '{n}' gespeichert.",
    'Bin types':
        'Behältertypen',
    'Bin {n}':
        'Behälter {n}',
    'bins':
        'Behälter',
    'Bins':
        'Behälter',
    'Bins_summary':
        'Behaelter_Uebersicht',
    'bottom':
        'unten',
    'bottom (-Y)':
        'unten (-Y)',
    'Clear level':
        'Ebene leeren',
    'Combined Grid':
        'Kombiraster',
    'Could not move {p} to the recycle bin (code {c}).':
        '{p} konnte nicht in den Papierkorb verschoben werden (Code {c}).',
    'Creates a copy of the selected type with a new name, e.g. to try a different height.':
        'Legt eine Kopie des gewählten Typs mit neuem Namen an, z. B. um eine andere Höhe auszuprobieren.',
    'Custom':
        'Individuell',
    'Custom ({w} mm)':
        'Individuell ({w} mm)',
    'Custom plate size (mm)':
        'Plattengröße individuell (mm)',
    'Delete project':
        'Projekt löschen',
    'Deletes the type from the list. Bins already placed stay.':
        'Löscht den Typ aus der Liste. Schon platzierte Behälter bleiben.',
    'Depth':
        'Tiefe',
    'Depth Y (cells)':
        'Tiefe Y (Zellen)',
    'Depth Y (mm)':
        'Tiefe Y (mm)',
    'Done':
        'Fertig',
    'Drawer':
        'Schublade',
    'Drawer is too small for a plate.':
        'Die Schublade ist zu klein für eine Platte.',
    'Drawer {w} x {d} mm':
        'Schublade {w} x {d} mm',
    'Drawer {w} x {d} mm, {x} x {y} cells\nPartial cells: X {px}, Y {py}':
        'Schublade {w} x {d} mm, {x} x {y} Zellen\nTeilzellen: X {px}, Y {py}',
    'Drawer:    {w} x {d} mm (usable after {t} mm tolerance: {uw} x {ud} mm)':
        'Schublade: {w} x {d} mm (nutzbar nach Toleranz {t} mm: {uw} x {ud} mm)',
    'Drawer_{w}x{d}':
        'Schublade_{w}x{d}',
    'Duplicate':
        'Duplizieren',
    'Each part once as STL/3MF plus ready-made print plates for your printer: everything lies flat, stacked bins too. Includes an assembly sheet (PDF) showing where every part goes.':
        'Jedes Teil einmal als STL/3MF plus fertig belegte Druckplatten für deinen Drucker: alles liegt flach, auch gestapelte Behälter. Dazu ein Aufbauplan (PDF), der zeigt, wohin jedes Teil gehört.',
    'Edit':
        'Bearbeiten',
    'Enter at least 0.5 cells or a partial cell.':
        'Mindestens 0,5 Zellen oder eine Teilzelle angeben.',
    'Error':
        'Fehler',
    'Error: {e}':
        'Fehler: {e}',
    'Export failed: {e}\n\nDetails in the log:\n{l}':
        'Export fehlgeschlagen: {e}\n\nDetails im Log:\n{l}',
    'Export print-ready (STL + 3MF)':
        'Druckfertig exportieren (STL + 3MF)',
    'extends beyond the grid':
        'ragt über das Raster hinaus',
    'Fill empty cells with type':
        'Leere Zellen mit Typ füllen',
    'Filler':
        'Fuellleiste',
    'Fills all free spots of this level with the selected type.':
        'Füllt alle freien Plätze dieser Ebene mit dem gewählten Typ.',
    'First create a project in the Baseplate tab.':
        'Erst im Reiter Basis ein Projekt anlegen.',
    'Generate files':
        'Dateien erzeugen',
    'Generates all plates as STL, a 3MF with the drawer layout and ready-made print plates for your printer.':
        'Erzeugt alle Platten als STL, eine 3MF mit der Anordnung in der Schublade und fertig belegte Druckplatten für deinen Drucker.',
    'Generating failed: {e}\n\nDetails in the log:\n{l}':
        'Erzeugen fehlgeschlagen: {e}\n\nDetails im Log:\n{l}',
    'Grid from baseplate':
        'Raster aus Basis',
    'Grid from the Baseplate tab that you plan on.':
        'Raster aus dem Basis-Reiter, auf dem du planst.',
    'Grid {x} x {y} mm, partial cells: X {px}, Y {py}':
        'Raster {x} x {y} mm, Teilzellen: X {px}, Y {py}',
    'Grid:        {x} x {y} cells, {h} units':
        'Raster:      {x} x {y} Zellen, {h} HE',
    'Grid:      {x} x {y} mm':
        'Raster:    {x} x {y} mm',
    'Gridfinity Toolkit':
        'Gridfinity Toolkit',
    'Grids you sent from the Baseplate tab. Use them to take over their partial cells.':
        'Raster, die du im Basis-Reiter gesendet hast. Damit übernimmst du ihre Teilzellen.',
    'Height':
        'Höhe',
    'Height (mm)':
        'Höhe (mm)',
    'Height in mm without stacking lip, e.g. what you measured. The next larger height in units (steps of 3.5 mm) is used.':
        'Höhe in mm ohne Stapelrand, z. B. was du gemessen hast. Genommen wird die nächstgrößere Höhe in HE (Schritte von 3,5 mm).',
    'Height (units):':
        'Höhe (HE):',
    'Height in Gridfinity units (1 unit = 7 mm), without stacking lip. Sets the mm field to match.':
        'Höhe in Gridfinity-Einheiten (1 HE = 7 mm), ohne Stapelrand. Setzt das mm-Feld passend.',
    'Height in units. With a type selected it changes all bins of that type; with bins selected in the grid only those (they get a new type unless they are all bins of their type).':
        'Höhe in HE. Ist ein Typ gewählt, ändert sie alle Behälter dieses Typs; sind im Raster Behälter gewählt, nur diese (sie werden ein neuer Typ, außer es sind alle Behälter ihres Typs).',
    'Height of the bin bottom in units. 0 = on the baseplate, higher = stacked.':
        'Höhe der Behälter-Unterkante in HE. 0 = auf der Basis, höher = gestapelt.',
    'Height too small: at least {h} units.':
        'Höhe zu klein: mindestens {h} HE.',
    'Height: {e}':
        'Höhe: {e}',
    'hexagon':
        'Sechseck',
    'Hexagon cut-outs':
        'Sechseck-Ausstanzung',
    'Hole size (mm)':
        'Lochgröße (mm)',
    'Baseplates':
        'Grundplatten',
    'Single files':
        'Einzeldateien',
    "Also writes every part as STL/3MF, the single print plates and a text summary into the folder 'Single files'. Off: only the assembly sheet and the file with all print plates.":
        "Schreibt zusätzlich jedes Teil als STL/3MF, die einzelnen Druckplatten und eine Textübersicht in den Ordner 'Einzeldateien'. Aus: nur Aufbauplan und die Datei mit allen Druckplatten.",
    "Also writes every plate as STL and a 3MF with the drawer layout into the folder 'Single files'. Off: only the file with all print plates.":
        "Schreibt zusätzlich jede Platte als STL und ein 3MF mit der Schubladen-Anordnung in den Ordner 'Einzeldateien'. Aus: nur die Datei mit allen Druckplatten.",
    'Saves the project and generates ready-made print plates for your printer.':
        'Speichert das Projekt und erzeugt fertige Druckplatten für deinen Drucker.',
    'Ready-made print plates for your printer (everything lies flat, stacked bins too) and an assembly sheet (PDF) showing where every part goes. Saved in output/<project>.':
        'Fertige Druckplatten für deinen Drucker (alles liegt flach, auch gestapelte Behälter) und ein Aufbauplan (PDF), der zeigt, wo jedes Teil hinkommt. Gespeichert in output/<Projekt>.',
    'Include baseplates':
        'Basis-Platten mitdrucken',
    'Infill':
        'Füllung',
    'Infill:      {v}':
        'Füllung:     {v}',
    'Inner size of the drawer from bottom to top (in the picture).':
        'Innenmaß der Schublade von unten nach oben (im Bild).',
    'Inner size of the drawer from left to right.':
        'Innenmaß der Schublade von links nach rechts.',
    'Invalid cell widths {c} (allowed {a} to {b} mm).':
        'Ungültige Zellbreiten {c} (erlaubt {a} bis {b} mm).',
    'Largest plate: {m} mm (print bed {x} x {y} mm)':
        'Größte Platte: {m} mm (Druckbett {x} x {y} mm)',
    'Layout could not be saved: {e}':
        'Planung konnte nicht gespeichert werden: {e}',
    'left':
        'links',
    'left (-X)':
        'links (-X)',
    'Level':
        'Ebene',
    'Level (units above floor):':
        'Ebene (HE über Boden):',
    'Level 0: directly on the baseplate':
        'Ebene 0: direkt auf der Basis',
    'Level {z} units: stacked on the bins drawn faintly':
        'Ebene {z} HE: gestapelt auf die blass gezeichneten Behälter',
    'Level: please enter a whole or half number from 0.':
        'Ebene: bitte eine ganze oder halbe Zahl ab 0 eingeben.',
    'Levels (bottom): {v} units':
        'Ebenen (Unterkante): {v} HE',
    'Loads the type into the Bin tab. Change it there and update it here, including all placed bins of this type.':
        'Lädt den Typ in den Behälter-Reiter. Dort änderst du ihn und aktualisierst ihn hier, auch alle schon platzierten Behälter dieses Typs.',
    "Longest edge of a plate in mm. Only active when 'Custom' is selected as printer.":
        "Größte Kantenlänge einer Platte in mm. Nur aktiv, wenn als Drucker 'Individuell' gewählt ist.",
    'Makes a separate bin from this partial cell only (length stays adjustable).':
        'Macht einen eigenen Behälter nur aus dieser Teilzelle (Länge bleibt einstellbar).',
    'Material bins: approx. {g} g PLA':
        'Material Behälter: ca. {g} g PLA',
    'Material width between two holes in mm.':
        'Materialbreite zwischen zwei Löchern in mm.',
    'Material:    approx. {g} g PLA ({c} cm3)':
        'Material:    ca. {g} g PLA ({c} cm3)',
    'Max. plate size must be at least {m} mm.':
        'Max. Plattengröße muss mindestens {m} mm sein.',
    'Min. partial cell (mm)':
        'Min. Teilzelle (mm)',
    'Moves the selected project folder to the recycle bin (can be restored from there).':
        'Verschiebt den gewählten Projektordner in den Papierkorb (dort wiederherstellbar).',
    'Must be greater than 0.':
        'Muss größer als 0 sein.',
    'Must not be negative.':
        'Darf nicht negativ sein.',
    "Name: '{n}' is already in use.":
        "Name: '{n}' ist schon vergeben.",
    'Name: please enter a name.':
        'Name: bitte einen Namen eingeben.',
    'Name':
        'Name',
    'Name of the bin. Shown in the Combined Grid and in the file name.':
        'Name des Behälters. Erscheint im Kombiraster und im Dateinamen.',
    'Narrower remainders become a filler strip or stay empty instead of a shortened cell. At least 8 mm.':
        'Schmalere Reste werden keine gekürzte Zelle, sondern Füllleiste oder bleiben frei. Mindestens 8 mm.',
    'Negative values are not allowed.':
        'Negative Werte sind nicht erlaubt.',
    "New bin '{n}' ({x} x {y}) created.":
        "Neuer Behälter '{n}' ({x} x {y}) angelegt.",
    'No type selected: new bins get the Bin tab settings with this height.':
        'Kein Typ gewählt: Neue Behälter bekommen die Einstellungen aus dem Behälter-Reiter mit dieser Höhe.',
    "{n} stacked bins have magnet holes ({names}). The stacking lip below has no magnets, so they hold nothing there.":
        'Gestapelte Behälter mit Magnetlöchern: {n} ({names}). Der Stapelrand darunter hat keine Magnete, dort halten sie also nichts.',
    "{n} bins with magnet holes stand on the 'thin' baseplate ({names}). It has no magnet holes; choose 'skeletonized' or 'weighted' in the Baseplate tab.":
        "Behälter mit Magnetlöchern auf der dünnen Grundplatte: {n} ({names}). Sie hat keine Magnetlöcher – wähle im Reiter Grundplatte 'skelettiert' oder 'beschwert'.",
    'Applies to: the {c} selected bins':
        'Gilt für: die {c} ausgewählten Behälter',
    "{c} bins set to {h} units and saved as new type '{n}'.":
        "{c} Behälter auf {h} HE gesetzt und als neuer Typ '{n}' gespeichert.",
    "Type '{n}' resized to {x} x {y}.":
        "Typ '{n}' auf {x} x {y} geändert.",
    "Bin resized to {x} x {y} and saved as new type '{n}'.":
        "Behälter auf {x} x {y} geändert und als neuer Typ '{n}' gespeichert.",
    'Measured from the drawer floor to the top of the highest part, so you can compare it with the height of your drawer.':
        'Gemessen vom Schubladenboden bis zur Oberkante des höchsten Teils – zum Vergleich mit der Höhe deiner Schublade.',
    'Drawer height (mm):':
        'Schubladenhöhe (mm):',
    'optional':
        'optional',
    'Inside height of the drawer in mm. Optional: if set, the highest point turns red when something is too high, and the export warns.':
        'Innenhöhe der Schublade in mm. Optional: Ist sie gesetzt, wird der höchste Punkt rot, sobald etwas zu hoch ist, und der Export warnt.',
    'The highest part ({n}) reaches {h} mm, but the drawer is only {m} mm high.':
        'Das höchste Teil ({n}) reicht bis {h} mm, die Schublade ist aber nur {m} mm hoch.',
    'Plate {n}':
        'Platte {n}',
    'plate':
        'Platte',
    'stackable':
        'stapelbar',
    'Grip':
        'Griff',
    'no grip':
        'kein Griff',
    'finger hole':
        'Fingerloch',
    'grip slot':
        'Griffschlitz',
    'Plates have a fixed height.':
        'Platten haben eine feste Höhe.',
    'Undone.':
        'Rückgängig gemacht.',
    'Redone.':
        'Wiederhergestellt.',
    'Nothing to undo.':
        'Nichts zum Rückgängigmachen.',
    'Nothing to redo.':
        'Nichts zum Wiederherstellen.',
    'Undo (Ctrl+Z)':
        'Rückgängig (Strg+Z)',
    'Redo (Ctrl+Y)':
        'Wiederherstellen (Strg+Y)',
    'Moved.':
        'Verschoben.',
    '{n} bins moved.':
        '{n} Behälter verschoben.',
    'Select the bins to copy first.':
        'Erst die Behälter zum Kopieren auswählen.',
    '{n} bins copied. Ctrl+V and click where the copy goes.':
        '{n} Behälter kopiert. Strg+V und dann dorthin klicken, wo die Kopie hin soll.',
    'Nothing copied yet: select bins and press Ctrl+C.':
        'Noch nichts kopiert: Behälter auswählen und Strg+C drücken.',
    'Click where the copy goes (Esc cancels).':
        'Dorthin klicken, wo die Kopie hin soll (Esc bricht ab).',
    'Compartments and access':
        'Fächer und Zugriff',
    'Divides the bin into compartments: number in X and in Y (1 = no divider).':
        'Teilt den Behälter in Fächer: Anzahl in X und in Y (1 = keine Trennwand).',
    'Compartments X x Y':
        'Fächer X x Y',
    'Compartments X':
        'Fächer X',
    'Compartments Y':
        'Fächer Y',
    'Label shelf':
        'Beschriftungslasche',
    'Shelf at the back for a label. The 45 degree underside prints without support.':
        'Ablage hinten für ein Etikett. Die 45°-Unterseite druckt ohne Stützen.',
    'Scoop':
        'Griffmulde',
    'Rounded ramp at the front of every compartment, so small parts slide out easily.':
        'Gerundete Rampe vorne in jedem Fach, damit Kleinteile leicht herausrutschen.',
    'Whole number from 1 to 8.':
        'Ganze Zahl von 1 bis 8.',
    '{x}x{y} compartments':
        '{x}x{y} Fächer',
    'label shelf':
        'Beschriftungslasche',
    'scoop':
        'Griffmulde',
    'Compartments: {x} x {y}':
        'Fächer:      {x} x {y}',
    'Label shelf: {v}':
        'Lasche:      {v}',
    'Scoop:       {v}':
        'Griffmulde:  {v}',
    'Plate:       {x} x {y} cells':
        'Platte:      {x} x {y} Zellen',
    'Stackable:   {v}':
        'Stapelbar:   {v}',
    'Grip:        {v}':
        'Griff:       {v}',
    'Type colours as filaments (AMS)':
        'Typfarben als Filamente (AMS)',
    'In the Bambu project every type colour becomes its own filament, e.g. for the AMS. Baseplates use filament 1. Off: everything in one filament.':
        'Im Bambu-Projekt wird jede Typfarbe ein eigenes Filament, z. B. für das AMS. Grundplatten nutzen Filament 1. Aus: alles in einem Filament.',
    'Print time: approx. {t} in total (rough estimate for the 0.2 mm standard profile, +-20 %)':
        'Druckzeit: ca. {t} insgesamt (grobe Schätzung für das 0,2-mm-Standardprofil, ±20 %)',
    'Print time approx. {t} (rough estimate).':
        'Druckzeit ca. {t} (grobe Schätzung).',
    'Highest point':
        'Höchster Punkt',
    'only the baseplate':
        'nur die Grundplatte',
    '{n}, top at {z} units':
        '{n}, Oberkante bei {z} HE',
    '+ stacking lip':
        '+ Stapelrand',
    'Drawer {m} mm: {d} mm too high!':
        'Schublade {m} mm: {d} mm zu hoch!',
    'Drawer {m} mm: {d} mm left':
        'Schublade {m} mm: noch {d} mm Luft',
    'Above level {z} units: {r} mm up to the drawer top, bins up to {h} units fit (with stacking lip).':
        'Über Ebene {z} HE: noch {r} mm bis zur Schubladendecke, Behälter bis {h} HE passen (mit Stapelrand).',
    'Above level {z} units: only {r} mm up to the drawer top, no bin fits there.':
        'Über Ebene {z} HE: nur noch {r} mm bis zur Schubladendecke, dort passt kein Behälter mehr.',
    'Enter the drawer height to see how much room is left above each level.':
        'Schubladenhöhe eintragen, um den Platz über jeder Ebene zu sehen.',
    'Help for this tab (F1)':
        'Hilfe zu diesem Reiter (F1)',
    'Help':
        'Hilfe',
    'Kind':
        'Art',
    'Bin: stackable box. Plate: flat plate on the feet, closes cells or is a lid on a bin.':
        'Behälter: stapelbare Box. Platte: flache Platte auf den Füßen, schließt Zellen oder ist Deckel auf einem Behälter.',
    'Finger hole in the middle or a slot at the front to lift the plate.':
        'Fingerloch in der Mitte oder Schlitz vorne, um die Platte anzuheben.',
    "Bin renamed to '{n}' and saved as its own type.":
        "Behälter in '{n}' umbenannt und als eigener Typ gespeichert.",
    'Ends editing. Changes made meanwhile are applied to the type in the Combined Grid (Ctrl+Z there undoes them).':
        'Beendet die Bearbeitung. Änderungen werden in den Typ im Kombiraster übernommen (Strg+Z dort macht sie rückgängig).',
    '{k} kept their old size, there is no room for the new one.':
        '{k} behielten ihre alte Größe, für die neue ist kein Platz.',
    'Display colour of the type (also the filament colour in the Bambu project)':
        'Anzeigefarbe des Typs (auch die Filamentfarbe im Bambu-Projekt)',
    "Colour of '{n}'":
        "Farbe von '{n}'",
    'Size: whole number from 1 to 12.':
        'Größe: ganze Zahl von 1 bis 12.',
    'Smooth floor':
        'Glatter Boden',
    'Closes the hollow feet at the top, so the inside floor is flat (lite base).':
        'Schließt die hohlen Füße oben, sodass der Boden innen eben ist (Unterbau lite).',
    'Floor:       {v}':
        'Innenboden:  {v}',
    'smooth':
        'glatt',
    'open grid':
        'offenes Raster',
    'open floor':
        'offener Boden',
    'Export anyway?':
        'Trotzdem exportieren?',
    'no':
        'nein',
    'No bins placed yet.':
        'Noch keine Behälter platziert.',
    'no lip':
        'ohne Rand',
    'No project loaded':
        'Kein Projekt geladen',
    'No projects yet.':
        'Noch keine Projekte.',
    'not held: needs stacking lips on two opposite sides (left and right or front and back)':
        'hält nicht: braucht Stapelränder an zwei gegenüberliegenden Seiten (links und rechts oder vorne und hinten)',
    'Grey out other levels':
        'Andere Ebenen ausgrauen',
    '3D view: bins that do not start on the current level are grey, so lower levels are easier to see.':
        '3D-Ansicht: Behälter, die nicht auf der aktuellen Ebene anfangen, sind grau – so sieht man untere Ebenen besser.',
    'no stacking surface below (needed: bins with stacking lip and top at {z} units under every cell)':
        'keine Stapelfläche darunter (nötig: unter jeder Zelle ein Behälter mit Stapelrand und Oberkante {z} HE)',
    'No valid split found.':
        'Keine gültige Aufteilung gefunden.',
    'No {f} in {d}.':
        'Keine {f} in {d}.',
    'none':
        'keine',
    'Not all tabs could be loaded, see log:\n{l}':
        'Nicht alle Reiter konnten geladen werden, siehe Log:\n{l}',
    'Not possible: {e}.':
        'Geht nicht: {e}.',
    'Search':
        'Suche',
    "Shows only the types whose name or details contain this text, e.g. '2x1', '6 HE' or 'hexagon'.":
        "Zeigt nur die Typen, deren Name oder Angaben diesen Text enthalten, z. B. '2x1', '6 HE' oder 'Sechseck'.",
    'Clear the search: show all types.':
        'Suche leeren: alle Typen zeigen.',
    'Note':
        'Hinweis',
    'Nozzle:      {v}':
        'Düse:        {v}',
    'Outer size:  {w} x {d} mm, height {t} mm':
        'Außenmaß:    {w} x {d} mm, Höhe {t} mm',
    'Output folder':
        'Ausgabeordner',
    'overlaps {n}':
        'überschneidet {n}',
    'partial cell':
        'Teilzelle',
    'Partial cell at least {m} mm (or 0 for none).':
        'Teilzelle mindestens {m} mm (oder 0 für keine).',
    'Partial cell must be smaller than {m} mm, otherwise use whole cells.':
        'Teilzelle muss kleiner als {m} mm sein, sonst ganze Zellen verwenden.',
    'Partial cells':
        'Teilzellen',
    'Partial cells and filler strips are at the {x} and {y}.':
        'Teilzellen und Füllleisten liegen {x} bzw. {y}.',
    'Partial cells in X:':
        'Teilzellen in X:',
    'Partial cells in Y:':
        'Teilzellen in Y:',
    'Parts':
        'Teile',
    'Place bins first.':
        'Erst Behälter platzieren.',
    'Plate':
        'Platte',
    'Plate {l}':
        'Platte {l}',
    'Plates':
        'Platten',
    'Please between 0 and 20 mm.':
        'Bitte zwischen 0 und 20 mm.',
    'Please between 0.4 and 1.8 mm.':
        'Bitte zwischen 0,4 und 1,8 mm.',
    'Please between 1 and 10 mm.':
        'Bitte zwischen 1 und 10 mm.',
    'Please between 3 and 20 mm.':
        'Bitte zwischen 3 und 20 mm.',
    'Please between {a} and {b} mm.':
        'Bitte zwischen {a} und {b} mm.',
    'Please between {a} and {b} units.':
        'Bitte zwischen {a} und {b} HE.',
    'Please correct:':
        'Bitte korrigieren:',
    'Please enter a name.':
        'Bitte einen Namen eingeben.',
    'Please enter a number.':
        'Bitte eine Zahl eingeben.',
    'Please fix the fields marked in red first.':
        'Bitte erst die rot markierten Eingaben korrigieren.',
    'Print plates for {p}:':
        'Druckplatten für {p}:',
    'Print_plate':
        'Druckplatte',
    'Printer':
        'Drucker',
    'Printing:    height units do not depend on nozzle/layer':
        'Druck:       HE ist unabhängig von Düse/Schicht',
    'Project':
        'Projekt',
    'Project could not be saved: {e}':
        'Projekt konnte nicht gespeichert werden: {e}',
    'Project file {f} is invalid: {e}':
        'Projektdatei {f} ist ungültig: {e}',
    'Project name. Used as folder name and shown in the Bin and Combined Grid tabs.':
        'Name des Projekts. Wird zum Ordnernamen und erscheint im Behälter- und Kombiraster-Reiter.',
    "Really delete project '{n}'?\n\nThe folder with all its files goes to the recycle bin.":
        "Projekt '{n}' wirklich löschen?\n\nDer Ordner mit allen Dateien kommt in den Papierkorb.",
    'Remainder from 3 mm as filler strip':
        'Rest ab 3 mm als Füllleiste',
    'Remainder: {x} mm (X) / {y} mm (Y)':
        'Rest:      {x} mm (X) / {y} mm (Y)',
    "Remainders between 3 mm and the minimum partial cell are printed as a flat strip so the plates don't slide.":
        'Reste zwischen 3 mm und der Mindest-Teilzelle werden als flache Leiste gedruckt, damit die Platten nicht verrutschen.',
    'Remove all {n} bins on level {z} (including bins stacked on them)?':
        'Alle {n} Behälter auf Ebene {z} HE entfernen (samt darauf gestapelten)?',
    'Remove partial cells':
        'Teilzellen entfernen',
    'Remove type':
        'Typ entfernen',
    'Removed. {n} bins stacked on it now have nothing below them (red).':
        'Entfernt. {n} darauf gestapelte Behälter haben jetzt keinen Unterbau mehr (rot).',
    '{n} bins have nothing below them ({names}); they would float in the drawer.':
        '{n} Behälter haben keinen Unterbau ({names}); sie würden in der Schublade schweben.',
    "The old assembly sheet is still open in another program and could not be replaced. The new one is '{f}'. Close the old PDF before the next export.":
        "Der alte Aufbauplan ist noch in einem anderen Programm geöffnet und konnte nicht ersetzt werden. Der neue heißt '{f}'. Schließe die alte PDF vor dem nächsten Export.",
    'The assembly sheet could not be created: {e}':
        'Der Aufbauplan konnte nicht erstellt werden: {e}',
    '{n} old files are open in another program and were kept: {f}':
        '{n} alte Dateien sind in einem anderen Programm geöffnet und wurden behalten: {f}',
    'Removes all bins of this level including stacked ones.':
        'Entfernt alle Behälter dieser Ebene samt darauf gestapelten.',
    'Removes all partial cells from the current bin.':
        'Entfernt alle Teilzellen aus dem aktuellen Behälter.',
    'right':
        'rechts',
    'right (+X)':
        'rechts (+X)',
    'rotated (key R)':
        'gedreht (Taste R)',
    'Save (STL + 3MF)':
        'Speichern (STL + 3MF)',
    'Saved:\n{f}\n\nin {d}\n\nOpen folder?':
        'Gespeichert:\n{f}\n\nin {d}\n\nOrdner öffnen?',
    'Saves the grid as a project (without generating plates). It is then available in the Bin tab for partial cells and in the Combined Grid for planning.':
        'Speichert das Raster als Projekt (ohne Platten zu erzeugen). Es steht dann im Behälter-Reiter für Teilzellen und im Kombiraster zum Planen bereit.',
    'Saves this one bin as STL and 3MF.':
        'Speichert diesen einen Behälter als STL und 3MF.',
    'Saving failed: {e}\n\nDetails in the log:\n{l}':
        'Speichern fehlgeschlagen: {e}\n\nDetails im Log:\n{l}',
    'Send to Bin & Combined Grid':
        'An Behälter & Kombiraster senden',
    'Send to Combined Grid':
        'Ins Kombiraster übernehmen',
    'single':
        'einzeln',
    'Size':
        'Größe',
    'Size in grid cells of 42 mm. Half cells like 1.5 can be typed in.':
        'Größe in Rasterzellen à 42 mm. Halbe Zellen wie 1.5 lassen sich eintippen.',
    'solid':
        'geschlossen',
    'Solid':
        'Geschlossen',
    'Solid walls.':
        'Durchgehende Wände.',
    'Something went wrong:\n{e}\n\nDetails are in the log:\n{l}':
        'Da ist etwas schiefgelaufen:\n{e}\n\nDie Details stehen im Log:\n{l}',
    'Stack lip:   {v}':
        'Stapelrand:  {v}',
    'Stacking lip (stackable)':
        'Stapelrand (stapelbar)',
    'Stacking surface':
        'Stapelfläche',
    'Stacking surfaces: {v}':
        'Stapelflächen: {v}',
    'Stop editing':
        'Bearbeitung beenden',
    "Subtracted from width and depth so the plates don't jam. 1 mm is a good value.":
        'Wird von Breite und Tiefe abgezogen, damit die Platten nicht klemmen. 1 mm ist ein guter Wert.',
    'Swaps width and depth of the type when placing.':
        'Tauscht Breite und Tiefe des Typs beim Platzieren.',
    'The Combined Grid has no half cells, the type is taken over as {x} x {y} cells.':
        'Halbe Zellen gibt es im Kombiraster nicht, der Typ wird als {x} x {y} Zellen übernommen.',
    "The file '..._Bambu_all_plates.3mf' contains all plates in one Bambu Studio project. The single '..._Plate_n.3mf' files work in any slicer.":
        "Die Datei '..._Bambu_alle_Platten.3mf' enthält alle Platten in einem Bambu-Studio-Projekt. Die einzelnen '..._Platte_n.3mf' funktionieren in jedem Slicer.",
    'The floor gets hexagon holes too.':
        'Auch der Boden bekommt Sechseck-Löcher.',
    'the new height would collide with stacked bins':
        'die neue Höhe würde mit gestapelten Behältern kollidieren',
    'The plate files are written here.':
        'Hierhin werden die Platten-Dateien geschrieben.',
    'The single bin is saved here.':
        'Hierhin wird der einzelne Behälter gespeichert.',
    'This tab could not be loaded:\n{e}\n\nDetails in the log:\n{l}':
        'Dieser Reiter konnte nicht geladen werden:\n{e}\n\nDetails im Log:\n{l}',
    'To print ({n} plate(s)):':
        'Zu drucken ({n} Platte(n)):',
    'To the next stacking surface above.':
        'Zur nächsten Stapelfläche darüber.',
    'To the next stacking surface below.':
        'Zur nächsten Stapelfläche darunter.',
    'too large for the print bed ({w} x {d} mm, {p})':
        'zu groß fürs Druckbett ({w} x {d} mm, {p})',
    'top':
        'oben',
    'top (+Y)':
        'oben (+Y)',
    'Top rim the next bin locks into. Without it the bin is not stackable.':
        'Oberer Rand, in den der nächste Behälter einrastet. Ohne Rand nicht stapelbar.',
    'Top view for planning or 3D view for looking.':
        'Draufsicht zum Planen oder 3D-Ansicht zum Anschauen.',
    'Total tolerance (mm)':
        'Toleranz gesamt (mm)',
    'Triangles:   {n}':
        'Dreiecke:    {n}',
    "Type '{a}' duplicated as '{b}'.":
        "Typ '{a}' als '{b}' dupliziert.",
    "Type '{n}' added.":
        "Typ '{n}' übernommen.",
    "Type '{a}' renamed to '{b}'.":
        "Typ '{a}' in '{b}' umbenannt.",
    "Type '{n}' set to {h} units, {c} placed bins adjusted.":
        "Typ '{n}' auf {h} HE gesetzt, {c} platzierte Behälter angepasst.",
    "Type '{n}' updated, {c} placed bins adjusted.":
        "Typ '{n}' aktualisiert, {c} platzierte Behälter angepasst.",
    'Types could not be saved: {e}':
        'Typen konnten nicht gespeichert werden: {e}',
    'units':
        'HE',
    'Unexpected error':
        'Unerwarteter Fehler',
    'up to {h} units':
        'bis {h} HE',
    "Update type '{n}'":
        "Typ '{n}' aktualisieren",
    'Used on level 0: {u} of {t} cells':
        'Belegt auf Ebene 0: {u} von {t} Zellen',
    'Wall thickness':
        'Wandstärke',
    'Wall thickness (mm)':
        'Wandstärke (mm)',
    'Wall thickness must be between 0.4 and 1.8 mm.':
        'Wandstärke bitte zwischen 0,4 und 1,8 mm.',
    'Wall thickness. 0.8 mm = 2 lines with a 0.4 nozzle.':
        'Dicke der Wände. 0,8 mm = 2 Linien mit 0,4er Düse.',
    'Wall:        {w} mm':
        'Wand:        {w} mm',
    'Walls with hexagon holes: saves material and weight.':
        'Wände mit Sechseck-Löchern: spart Material und Gewicht.',
    'WARNING: does not fit the print bed ({p}, {x} x {y} mm)!':
        'ACHTUNG: passt nicht aufs Druckbett ({p}, {x} x {y} mm)!',
    'Web (mm)':
        'Steg (mm)',
    'Which side the shortened cells (and filler strips) are on.':
        'Auf welcher Seite die gekürzten Zellen (und Füllleisten) liegen.',
    'Whole or half cells only (e.g. 1 or 1.5).':
        'Nur ganze oder halbe Zellen (z. B. 1 oder 1.5).',
    'Whole or half units only.':
        'Nur ganze oder halbe HE.',
    'Width':
        'Breite',
    'Width across flats of the hexagons in mm.':
        'Schlüsselweite der Sechsecke in mm.',
    'Width X (cells)':
        'Breite X (Zellen)',
    'Width X (mm)':
        'Breite X (mm)',
    'yes':
        'ja',
    "You are editing type '{n}' from the Combined Grid. 'Update type' applies the changes.":
        "Du bearbeitest den Typ '{n}' aus dem Kombiraster. 'Typ aktualisieren' übernimmt die Änderungen.",
    'Your printer determines the maximum size of a plate.':
        'Dein Drucker bestimmt, wie groß eine Platte höchstens werden darf.',
    '{ax}: enter at least 0.5 cells or a partial cell.':
        '{ax}: mindestens 0,5 Zellen oder eine Teilzelle angeben.',
    '{ax}: partial cell must be at least {m} mm.':
        '{ax}: Teilzelle muss mindestens {m} mm sein.',
    '{ax}: partial cell must be smaller than {m} mm (use whole cells otherwise).':
        '{ax}: Teilzelle muss kleiner als {m} mm sein (sonst ganze Zellen verwenden).',
    '{d} 1 line':
        '{d} 1 Linie',
    '{d} no':
        '{d} nein',
    '{d} {n} lines':
        '{d} {n} Linien',
    '{k} stayed unchanged because the new height would collide with stacked bins.':
        '{k} blieben unverändert, weil die neue Höhe mit gestapelten Behältern kollidieren würde.',
    '{n} ({w} x {d} mm) does not fit the print bed ({x} x {y} mm).':
        '{n} ({w} x {d} mm) passt nicht aufs Druckbett ({x} x {y} mm).',
    '{n} bins added.':
        '{n} Behälter eingefügt.',
    '{n} bins no longer fit the changed grid and were removed.':
        '{n} Behälter passten nicht mehr zum geänderten Raster und wurden entfernt.',
    '{n} bins, {k} different parts':
        '{n} Behälter, {k} verschiedene Teile',
    '{n} files created in:\n{f}\n\nOpen folder?':
        '{n} Dateien erzeugt in:\n{f}\n\nOrdner öffnen?',
    'Adds the partial cell to your current bin, making it larger. Click again to remove it.':
        'Hängt die Teilzelle an deinen aktuellen Behälter an, er wird entsprechend größer. Nochmal klicken entfernt sie wieder.',
    '− Remove edge strip X ({w} mm)':
        '− Randstreifen X ({w} mm) entfernen',
    '− Remove edge strip Y ({w} mm)':
        '− Randstreifen Y ({w} mm) entfernen',
    '− Remove corner cell {x} x {y} mm':
        '− Eckzelle {x} x {y} mm entfernen',
    'Single_files':
        'Einzeldateien',
    'Style:     {s}, {h} mm high':
        'Stil:      {s}, {h} mm hoch',
    'Unknown baseplate style: {s}':
        'Unbekannter Grundplatten-Stil: {s}',
    'skeletonized (magnets)':
        'skelettiert (Magnete)',
    'thin (lightest)':
        'dünn (am leichtesten)',
    'weighted (magnets, weight)':
        'beschwert (Magnete, Gewicht)',
    'Base:        {v}':
        'Boden:       {v}',
    'Unknown base style: {b}':
        'Unbekannter Boden-Stil: {b}',
    'lite (hollow, lightest)':
        'lite (hohl, am leichtesten)',
    'standard (solid)':
        'standard (massiv)',
    'Baseplate style':
        'Grundplatten-Stil',
    "Shape of the plates (from gridfinity-rebuilt). 'thin' needs the least material; the thick styles hold magnets.":
        "Form der Platten (aus gridfinity-rebuilt). 'dünn' braucht am wenigsten Material, die dicken Stile nehmen Magnete auf.",
    "Bottom of the bin (from gridfinity-rebuilt). 'lite' has hollow feet and needs the least material; 'standard' is solid.":
        "Boden des Behälters (aus gridfinity-rebuilt). 'lite' hat hohle Füße und braucht am wenigsten Material, 'standard' ist massiv.",
    'standard base':
        'Standard-Boden',
    'Magnets:     {v}':
        'Magnete:     {v}',
    '{n} holes for 6 x 2 mm':
        '{n} Löcher für 6 x 2 mm',
    'Magnet holes (6 x 2 mm)':
        'Magnetlöcher (6 x 2 mm)',
    "Four holes per whole cell in the bottom for 6 x 2 mm magnets. Matches the 'skeletonized' and 'weighted' baseplates.":
        "Vier Löcher pro ganzer Zelle im Boden für Magnete 6 x 2 mm. Passt zu den Grundplatten 'skelettiert' und 'beschwert'.",
    'magnets':
        'Magnete',
    'Select all':
        'Alle anwählen',
    '☑ = export, ☐ = placeholder only. Ticks the export box of all types shown (click again to untick them).':
        '☑ = exportieren, ☐ = nur Platzhalter. Setzt bei allen angezeigten Typen das Export-Häkchen (nochmal klicken nimmt sie wieder weg).',
    'Click a type to select it: free cells get this type, and its bins are highlighted. Double-click to rename it. Click the box behind it to export the type or not (placeholder, e.g. for bins you already have).':
        'Typ anklicken zum Auswählen: freie Zellen bekommen diesen Typ, seine Behälter werden hervorgehoben. Doppelklick zum Umbenennen. Kästchen dahinter anklicken: Typ exportieren oder nicht (Platzhalter, z. B. für Behälter, die du schon hast).',
    'placeholder, not exported':
        'Platzhalter, wird nicht exportiert',
    'placeholder':
        'Platzhalter',
    "Type '{n}' is exported.":
        "Typ '{n}' wird exportiert.",
    "Type '{n}' is a placeholder now: it stays in the grid but is not exported.":
        "Typ '{n}' ist jetzt Platzhalter: bleibt im Raster, wird aber nicht exportiert.",
    'All placed types are placeholders: tick at least one type for the export.':
        'Alle platzierten Typen sind Platzhalter: mindestens einen Typ für den Export anhaken.',
    'Not exported (placeholders): {n} bins of the types {t}':
        'Nicht exportiert (Platzhalter): {n} Behälter der Typen {t}',
}

TABLES = {"de": DE}


def T(text, **kw):
    out = text
    table = TABLES.get(_lang)
    if table is not None:
        out = table.get(text)
        if out is None:
            if text not in _missing:
                _missing.add(text)
                log.warning("No %s translation for: %r", _lang, text)
            out = text
    return out.format(**kw) if kw else out


def lang():
    return _lang


def set_lang(code):
    global _lang
    _lang = code if code in LANGUAGES else DEFAULT_LANGUAGE


def load_settings():
    try:
        with open(paths.SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        log.exception("Settings unreadable, using defaults")
        return {}


def save_settings(**changes):
    data = load_settings()
    data.update(changes)
    try:
        with open(paths.SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        log.exception("Could not save settings")


set_lang(load_settings().get("language", DEFAULT_LANGUAGE))
