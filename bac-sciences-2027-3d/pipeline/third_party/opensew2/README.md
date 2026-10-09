# Clothing Design for Blender

**Draw flat pattern pieces, sew them, and drape them onto your character — a pattern-based garment workflow that lives entirely inside Blender.**

Free and open source. No subscription, no login server, no external dependencies: a pure-Python add-on on top of Blender's own cloth solver.

![Draft, arrange, sew, drape, grab](docs/demo.gif)

## What it does

- **Measures your character.** Point it at any rigged body mesh. Landmarks are read off the *mesh*, not off bone names: the waist is the narrowest section, the hip the fullest over the seat, the chest the fullest below the shoulder. Rigs disagree about where a "chest" bone belongs — CC4 puts it at 71 % of stature and Mixamo at 76 %, 8 cm apart on the same body — and drafting from that instead is how a block ends up with an armhole down at the waist. Tested across bodies from 145 cm to 217 cm, chest 86 to 117 cm, in `tests/test_bodies.py`. It takes a stack of cross-sections and the limb axes from the armature, masking the arms and head out by skin weight so a figure with its arms down doesn't measure as having a 112 cm waist.
- **Drafts garments from those measurements.** Nine parametric blocks — T-shirt, tank top, skirt, trousers, jumpsuit, dress, jacket, hoodie, flat panel — drawn the way a pattern cutter would: the neckline is solved to the true neck girth, the armhole to the biceps, and the sleeve cap is solved by bisection so it measures the same as the armhole it's sewn to. A cap longer than its armhole is what gathers a sleeve into a crumpled mess.
- **Knows men from women.** The figure is read off the measured proportions (or set by hand) and each block follows that figure's drafting rules: scooped vs crew neck, sloped vs square shoulder, side seams that curve in at the waist vs straight, hem cut to the hip, trouser rise at the waist vs below it.
- **Lets you draw your own.** Click points on the grid in the 2D pattern view, click the first point to close, name the edges, sew them. Every piece has Width and Length, and a garment has a Size that scales all its pieces together. *Counterpart* mirrors a piece to the other side of the body and stitches the edges that meet — draw the front, get the back.
- **Sews and drapes in four phases.** Stitch (sewing springs pull the seams closed at low gravity), weld (paired seam vertices merge into one continuous surface), settle (full gravity), and for outfits **relax** - a finishing pass that softens the fabric, takes it in a touch so it wraps the body, and lets it rest, because the welded rest shape otherwise holds its ballooned memory forever. Welding matters: springs that never stop pulling crush the fabric into wrinkles.
- **Grab tool.** Drag on the garment while it simulates and pull the fabric where you want it.
- **Walks it.** A garment that looks right standing still can gape once the body moves, so *Animate* keys a walk in place to test it on. Two gaits: an ordinary **Walk**, and a **Catwalk** — slower (70 frames a stride against 32), with roughly three times the pelvis roll and five times the hip sway, the shoulders counter-rotating against the hips, and the feet landing on the centre line rather than on two parallel tracks. Both are generated in code from the body's own axes, so they work on whatever rig you bring and no motion-capture asset is redistributed.
- **Outfits, layered.** Build a whole outfit at once, in the order you would dress: bottoms first, tops untucked over them, outerwear last. Each garment is arranged over the layers already worn beneath it — not against bare skin — so a jacket goes *on* the shirt instead of through it, and it collides with the body and everything under it.
- **Finalize.** Freezes the shape, adds thickness, transfers skin weights from the body (smoothed across neighbours, so the crotch of a jumpsuit doesn't tear when the legs separate) and binds to the rig. The garment follows your animation.

![The Clothing Design workspace in Blender: flat pattern pieces in the 2D view on the left, the avatar wearing a sewn tank top and trousers in the middle, and the Clothing sidebar on the right](docs/workspace.png)

The workspace as it actually looks: pattern pieces on the cutting table at the left, the garment on the body in the middle, and every control on the right — the measurements read off this avatar (161 cm, 87/67/92), the pieces and their sewing springs, the garments stacked in the order they are worn, the seam list, and the simulation.

The flat pieces on their own — T-shirt, trousers and jacket, every one drafted from the body in front of it:

![Flat pattern pieces](docs/patterns_row.png)

## Install

Built and tested on **Blender 5.2**. Nothing else to install.

1. Download this repository as a zip (or clone it).
2. Zip the `clothing_design` folder on its own: `zip -r clothing_design.zip clothing_design -x '*__pycache__*'`
3. Blender: *Edit > Preferences > Add-ons > Install from Disk…*, pick the zip, tick **Clothing Design**.

Developing? Symlink `clothing_design/` into `scripts/addons/` instead and edits are live after *Reload Scripts*.

## Five-minute first garment

1. Sidebar (`N`) > **Clothing** > *Workspace* > **Create Clothing Design Workspace**. You get a 2D pattern view on the left, the 3D body in the middle, the physics panel on the right.
2. *Avatar* > **Default > Woman** (or **Man**). A bundled fitting body is imported, set as the avatar and measured.
3. *Patterns* > **Add Garment** > T-Shirt. Four pieces appear in the 2D view, already arranged around the body and sewn.
4. *Garments* > **Sew**. Watch it stitch, weld and settle.
5. *Finalize* > **Finalize** when you like it.

Then try **Outfit** for a full layered set, or **Draw Pattern** to start from your own pieces. The add-on's own [README](clothing_design/README.md) walks through every tool and the reasoning behind it.

## Garments and outfits

| Garment | Pieces | Notes |
|---|---|---|
| T-Shirt | front, back, two sleeves | sleeve cap solved to the armhole |
| Tank Top | front, back | deeper neck and armhole |
| Skirt | front, back | flared |
| Trousers | hip yoke front/back, four leg panels | the yoke is what keeps them up |
| Jumpsuit | bodice with a split hem, sleeves, four legs | one piece shoulder to ankle |
| Dress | front, back (optional sleeves) | A-line shift |
| Jacket | two front halves, back, long sleeves | buttoned below an open lapel V |
| Hoodie | front, back, sleeves, two-piece hood | hood cut to the neckline it joins |
| Flat Panel | one rectangle | for drawing your own |

Outfits follow the figure. **Man:** Casual, Streetwear, Workwear, Full Layers. **Woman:** Casual, Summer, Dress & Jacket, Streetwear, Workwear.

## Fabric

Four presets — Crisp/Tailored, Soft/Jersey, Stiff/Denim, Light/Silk — set tension, compression, shear and bending together. Bending stiffness is the strongest control over how many folds you get. *Take In* shrinks the fabric onto the body once the seams are welded.

## How it's built

- **Quad grid, not triangles.** Each piece is a structured quad grid clipped to its outline (100 % quads, ~85° minimum corner angle). A quad cage subdivides into a clean surface, and its edges run along the pattern's own axes, so the cloth stretches along the grain like woven fabric instead of isotropically like a membrane.
- **The cloth solves on the cage.** Subdivision sits *after* the cloth modifier, so raising the display level costs almost nothing at simulation time: a tank top drapes in 8 s at subdivision 1 and 15 s at 2 (it was 217 s with the subdivision in front of the cloth).
- **Seams belong to the garment**, not the scene, so you can have several garments and re-sew any of them. **Unsew** rebuilds a garment from its flat pieces so you can edit the draft and try again.
- **Layered collision is one-directional** (outer sees inner, never the reverse), because two cloth objects colliding with each other makes Blender's dependency graph cyclic and it silently drops the relationship.

## Avatars

Two fitting bodies are bundled — Nora and Theo, about 0.8 MB each: no textures, no facial morphs, arms held 60° out, feet on the floor. Both are generated with [MPFB2](https://static.makehumancommunity.org/mpfb.html) from the MakeHuman community's CC0 base mesh and targets (`tools/make_default_avatars.py` rebuilds them), carry Mixamo-named rigs with skin weights, and are themselves **public domain (CC0)** — you can ship, modify and reuse them without attribution. Garments drape noticeably cleaner with the arms away from the torso. Use your own character with **Set Avatar**; any rigged mesh with a recognisable spine/arm/leg bone naming (CC4, Mixamo, Rigify) measures automatically.

## Known issues

Honest list — it's a 1.0.

- **Tops ride up a few centimetres during the stitch phase.** Unlimited sewing springs hoist a hip-length top up the body while they close. Capping *Sew Force* around 2–5 measurably lowers a light top's hem, but a heavy garment (the dress) then fails to seat its shoulders, so the default stays unlimited. *Take In* after the weld tightens the drape.
- Layering is one-way: an outer garment sees the inner ones, inner garments don't react to outer ones.
- No darts, pleats or seam allowance yet in the drawn patterns.
- It is Blender's cloth solver: a full outfit takes a couple of minutes to sew, and results are as good as Blender cloth gets.
- Tested on Blender 5.2 only.

## Regenerating the assets

```bash
blender -b --python tools/make_default_avatars.py            # rebuild both bundled avatars (needs MPFB)
blender -b --python tools/render_readme_images.py            # outfit stills, if you want rendered ones
```

## Testing

```bash
blender -b --python tools/make_test_bodies.py         # once: six varied bodies (needs MPFB)
blender -b --python tests/test_bodies.py              # drafts and sews on all of them (~20 min)
blender -b --python tests/test_presets.py            # both avatars, every preset, seam lengths  (~1 min)
blender -b --python tests/test_presets.py -- --drape  # + sews a T-shirt and trousers on each     (~3 min)
blender -b --python tests/test_fit.py                 # drapes every preset on both avatars and checks
                                                      # hems, sleeve reach and floor clearance (~15 min)
```

## Contributing

Issues and pull requests welcome. If a garment drafts badly on your character, the most useful report is the measurements the Avatar panel shows (height, chest, waist, hip, neck) and which block went wrong. Adding a block is one function in `clothing_design/library.py` that returns pieces and seams — the T-shirt is the one to copy.

## License

GPL-3.0-or-later, like Blender itself. The two bundled avatars are separate
works dedicated to the public domain (CC0 1.0) — generated with MPFB2 from the
MakeHuman community's CC0 data; see `clothing_design/assets/README.md`.
