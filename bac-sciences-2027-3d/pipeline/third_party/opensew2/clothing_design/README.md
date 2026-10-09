# Clothing Design — a pattern-based garment workflow for Blender

Draw flat pattern pieces, sew them together, and simulate them onto your
character. Built and tested against Blender 5.2.

## Install

The add-on is already installed at
`~/.config/blender/5.2/scripts/addons/clothing_design`.

To install it elsewhere: `Edit > Preferences > Add-ons > Install…` and pick
`clothing_design.zip`, then tick **Clothing Design**.

## The workspace

Sidebar (`N`) > **Clothing** > Workspace > **Create Clothing Design Workspace**.

    ┌──────────────┬─────────────────────────────┬───────────┐
    │ 2D Pattern   │                             │ Outliner  │
    │ (front ortho)│      3D garment on body     ├───────────┤
    ├──────────────┤      + Clothing sidebar     │ Physics   │
    │ Side view    │                             │ properties│
    ├──────────────┴─────────────────────────────┴───────────┤
    │ Timeline                                               │
    └────────────────────────────────────────────────────────┘

The 2D pattern area is the world XZ plane laid out to the +X side of the
avatar, so pattern pieces and the body share one scene and one undo stack.

## Workflow

1. **Default > Woman / Man** — brings in a bundled fitting avatar: Nora or
   Theo, with no clothing, a neutral face, arms held 60 degrees out and the
   feet on the floor. It lands in a `CD_Avatar` collection, is set as the
   avatar and measured in one step. Pressing it again reuses the copy already
   in the scene. Both bodies are generated from the MakeHuman community's
   CC0 base mesh and targets with MPFB2 and carry a Mixamo-named rig with
   skin weights; they are rebuilt from scratch with
   `tools/make_default_avatars.py`, and the .blend files are public domain
   (CC0) — no third-party character license applies. Garments come out
   noticeably cleaner on these avatars than on an animated character,
   because the arms are held away from the torso instead of resting against
   the ribs.
2. **Set Avatar** — or point it at your own body mesh instead. It works out which way it faces from the
   rig's toe bones, and measures it: a stack of horizontal cross-sections plus
   limb axes taken from the armature. Arms and head are masked out using the
   skin weights, so a figure standing with its arms down does not measure as
   having a 112 cm waist.
3. **Figure** — Auto tells a man from a woman by the measured proportions
   (hip to chest girth, waist to hip, shoulder width to hip width; Nora scores
   -1.9, Theo +2.2, zero is the boundary) and every block is then drafted with
   that figure's rules. Override it if the guess is wrong for a stylised body.
   See *Man and woman blocks* below.
4. **Add Garment / Outfit** — nine garments: T-Shirt, Tank Top, Dress, Jacket,
   Hoodie, Skirt, Trousers, Jumpsuit, Flat Panel. **Outfit** builds several at
   once, each on its own layer; the list follows the figure. Man: Casual,
   Streetwear, Workwear, Full Layers. Woman: Casual, Summer, Dress & Jacket,
   Streetwear, Workwear.
   Original note — T-Shirt, Tank Top, Skirt, Trousers or a Flat Panel. Every
   piece is drafted from the measurements: the neckline is solved to 1.12x the
   true neck girth, the armhole to 1.3x the biceps, and the sleeve cap is
   solved by bisection to match the armhole it is sewn to.
5. **Draw Pattern** — click points in the 2D view; click the first point again
   to close (it lights up green when the mouse is on it; Enter still works).
   Points snap to a grid — 1 cm by default, set next to the button, 0 for off —
   and holding Ctrl inverts the snap. Each click run becomes a named edge you
   can sew.
6. **Counterpart** — copies the piece to the other side of the body and sews
   the edges that meet, which is the "draw the front, get the back" step.
7. **Fabric** — pick Crisp/Tailored, Soft/Jersey, Stiff/Denim or Light/Silk.
   Bending stiffness is the strongest control over how many folds appear;
   *Take In* shrinks the fabric onto the body once the seams are welded.
   Note the sign: in Blender a *positive* shrink tightens, negative eases out.
8. **Grab Fabric** — pull the cloth by hand. Drag on the garment to pull it
   while the simulation runs, release to let go, scroll to change the grab
   radius, Esc to finish. It works by hooking the pinned patch, because writing
   pin targets into mesh data mid-simulation stalls the solver.
9. **Sew & Drape** — three phases:
   - *stitch*: cloth sewing springs pull the seams closed at low gravity
   - *weld*: paired seam vertices are merged into one continuous surface
   - *settle*: the garment drapes at full gravity
   Welding matters. Sewing springs never stop pulling, so leaving them on for
   the whole simulation crushes the fabric into wrinkles.
10. **Finalize** — freezes the shape, adds thickness, transfers skin weights
   from the body and binds to the rig, so the garment follows your animation.

## Man and woman blocks

