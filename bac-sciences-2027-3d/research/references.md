# Research, references and licences — 3D collection

Project: **LYCÉE HANNIBAL · TÉBOURBA · BAC SCIENCES 2027** — 3D live fashion collection.
Everything below says *what was used, from where, under which licence, and what was verified in this session*.
Nothing in this folder reproduces a protected logo or graphic: the six visual references supplied by the client were used **as inspiration for placement, mood and graphic ideas only**; every graphic on the garments is original or built from public scientific facts.

## 1. The six supplied references → what was taken from each

| Ref | What the reference shows | Idea retained | What is **original** in our version |
|---|---|---|---|
| 1 | Pink zip hoodie: yoke seam, metal zip, embroidered script, woven crest patch | Silhouette (oversized, dropped shoulder, rib cuffs/hem), yoke seam, metal zip, left-chest woven patch, script on sleeve | Our own crest (Surus + atom ear), our own script lettering (Great Vibes, SIL OFL) reading “Bac Sciences”, our own colours (dusty rose), our own back print (periodic tiles B·Ac·Sc·I) → **H1 ROSE ORBITE** |
| 2 | Cosmic “energy” back print + all-over scarf | Large circular cosmic print on a dark ground; orbit / torus geometry used as a repeat | Procedurally generated spiral-galaxy + three-ellipse atom figure; the quote is replaced by an **unattributed** statement of conservation of energy (the Einstein attribution of the original line could not be verified) → **H3 NUIT COSMIQUE**, **S1 ORBITE** |
| 3 | Grey collegiate hoodie with a back collage (DNA, portrait, Arabic calligraphy, 2027, SCIENCES, varsity badges) | Grey pullover, kangaroo pocket, collage back | Our collage: arched SCIENCES (Graduate, SIL OFL), Surus roundel (original), DNA with correct pairing, Arabic « علوم » set with HarfBuzz, “2027” with an orbit zero, three original badges (Physique / Chimie / SVT) → **H2 GRIS COLLÈGE**, **J1/V1** back arch |
| 4 | “You were born unique” — minimal DNA back print, tiny DNA on the chest | Minimal back print + tiny chest motif | Our DNA (A–T 2 bonds, G–C 3 bonds), French line « ON NAÎT UNIQUE » → **T1 NUIT** |
| 5 | Molecule graphic | A chemical-structure graphic as the main print | **Caffeine**, drawn from RDKit 2D coordinates, formula and molar mass checked in code → **T3 CAFÉINE**, **J2** back, **A3** tote |
| 6 | Periodic-table tiles spelling a word | Tiles spelling a word | **B · Ac · Sc · I** (boron, actinium, scandium, iodine) read “BAC SCI” → **T2 TABLEAU**, **H1** back, patches |

## 2. Scientific facts used on the garments (checked)

* **Tiles** (IUPAC layout: atomic number, symbol, name, mass). Values written in French notation:
  B Z=5 *Bore* 10,81 · Ac Z=89 *Actinium* [227] (no stable isotope → mass number in brackets) · Sc Z=21 *Scandium* 44,956 · I Z=53 *Iode* 126,90.
  Source: IUPAC periodic table / standard atomic weights — https://iupac.org/what-we-do/periodic-table-of-elements/ and https://ciaaw.org/atomic-weights.htm
* **Caffeine**: C₈H₁₀N₄O₂, 1,3,7-trimethylxanthine, M ≈ 194,19 g·mol⁻¹. SMILES `CN1C=NC2=C1C(=O)N(C(=O)N2C)C`. The molecular formula is **asserted in code** (`rdMolDescriptors.CalcMolFormula == "C8H10N4O2"`) every time the artwork is generated. Reference: https://pubchem.ncbi.nlm.nih.gov/compound/Caffeine
* **DNA**: Watson–Crick pairing, A–T joined by 2 hydrogen bonds and G–C by 3; the artwork draws 2 / 3 dots on the rungs accordingly.
* **Punnett square** Aa × Aa → AA, Aa, Aa, aa → genotype 1 : 2 : 1, phenotype 3 : 1 (complete dominance).
* **Conservation of energy** (H3 / cosmic print): « L’énergie ne se crée ni ne se détruit : elle se transforme ». Deliberately **not attributed** to any person.
* **E = mc²** appears on the cosmic print as an equation, not as a quotation.
* **Tébourba** is written « 36°50′N · 9°50′E » (≈ 36.83 °N, 9.83 °E). The ancient town is *Thuburbo Minus*. https://en.wikipedia.org/wiki/Tebourba
* **Surus** — the school mascot is *Surus*, the war elephant associated with Hannibal; ancient authors report that it had a **broken tusk** (Pliny the Elder, *Natural History* 8.11). The mark shows the elephant with an atom-ring ear and a single visible tusk accent. We **do not** use the line « aut viam inveniam aut faciam » with Hannibal’s name: it is Seneca’s, not Hannibal’s.
* **Motto** « TRAVERSER L’INCONNU / عبور المجهول ». The Arabic line is shaped by HarfBuzz (correct joining) but **has not been reviewed by a native Arabic reader** — flagged in the QC report. The word « علوم » (sciences) on the collage is the same.

