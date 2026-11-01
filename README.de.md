# Gridfinity Toolkit – Anleitung

*[English version](README.md)*

> **Hinweis: Dieses Projekt ist „vibe coded“.** Es ist großteils mit einem KI-Assistenten (Claude)
> entstanden und durch Drucken getestet, nicht durch eine formale Testsuite. Bei mir funktioniert
> es gut – prüfe die Ergebnisse trotzdem im Slicer, bevor du druckst. Nutzung auf eigene Gefahr.

Ein Desktop-Programm für [Gridfinity](https://gridfinity.xyz/)-Ordnungssysteme, das dich von der
leeren Schublade bis zu fertig belegten Druckplatten bringt:

1. **Basis** – schneidet Gridfinity-Grundplatten passgenau für deine Schublade zu.
2. **Behälter** – entwirft stapelbare Behälter (jede Größe, geschlossen oder mit
   Sechseck-Löchern) mit 3D-Vorschau.
3. **Kombiraster** – plant die ganze Schublade: Behälter aufs Raster setzen, stapeln, in 3D
   ansehen und Druckplatten für deinen Drucker samt Aufbauplan exportieren.

Die Geometrie basiert auf [Gridfinity](https://gridfinity.xyz/) von Zack Freedman und auf
[gridfinity-rebuilt-openscad](https://github.com/kennetek/gridfinity-rebuilt-openscad) von
kennetek (beide MIT, siehe [Herkunft und Lizenzen](#herkunft-und-lizenzen)).

Die Oberfläche gibt es auf **Deutsch und Englisch** (Flaggen oben rechts, die Wahl wird
gespeichert). Zu jedem Feld und Knopf erscheint eine kurze Erklärung, wenn du mit der Maus kurz
darauf bleibst.

---

## Inhalt

- [Installation](#installation)
- [Schnellstart](#schnellstart)
- [Reiter 1: Basis](#reiter-1-basis)
- [Reiter 2: Behälter](#reiter-2-behälter)
- [Reiter 3: Kombiraster](#reiter-3-kombiraster)
- [Was exportiert wird](#was-exportiert-wird)
- [Begriffe](#begriffe)
- [Tipps und Probleme](#tipps-und-probleme)
- [Kommandozeile](#kommandozeile)
- [Herkunft und Lizenzen](#herkunft-und-lizenzen)

---

## Installation

### Windows: fertiges Programm (ohne Python)

1. `Gridfinity-Toolkit-<Version>-windows.zip` aus dem [neuesten Release](https://github.com/verproegler/gridfinity-toolkit/releases/latest) herunterladen.
2. Irgendwohin entpacken (z. B. `Dokumente\Gridfinity Toolkit`).
3. Im entpackten Ordner `Gridfinity Toolkit.exe` starten.

Projekte, Exporte, Logs und Einstellungen landen **neben der .exe** (`projects/`, `output/`,
`logs/`, `settings.json`) – lege den Ordner also dorthin, wo du schreiben darfst. Zum
Aktualisieren die neue Version über den alten Ordner entpacken; deine Daten bleiben erhalten.

Windows SmartScreen warnt beim ersten Start eventuell, weil das Programm nicht signiert ist:
**Weitere Informationen → Trotzdem ausführen**.

### Aus dem Quellcode (alle Systeme, Python)

Du brauchst **Python 3.10 oder neuer** (getestet mit Python 3.14 unter Windows 11).

```
pip install -r requirements.txt
```

Damit werden numpy, manifold3d (Geometrie), Pillow (Bilder/PDF) sowie pyopengltk und PyOpenGL
(3D-Ansicht) installiert.

Starten:

- **Windows:** Doppelklick auf `Start Gridfinity Toolkit.bat`
- **allgemein:** `python -m gridfinity_toolkit` in diesem Ordner

Beim Start passt sich die Fensterhöhe so an, dass kein Reiter scrollen muss (soweit der
Bildschirm reicht).

---

## Schnellstart

1. **Reiter Basis:** Innenmaß der Schublade eintragen, Drucker wählen, Bild prüfen,
   **An Behälter & Kombiraster senden** klicken.
2. **Reiter Behälter:** Behälter einstellen (Größe, Höhe, Füllung), **Ins Kombiraster
   übernehmen** klicken. Für jede Behälterart wiederholen.
3. **Reiter Kombiraster:** links einen Behältertyp wählen, ins Raster klicken, um ihn zu setzen.
   Zum Stapeln die Ebene erhöhen. Dann **Druckfertig exportieren**.
4. `Druckplatte_Bambu_alle_Platten.3mf` (Bambu-Drucker) oder die einzelnen Plattendateien im
   Slicer öffnen und drucken. Der `Aufbauplan.pdf` zeigt, wohin jedes Teil gehört.

---

## Reiter 1: Basis

Hier beschreibst du die Schublade. Das Tool rechnet aus, wie viele 42-mm-Zellen hineinpassen,
teilt die Fläche in Platten auf, die auf deinen Drucker passen, und füllt den Rest auf.

### Schublade

| Feld | Bedeutung |
| --- | --- |
| **Name** | Projektname, wird zum Ordnernamen und erscheint in den anderen Reitern. Er folgt der Schubladengröße (`Schublade_500x380`), bis du selbst einen Namen eintippst. |
| **Breite X (mm)** | Innenbreite der Schublade von links nach rechts. |
| **Tiefe Y (mm)** | Innentiefe, im Bild von unten nach oben (in der Schublade von vorne nach hinten). |
| **Toleranz gesamt (mm)** | Wird von Breite und Tiefe abgezogen, damit die Platten nicht klemmen. 1 mm ist ein guter Anfang, bei Holzschubladen eher mehr. |
| **Min. Teilzelle (mm)** | Reste, die schmaler sind, werden keine gekürzte Zelle (siehe unten), sondern Füllleiste oder bleiben frei. Standard 12 mm, mindestens 8 mm. |
| **Grundplatten-Stil** | Form der Platten wie bei gridfinity-rebuilt: **dünn** (nur Kontur, 5 mm hoch, am wenigsten Material – Standard), **skelettiert** (11,75 mm, Magnetlöcher, Mitte ausgespart) oder **beschwert** (11,4 mm, Magnetlöcher, Platz für ein Gewicht darunter). |

### Drucker

| Feld | Bedeutung |
| --- | --- |
| **Drucker** | Dein Drucker. Er bestimmt die größte Platte (Bett minus 6 mm Rand) und gilt überall: Bettprüfung der Behälter und Export der Druckplatten. Die Wahl wird gespeichert. |
| **Plattengröße individuell (mm)** | Nur aktiv bei Drucker *Individuell*: größte Kantenlänge einer Platte. |

Darunter steht die sich ergebende größte Platte und die Bettgröße.

### Teilzellen

Eine Schublade ist selten ein Vielfaches von 42 mm. Der Rest wird zur **Teilzelle**: einer
gekürzten Zelle mit vollwertiger Wand. Teilzellen liegen je Achse immer auf einer Seite.

| Feld | Bedeutung |
| --- | --- |
| **Rest ab 3 mm als Füllleiste** | Reste zwischen 3 mm und der Mindest-Teilzelle werden flache Leisten, damit nichts verrutscht. |
| **Teilzellen in X / Y** | Auf welcher Seite die gekürzten Zellen (und Füllleisten) liegen: links/rechts und unten/oben. **Abkürzung:** Klick im Bild auf eine helle (gekürzte) Zelle legt sie auf die andere Seite. |
| **Ausgabeordner** | Wohin die Plattendateien geschrieben werden (Standard `output/`). |

Das Bild zeigt die Schublade von oben: jede Farbe ist ein Plattentyp (A, B, …), helle Zellen
sind Teilzellen, graue Streifen Füllleisten. Im Textfeld steht, was zu drucken ist.

### Knöpfe (unten links)

- **An Behälter & Kombiraster senden** – speichert das Raster als Projekt, *ohne* Platten zu
  erzeugen. Es erscheint dann in den Projektlisten der anderen Reiter. Ideal zum Planen.
- **Dateien erzeugen** – schreibt zusätzlich die Grundplatten: eine Datei mit allen Druckplatten
  für deinen Drucker plus Zwischendateien (siehe [Was exportiert wird](#was-exportiert-wird)).

---

## Reiter 2: Behälter

Hier entwirfst du einen einzelnen Behälter und siehst ihn in 3D. Die Behälter folgen
gridfinity-rebuilt: dünne Wände, standardmäßig hohle Füße („lite“) und oben ein **Stapelrand**,
in den der nächste Behälter einrastet.

### Name und Größe

| Feld | Bedeutung |
| --- | --- |
| **Name** | Name des Behälters, erscheint im Kombiraster und im Dateinamen. Standardnamen zählen hoch (`Behälter 1`, `Behälter 2`, …). |
| **Breite X / Tiefe Y (Zellen)** | Größe in 42-mm-Zellen. Die Pfeile springen in ganzen Zellen, halbe wie `1.5` kannst du eintippen. |
| **+ Teilzelle mm** | Zusätzliche gekürzte Zelle (12–41 mm) auf dieser Achse, z. B. für den Randstreifen einer Schublade. `0` = keine. |
| **Höhe (mm)** | Höhe ohne Stapelrand in mm, z. B. was du gemessen hast. Genommen wird die nächstgrößere Höhe in HE (Schritte von 3,5 mm). |
| **Höhe (HE)** | Höhe in Gridfinity-Einheiten ohne Stapelrand (6 HE = 42 mm, dazu ca. 3,55 mm Rand). Eine Änderung setzt das mm-Feld passend. |
| **Stapelrand (stapelbar)** | Oberer Rand zum Stapeln. Ohne ist der Behälter niedriger, aber nicht stapelbar. |
| **Boden** | **lite** (hohle Füße, am wenigsten Material – Standard) oder **standard** (massiver Boden), wie bei gridfinity-rebuilt. |

### Raster aus Basis

Eine Liste (zum Scrollen) aller Projekte, die du aus dem Basis-Reiter gesendet hast. Wähle eins
aus, dann siehst du seine Teilzellen und kannst die Knöpfe darunter nutzen:

- **+ Randstreifen X / Y (… mm) anhängen** – hängt diese Teilzelle an deinen aktuellen Behälter
  an (er wird größer). Nochmal klicken (**− … entfernen**) nimmt sie wieder weg.
- **+ Eckzelle anhängen** – hängt beide Teilzellen an.
- **einzeln** – macht einen Behälter nur aus diesem Streifen (z. B. einen schmalen 39-mm-Behälter),
  die Länge bleibt einstellbar.
- **Teilzellen entfernen** – setzt beide Teilzellen auf 0.
- **Projekt löschen** – verschiebt den gewählten Projektordner nach Rückfrage in den Papierkorb.

### Füllung und Erweitert

| Feld | Bedeutung |
| --- | --- |
| **Geschlossen** | Durchgehende Wände. |
| **Sechseck-Ausstanzung** | Wände mit Sechseck-Löchern, spart Material und Gewicht. |
| **Lochgröße / Steg (mm)** | Schlüsselweite der Sechsecke und Materialbreite zwischen zwei Löchern. |
| **Boden auch lochen** | Auch der Boden bekommt Sechseck-Löcher. |
| **Wandstärke (mm)** | Standard 0,8 mm = zwei Linien mit 0,4er Düse. Das Infofeld zeigt, welche Düsen die Wand in ganzen Linien drucken. |
| **Magnetlöcher (6 x 2 mm)** | Vier Löcher pro ganzer Zelle im Boden (6,5 mm breit, 2,4 mm tief, 8 mm vom Zellrand, wie bei gridfinity-rebuilt). Sie liegen genau über den Löchern der Grundplatten *skelettiert* und *beschwert*. Standardmäßig aus. |
| **Ausgabeordner** | Wohin ein einzelner Behälter gespeichert wird (Standard `output/bins`). |

Ungültige Werte werden **rot** markiert und im Infofeld erklärt (z. B. Teilzelle unter 12 mm
oder zu geringe Höhe). Das Infofeld zeigt außerdem Außenmaß, geschätztes Gewicht und eine
Warnung, wenn der Behälter nicht aufs Druckbett passt.

### 3D-Vorschau

Links ziehen = drehen, rechts ziehen = verschieben, Mausrad = zoomen, Doppelklick =
zurücksetzen. Das Raster unter dem Behälter zeigt seine Zellen in Grün (Teilzellen mit ihrer
echten Breite).

### Knöpfe (unten links)

- **Ins Kombiraster übernehmen** – übernimmt den Behälter als *Behältertyp* ins Kombiraster.
  Änderst du danach etwas, zählt der Name automatisch hoch, damit du den gerade übernommenen Typ
  nicht überschreibst.
- **Speichern (STL + 3MF)** – speichert diesen einen Behälter.

**Typ bearbeiten:** Im Kombiraster einen Typ wählen und **Bearbeiten** klicken. Er öffnet sich
hier mit einem gelben Hinweis, der Knopf heißt dann **Typ '…' aktualisieren** und ändert den Typ
und alle schon platzierten Behälter dieses Typs. **Bearbeitung beenden** führt ohne Änderung
zurück ins Kombiraster.

---

## Reiter 3: Kombiraster

Hier planst du die komplette Schublade auf dem Raster eines Basis-Projekts.

### Projekt

Die Liste der Basis-Projekte (zum Scrollen, mit **Projekt löschen**). Darunter stehen
Schubladengröße, Zellenzahl und Teilzellen.

### Ebenen (Stapeln)

**Ebene (HE über Boden)** ist die Höhe der *Unterkante* eines Behälters:

- **Ebene 0** – Behälter direkt auf der Basis.
- **Höhere Ebenen** – gestapelte Behälter. Ein Behälter auf Ebene *L* braucht darunter einen
  Behälter mit Stapelrand, dessen Oberkante genau *L* ist und der seine ganze Grundfläche trägt.

Die Pfeile ▼▲ springen zwischen den vorhandenen Stapelflächen (stehen unter dem Feld). Im
2D-Raster auf einer höheren Ebene gilt:

- **hell gestrichelt** = Stapelfläche, darauf kannst du setzen,
- **rot** = ragt durch diese Ebene (dort kann nichts gestapelt werden),
- Behälter der aktuellen Ebene sind voll farbig.

### Behältertypen

Jeder Typ zeigt seinen Namen und darunter Größe, Höhe und Füllung.

| Bedienelement | Bedeutung |
| --- | --- |
| Typ anklicken | wählt ihn aus: Klick in eine freie Zelle setzt diesen Typ, alle Behälter dieses Typs werden im Raster **gelb hervorgehoben** |
| **gedreht (Taste R)** | tauscht beim Setzen Breite und Tiefe |
| **Bearbeiten** | öffnet den Typ im Behälter-Reiter (siehe oben) |
| **Typ entfernen** | löscht den Typ aus der Liste, platzierte Behälter bleiben |
| **Höhe (HE)** | ändert die Höhe, siehe unten |
| **Duplizieren** | Kopie des Typs mit neuem Namen, z. B. um eine andere Höhe auszuprobieren |

**Höhe ändern:**

- Ist ein **Typ** gewählt (Klick in der Liste), gilt die Höhe für den Typ und **alle seine
  platzierten Behälter**.
- Ist ein **einzelner Behälter** gewählt (Klick im Raster), ändert sich nur dieser. Er wird ein
  eigener Typ mit neuem Namen.
- Gestapeltes wandert mit der neuen Oberkante mit. Würde dabei etwas kollidieren, bleibt der
  Behälter unverändert und die Statuszeile sagt Bescheid.

Die Zeile unter dem Höhenfeld zeigt immer, wofür die Änderung gilt.

### Arbeiten im Raster

| Aktion | Ergebnis |
| --- | --- |
| Klick in eine freie Zelle | setzt den gewählten Typ (grüner Rahmen = passt, rot = passt nicht) |
| Ziehen über freie Zellen | legt einen **neuen Behälter mit eigenem Namen** genau dieser Größe an (wird ein neuer Typ) |
| Klick auf einen Behälter | wählt diesen einen Behälter aus (gelber Rahmen), **Esc** hebt die Auswahl auf |
| Rechtsklick oder **Entf** | entfernt den Behälter samt allem, was darauf gestapelt ist |
| **Leere Zellen mit Typ füllen** | füllt alle freien Plätze der aktuellen Ebene |
| **Ebene leeren** | entfernt alle Behälter der aktuellen Ebene (samt Gestapeltem) |

Behälter auf einer Teilzelle bekommen automatisch deren Breite. Die kleinen Zahlen unten und
links an jedem Behälter sind sein Außenmaß in mm. Alles wird automatisch gespeichert.

### 2D-Raster / 3D-Ansicht

Oben umschalten. Die 3D-Ansicht zeigt die ganze Schublade mit Basis und Stapeln, das grüne Raster
markiert die aktuelle Ebene. Maussteuerung wie im Behälter-Reiter.

### Export (unten links)

- **Basis-Platten mitdrucken** – legt auch die Grundplatten und Füllleisten des Projekts auf
  Druckplatten.
- **Druckfertig exportieren (STL + 3MF)** – siehe unten.

---

## Was exportiert wird

Alle Teile liegen **flach auf dem Bett** deines Druckers (auch gestapelte Behälter), mindestens
4 mm auseinander, bei Bedarf gedreht. Die Abstreifzone vorne links bei Bambu X1/P1 bleibt frei.

```
projects/<Projekt>/                      Projektdaten für das Tool (project.json, layout.json, summary.txt)
projects/bin_types.json                  Behältertypen, gemeinsam für alle Projekte

output/<Projekt>/
    Druckplatte_Bambu_alle_Platten.3mf   <- diese öffnen: alle Platten schon belegt
    Aufbauplan.pdf                       <- wohin jedes Teil gehört
    Grundplatten_Bambu_alle_Platten.3mf  nur von „Dateien erzeugen“ im Basis-Reiter
    Einzeldateien/                       nur mit der Option „Einzeldateien“ (Standard aus)
        K1_<Name>_Bin_2x1x6_3x.3mf      eine 3MF je unterschiedlichem Teil (mit Stückzahl)
        Druckplatte_Behaelter_Platte_1.3mf   einzelne Druckplatten (für jeden Slicer)
        Behaelter_Uebersicht.txt
        Aufbauplan.png
        STL/                             alle STL-Dateien
        Grundplatten/                    Einzeldateien des Basis-Reiters
```

Projekte älterer Versionen (Daten in `output/<Projekt>/`) werden beim ersten Start nach
`projects/` verschoben; ihre alten Einzeldateien-Ordner kommen in den Papierkorb.

- **Bambu-Sammeldatei:** gibt es nur für Drucker mit Vorlage in `assets/` (derzeit Bambu Lab
  P1P/P1S). Bei anderen Druckern liegen stattdessen die einzelnen Druckplatten direkt im
  Exportordner.
- **Teile-Kennung (K1, K2, …):** Gleiche Behälter (gleiche Größe bis auf Drehung, gleicher Stil)
  sind ein Teil. Die Kennung steht in den Dateinamen, auf den Druckplatten und im Aufbauplan.
- **Aufbauplan (PDF):** Seite 1 zeigt die Schublade in 3D und die Teileliste, Seite 2 wohin die
  Grundplatten A, B, … gehören, danach eine Seite pro Ebene mit jedem Behälter, seiner Kennung,
  Name und Größe. Darunterliegendes ist blass gezeichnet, damit klar ist, worauf gestapelt wird.
- Dateinamen folgen der Sprache der Oberfläche (Englisch: `Print_plate_…`, `Assembly_sheet.pdf`, …).

---

## Begriffe

| Begriff | Bedeutung |
| --- | --- |
| **Zelle** | 42 × 42 mm großes Gridfinity-Rasterfeld |
| **HE (Höheneinheit)** | 7 mm Höhe; ein 6-HE-Behälter ist 42 mm hoch plus Stapelrand (4,4 mm nominal, mit abgerundeter Spitze ca. 3,55 mm) |
| **Teilzelle** | gekürzte Zelle am Schubladenrand, 8–41 mm breit (Behälter: 12–41 mm) |
| **Füllleiste** | flache Leiste für Reste, die für eine Teilzelle zu schmal sind |
| **Stapelrand** | Rand oben am Behälter, in den die Füße des nächsten Behälters greifen |
| **Ebene** | Höhe der Behälter-Unterkante in HE; 0 = auf der Basis |

---

## Tipps und Probleme

- **Etwas schiefgelaufen?** Fehlermeldungen nennen die Logdatei `logs/gridfinity_toolkit.log`.
  Dort steht jede Aktion samt allen Fehlerdetails.
- **Rote Felder** erklären sich immer im Infofeld darunter.
- **3D-Ansicht schwarz oder fehlt:** Ohne funktionierendes OpenGL schaltet das Tool automatisch
  auf eine langsamere Software-Darstellung um.
- **Schublade nachträglich geändert?** Die Basis unter gleichem Namen erneut senden. Behälter, die
  nicht mehr ins neue Raster passen, werden aus der Planung entfernt (die Statuszeile nennt die
  Anzahl).
- **Projekt versehentlich gelöscht?** Es liegt im Papierkorb.
- **Daten woanders ablegen:** Umgebungsvariable `GRIDFINITY_TOOLKIT_DATA` auf einen Ordner setzen,
  dann liegen `projects/`, `output/`, `logs/` und `settings.json` dort.

---

## Kommandozeile

Ohne Argumente startet die Oberfläche. Mit Argumenten:

```
python -m gridfinity_toolkit baseplate 500 380                    # Platten für eine 500 x 380 mm Schublade
python -m gridfinity_toolkit baseplate 418 238 --partial-x left --plan-only
python -m gridfinity_toolkit bin 2 1 6                            # 2 x 1 Zellen, 6 HE hoch
python -m gridfinity_toolkit bin 0 4 6 --partial-x 39 --hex       # 39-mm-Randstreifen, 4 Zellen lang
python -m gridfinity_toolkit bin 2 2 6 --base standard --magnets  # massiver Boden mit Magnetlöchern
python -m gridfinity_toolkit baseplate --help                     # alle Optionen
```

Hinweise zum Aufbau des Codes, zum Hinzufügen weiterer Bambu-Drucker und Sprachen stehen in der
[englischen README](README.md#for-developers).

---

## Herkunft und Lizenzen

Gridfinity Toolkit steht unter der [MIT-Lizenz](LICENSE).

- [Gridfinity](https://gridfinity.xyz/) stammt von Zack Freedman (MIT-Lizenz).
- Die Geometrie von Grundplatten und Behältern folgt
  [gridfinity-rebuilt-openscad](https://github.com/kennetek/gridfinity-rebuilt-openscad) von
  kennetek (MIT-Lizenz). Profile und Maße wurden in Python nachgebaut; die Lizenztexte stehen in
  [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
- `assets/bambu_template_*.config` sind aus Bambu Studio exportierte Druckereinstellungen
  (AGPL-3.0); sie fallen nicht unter die MIT-Lizenz dieses Projekts.
- Zur Laufzeit genutzte Python-Pakete (per `requirements.txt` installiert, nicht enthalten):
  numpy, manifold3d, Pillow, PyOpenGL, pyopengltk – siehe
  [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