Girths always come from the avatar. On top of them `library.FIGURE` applies
the rules a cutter would, and `Figure` picks the set:

| | Woman | Man |
|---|---|---|
| Front neck depth (tee / tank) | 7.5 / 9.5 cm scoop | 6 / 8.5 cm crew |
| Shoulder | sloped 5.5 cm, point at 93 % of the measured width | 4.5 cm, full width |
| Side seams | curve in at the waist when the hem is below it | straight |
| Hem of a hip-length top | cut to the hip girth | chest width, never under 98 % of the hip |
| Top length | to the hip line | 4.5 cm past it |
| T-shirt sleeve | 15 cm, cuff at 82 % of the cap width | 20 cm, 88 % |
| Trouser rise | waistband at the natural waist | 78 % of the way up from the crotch, band cut to the girth there |

The waist shaping is the side seam's share of the chest-to-waist difference,
capped at 2.2 cm per seam so a small waist never pinches. Both halves of every
seam are drafted to the same length: the jumpsuit's deeper back crotch dip and
the hood's front and back neck edges are each solved against the edge they
are sewn to. `tests/test_presets.py` (headless) imports both avatars, checks
the measurements and figure guess, drafts every preset on each and compares
seam lengths; with `--drape` it also sews a T-shirt and trousers on each and
counts vertices left inside the body.

Neck girth is the narrowest *near-complete* ring above the neck base. The head
is masked out of the profile by its skin weights, and above the last full
slice the smoothed radii decay towards zero; an earlier avatar's neck read
4.6 cm before the ring-completeness check was added. One missing sector per
ring is tolerated, because Mixamo-style weights hand the lower neck to the
head bone and a perfect-ring rule would stop the scan at the trapezius: Theo's
neck read 45 cm under the strict rule and 39 cm with the allowance.

Limb girths get the mirror-image guard. A limb's radius profile is measured
from the verts its vertex groups claim, and near the root that claim depends
on weight-painting style: Mixamo-style weights hand the whole deltoid to the
upper arm, which read as a 50 cm biceps on a 161 cm figure — the armhole
solver then hit its depth cap and every sleeve came out wide enough to swallow
the hand. The root bins of a limb profile are therefore capped by its interior
bins: a real limb never doubles its girth in its top fifth. `tests/test_fit.py`
drapes every preset on both avatars and checks hems, sleeve reach and floor
clearance against the body's own landmarks.

Keeping a jacket on the shoulders of a layered outfit took three separate
mechanisms, found the hard way (every plausible-sounding drafting tweak —
raising the sleeve, drafting the shoulder drop from the measured slope,
enlarging the armhole to clear the deltoid, even squaring the avatar's
shoulders — was tried, simulated and rejected for making other garments
worse):

- the jacket's front halves are sewn together below the lapel V. An
  unfastened open front is marginal physics on any dress form: nothing
  anchors it against the sleeves' weight and it slides off one run in
  three. `preset_jacket(closed_front=False)` still cuts the open version;
- during the stitch phase the collar band of a sleeved top is pinned in
  place (`sim.pin_shoulders`), a tailor's hand on the dress form, released
  from 60% so the neckline can draw in before the weld;
- cloth-on-cloth and cloth-on-body friction is 60 out of Blender's 80, not
  the slick default 5.

Layering itself needed the same kind of fix. Every garment used to be
arranged against the bare body, so an outer one started only its own ease
away from the skin - while the shirt beneath it, once sewn, occupies a shell
several times thicker than that. The jacket was laid out *inside* the shirt,
and no amount of simulation sorts that out: what you see is a jacket whose
sleeves and hem poke out of a t-shirt worn over it. Garments are now arranged
against the body **plus every layer worn under them** (`build.under_bvh`),
and a multi-garment **Sew** re-arranges each layer over the ones already sewn
beneath it, because when the outfit was drafted they were still flat panels.
The finishing pass then lifts any remaining overlap apart before it measures
anything (`sim.lift_off_layers`) - a garment already tangled measures as
snug, so testing first would let exactly the worst case through.

And one more for how the result *looks*: the weld bakes the mid-drape shape
as the cloth's new rest shape, and at fabric stiffness the bending springs
then hold that ballooned memory - a settle can run forever without the
garment ever lying down (measured: 150 extra frames moved the jacket's chest
standoff by one millimetre). **Relax** is the finishing pass that fixes it:
soften the bending to near-zero, take the fabric in a little so it wraps the
body (the take-in is also what keeps the soft garment from sliding off the
shoulders), freeze that as the new rest shape, then re-settle briefly at a
gentle stiffness so it reads as resting cloth rather than shrink wrap. It is
a button next to Settle, and **Add Outfit + Sew** runs it automatically.