## 3. Software and data used — sources and licences

| Item | Purpose | Source | Licence |
|---|---|---|---|
| Blender 5.2 (`bpy` wheel from PyPI) | Modelling, cloth, UV, Cycles rendering, glTF export | https://pypi.org/project/bpy/ | GPL-3.0-or-later |
| opensew-2 (clothing_design add-on) | First garment engine (pattern → sewing simulation). Evaluated, then set aside for the shell method (see QC). Kept unmodified in `pipeline/third_party/opensew2` | https://github.com/ (see `third_party/opensew2/SOURCE.txt`) | GPL-3.0-or-later, bundled avatars CC0 |
| clothcode | Reading for cloth-solver lessons (per-vertex mass, self-collision distance, headless baking) | https://github.com (notes in `pipeline/`) | MIT |
| MakeHuman base mesh, skeleton, weights, targets | Body proportions of the avatars (own build + the opensew avatar derives from the same family) | https://github.com/makehumancommunity ; `makehuman==1.3.2` wheel | CC0 (assets) |
| three.js r170 | Interactive viewer (vendored, no CDN) | https://github.com/mrdoob/three.js | MIT |
| @pmndrs studio HDRI | Soft studio reflections | npm package (see `pipeline/README.md`) | CC0 |
| HarfBuzz (`uharfbuzz`), fontTools | Text shaping and glyph outlines (French accents, Arabic joining) | PyPI | MIT / MIT |
| RDKit | Caffeine 2D depiction + formula check | https://www.rdkit.org | BSD-3-Clause |
| NumPy, SciPy, Pillow | Texture compositing | PyPI | BSD / HPND |
| Chromium headless shell | SVG → PNG rasteriser | bundled in the environment | BSD-style |
| Fonts: Archivo, Bricolage Grotesque, Space Grotesk, JetBrains Mono, Instrument Serif, Great Vibes, Pinyon Script, Graduate, Reem Kufi, Noto Kufi Arabic, Aref Ruqaa, Lalezar | Brand typography | Google Fonts repositories | SIL Open Font License 1.1 |

### Hosts that were **not reachable** from this environment (so not used)
download.blender.org, extensions.blender.org, Poly Haven, ambientCG, MPFB2/HumGen asset hosts, Hugging Face, jsDelivr/unpkg, GitHub archive/zip endpoints. Consequences:
* no Poly Haven / ambientCG PBR scans → **procedural PBR cloth** generated in `texlab.py` (albedo + normal + roughness maps, knit/rib/twill/leather/nylon/melton variations);
* no MPFB2/HumGen → the **MakeHuman-derived fitting avatar bundled with opensew-2** is used, shown as a faceless mannequin;
* three.js is **vendored from npm**, not loaded from a CDN.

## 4. Pipeline recommendations from the supplied GitHub list — what was done with them

| Repository (from the list) | Used? | Note |
|---|---|---|
| opensew-2 | Yes (evaluated) | Real sewing simulation worked on simple pieces but was not reliable on oversized shoulders (see QC). |
| clothcode | Read | Solver lessons (see above). |
| GarmentCode / Seamly2D / Awesome-3D-Garments | Read only | Not reachable/not needed for the shell method; no code copied. |
| GarmentDreamer | No | CC BY-NC 4.0 (non-commercial) — avoided. |
| Others (Costumy, blender_clothing_tools, TareminCloth …) | No | Licences/tooling not suited (GPL add-on UIs, GPU-only Rust). |