How much it takes in is measured, not guessed: the standoff between the
garment and whatever it is worn over decides it, capped at 6 % because
taking a garment in shortens it as well as narrowing it, and past that the
hem climbs far enough to read as cropped. Only the **outermost** garment is
relaxed - the one actually on show. Taking an inner top in rolls its collar
up the neck so it stands proud of the jacket over it, and softening trousers
slides their waistband down the hips. Inner layers are frozen instead: baked
where they settled, solver dropped, collision kept. That also keeps the pass
deterministic, since relaxing advances the scene by a hundred frames and any
other garment still carrying a solver would drift through them unwatched.

## Scaling pieces

Every piece has **Width** and **Length** in its *Arrangement* panel, and every
garment has **Size** in the *Garments* panel that scales all of its pieces
together so the seams keep matching. They are plain multipliers over the
drafted or drawn shape (1 = as drafted), they update the 3D garment live, and
they are mirrored into the piece's object scale so the 2D view shows the size
the garment is built at. That also means `S` on a piece in the 2D view followed
by **Sync** does the same job by hand; the builder reads the object scale. The
cloth's rest lengths follow the scaled piece, so a longer sleeve is a longer
sleeve, not a stretched one. *Counterpart* copies the scale.

## Mesh and subdivision

Pattern pieces are built as a **quad grid clipped to the outline**, not a
triangulation. Two reasons: a quad cage subdivides into a clean surface, and its
edges run along the pattern's own axes, so the cloth stretches along the grain
the way woven fabric does. Panels come out 100% quads at roughly 85 degrees
minimum corner angle.

**Subdivision** has separate viewport and render levels. The cloth always solves
on the quad cage, so raising the level costs nothing at simulation time - only
the displayed surface gets denser:

| Level | Rendered faces (tank top) | Mean fold angle | Drape time |
|------:|--------------------------:|----------------:|-----------:|
| 0     | 2,290                     | 19.4 deg        | 8 s        |
| 1     | 8,892                     |  8.4 deg        | 8 s        |
| 2     | 35,032                    |  4.4 deg        | 15 s       |

Modifier order is enforced as Armature, Cloth, Subdivision, Solidify. Putting the
subdivision before the cloth makes the solver run on the subdivided mesh instead
of the cage, which cost 217 s instead of 8 for the same result.

## Several garments at once

Each garment is its own entry in the **Garments** panel, listed by layer with its
open-stitch count. Selecting one makes it active: the pattern pieces, the seam
list and every operator follow it.

`Layer` sets the wearing order. A garment collides with the body and with every
garment on a *lower* layer, so 0 is worn innermost. The collision is deliberately
one-directional - an outer layer sees the inner ones, never the reverse - because
two cloth objects colliding with each other make the depsgraph cyclic and Blender
silently drops the relationship.

**Sew** stitches, welds and settles the active garment. **Unsew** does the
opposite: it rebuilds the garment from its flat pattern pieces, drops the rig
binding and thickness, and puts the stitches back so you can edit the draft and
try again. **Sew All** / **Unsew All** work through every layer from the inside
out.

Seams belong to the garment whose pieces they join, not to the scene. Storing
them globally meant adding a second garment wiped the first one's stitching and
left it impossible to re-sew.

## Skin weights

`Finalize` transfers weights from the body by nearest-polygon interpolation and
then **smooths them across neighbouring vertices**. This is not cosmetic. At the
crotch the two thighs nearly touch, so neighbouring garment vertices land on
opposite legs: one follows the left thigh, the next follows the right. As the
legs separate those neighbours are dragged apart and the garment tears open.
Measured on the jumpsuit at a mid-stride frame, worst-case edge stretch went
from 7.8x to 2.1x once the influences were blended.

Note that `bpy.ops.object.vertex_group_smooth` does nothing when driven
headlessly, so the smoothing is implemented directly rather than through the
operator.

## Notes

- Collision is restricted to a `CD_Colliders` collection holding just the
  avatar. Letting every cloth object collide with every other creates
  depsgraph cycles.
- *Keep Off Body* lifts arranged panels clear of the mesh before simulating.
  Anything starting inside the body gets ejected explosively by the solver.
- A Flat Panel has no seams, so it falls. That is expected: it is a piece of
  cloth, not a garment.
- Measurements ignore arms, hands, fingers and the head, using the rig's own
  skin weights. Missing even one group matters: CC4 names finger bones
  `Index1`/`Mid1`, and with those unmasked an A-pose reads as a 164 cm waist.
- Waist and hip are taken as the narrowest and widest sections of the torso,
  not from the rig's `Waist`/`Pelvis` bones, which sit several cm low.
- Fabric defaults are Crisp/Tailored: bending 25, compression 120, Take In
  0.05, quality 12. That is roughly a third fewer folds than the soft default,
  at about twice the simulation time.
- Sleeves are the roughest preset. The cap sews correctly but tends to gather
  at the armhole on a character whose arms hang against the body. On the
  bundled avatar they come out clean.
