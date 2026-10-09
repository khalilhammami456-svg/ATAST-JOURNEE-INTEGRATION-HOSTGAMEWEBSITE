"""Transparent cost assessment (TND) for the 17 collection pieces.  System python.

usage: python cost_model.py   ->  production/cost-assessment.md + production/cost_model.json + production/bom.csv

Honesty rules of this file
* VERIFIED  = a published public tariff in Tunisia that was seen (through search summaries) in the research of the 2D phase
              (research/manufacturing-tunisia.md §2).  They are retail / entry-level advertised prices, not quotes.
* ESTIMATE  = our own assumption.  Every estimate is tagged [EST] and carries a low and a high value so the reader sees the spread.
* No supplier was contacted; no quote exists.  The model's job is to size the budget and show which lines drive it.
"""
import json, csv, math
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
import sys
sys.path.insert(0, str(HERE))
from collection import ITEMS

# ------------------------------------------------------------------ verified public tariffs (Tunisia) -- see research §2
VERIFIED = [
    ("Teewinek", "Unisex hoodie (blank, promo)", "45 DT (struck-through 55 DT; other hoodies 'often 50-55 DT'), excl. delivery", "https://www.teewinek.com/produit/sweat-a-capuche-unisexe/"),
    ("Teewinek", "Sweatshirt (blank)", "39 DT (was 45 DT)", "https://www.teewinek.com/categorie-produit/acheter/sweat-capuche-acheter/"),
    ("Teewinek", "HD DTF cotton T-shirt, printed", "from 25 DT", "https://www.teewinek.com/grossiste-tee-shirt-personnalise-impression-t-shirt-t-shirt-publicitaire-en-tunsie/"),
    ("Labasni", "Screen print per tee", "3-5 DT for large quantities on one page, 'from 7 DT' on another (inconsistent)", "https://www.labasni.com/prix-impression-tshirt-tunisie/"),
    ("Labasni", "Flocage / flex per tee", "5-12 DT (two pages disagree)", "https://www.labasni.com/prix-impression-tshirt-tunisie/"),
    ("Labasni", "Digital / DTF print per tee", "7-15 DT", "https://www.labasni.com/prix-impression-tshirt-tunisie/"),
    ("Labasni", "Embroidery per tee (small logo)", "12-25 DT", "https://www.labasni.com/prix-impression-tshirt-tunisie/"),
    ("Modcom", "Custom sweatshirt (blank + marking not clear)", "from 20.90 HT (currency ambiguous)", "https://modcom.tn/sweat-shirt-personnalise-tunisie/"),
    ("Modcom", "Custom hoodie", "from 23.90 HT", "https://modcom.tn/sweat-capuche-personnalise-tunisie/"),
    ("Modcom", "Custom cap", "6.90 HT", "https://modcom.tn/casquette-personnalisee-tunisie/"),
    ("Modcom", "Custom vest (gilet)", "from 16.90 HT", "https://modcom.tn/gilet-personnalise-tunisie/"),
    ("Modcom", "Custom padded jacket (doudoune)", "from 29.90 HT", "https://modcom.tn/doudoune-personnalisee-tunisie/"),
]

# ------------------------------------------------------------------ decoration rates (DT per piece, per placement): (low, high, status)
DECO = {
    "screen1": (3.0, 7.0, "VERIFIED range (Labasni, inconsistent pages)"),
    "screen_multi": (5.0, 11.0, "EST: Labasni range + 1-2 DT per extra colour"),
    "dtf": (7.0, 15.0, "VERIFIED range (Labasni)"),
    "emb_small": (12.0, 25.0, "VERIFIED range (Labasni, small chest logo)"),
    "emb_large": (22.0, 45.0, "EST: 1.8-1.9 x the verified small-logo range (stitch count scales)"),
    "patch": (1.5, 5.0, "EST: no Tunisian rate found (Strasstex lists patches, price not published)"),
    "woven_label": (0.5, 1.8, "EST: no Tunisian rate found; European makers quote ~500 pc MOQ"),
    "chenille": (9.0, 22.0, "EST: appliqué/chenille letter, no Tunisian rate found"),
    "jacquard": (0.0, 0.0, "included in the knitted/woven fabric price"),
}

# ------------------------------------------------------------------ blanks: made-to-spec garment without decoration (DT / piece)
# Anchors are the verified retail blanks above; our spec is heavier / more complex, hence the premium (assumption).
BLANK = {
    "T1": (11.0, 21.0, "EST; anchor: entry tee 'from 8 DT' printed (Labasni); 240 gsm organic combed = premium"),
    "T2": (12.0, 23.0, "EST; heavy 260 gsm boxy cut"),
    "T3": (11.0, 21.0, "EST; cotton/modal 220 gsm"),
    "H1": (62.0, 105.0, "EST; anchor: hoodie 45 DT retail promo / 23.90 HT entry, ours is 380 gsm + zip + rib + yoke seam"),
    "H2": (50.0, 88.0, "EST; anchor as H1, French terry + kangaroo pocket"),
    "H3": (68.0, 118.0, "EST; bonded technical fleece, taped seams (needs a specialist CMT)"),
    "J1": (150.0, 270.0, "EST; no Tunisian anchor (melton + faux-leather + rib + snaps + lining)"),
    "J2": (52.0, 95.0, "EST; anchor: padded jacket from 29.90 HT (Modcom), ours is nylon taffeta with snaps"),
    "V1": (70.0, 125.0, "EST; felt vest with quilted lining"),
    "V2": (46.0, 82.0, "EST; anchor: vest from 16.90 HT (Modcom), ours is quilted ripstop with fill and funnel collar"),
    "S1": (22.0, 48.0, "EST; jacquard woven (needs a jacquard loom / mill run: MOQ risk, see notes)"),
    "S2": (18.0, 40.0, "EST; jacquard knit border"),
    "A1": (8.0, 17.0, "EST; anchor: cap 6.90 HT (Modcom)"),
    "A2": (7.0, 15.0, "EST; rib-knit merino/acrylic"),
    "A3": (5.0, 12.0, "EST; 12 oz canvas tote"),
    "A4": (0.0, 0.0, "see decoration"),
    "A5": (0.0, 0.0, "see decoration"),
}

# ------------------------------------------------------------------ decorations per item: (technique key, quantity, description)
PLAN = {
    "T1": [("emb_small", 1, "left-chest DNA 4 cm (~3,800 stitches, EST)"), ("screen_multi", 1, "back DNA double helix 2 colours")],
    "T2": [("screen_multi", 1, "chest tiles B·Ac·Sc·I 4 colours"), ("screen1", 1, "back 2027 1 colour"), ("emb_small", 1, "sleeve Sc tile")],
    "T3": [("screen_multi", 2, "caffeine front + Punnett back, 2 colours each")],
    "H1": [("patch", 1, "woven crest 7 cm"), ("emb_small", 1, "sleeve script + 2027"), ("emb_large", 1, "back tiles B·Ac·Sc·I"), ("woven_label", 1, "hem label")],
    "H2": [("emb_small", 1, "chest wordmark"), ("screen_multi", 1, "back collage 3 colours"), ("screen1", 2, "sleeve 2027 / HΛNNIBΛL"), ("woven_label", 1, "hem label")],
    "H3": [("patch", 1, "mini crest"), ("dtf", 1, "back cosmic print 40 cm (full colour gradients)"), ("screen_multi", 1, "sleeve orbit bands"), ("woven_label", 1, "violet hem label")],
    "J1": [("chenille", 1, "chest H"), ("patch", 2, "sleeve patches"), ("emb_large", 1, "back SCIENCES arch + crest"), ("woven_label", 1, "label")],
    "J2": [("emb_small", 1, "wordmark"), ("dtf", 1, "back molecule + formula"), ("woven_label", 1, "label")],
    "V1": [("patch", 1, "chest crest"), ("emb_large", 1, "back arch SCIENCES + crest")],
    "V2": [("screen1", 1, "back orbit tone-on-tone"), ("woven_label", 1, "label")],
    "S1": [("jacquard", 1, "all-over orbit jacquard + contrast ends")],
    "S2": [("jacquard", 1, "typographic border jacquard"), ("emb_small", 1, "end monogram")],
    "A1": [("emb_small", 1, "front monogram"), ("emb_small", 1, "back 2027")],
    "A2": [("woven_label", 1, "woven tab")],
    "A3": [("screen_multi", 1, "caffeine centre 2 colours"), ("screen1", 1, "back crest")],
    "A4": [("patch", 1, "80 mm merrow-border patch")],
    "A5": [("woven_label", 1, "60 x 12 mm damask label")],
}
# trims (zip, rib, cords, snaps, lining, hang-tag, polybag) DT / piece
TRIMS = {
    "T1": (0.8, 1.6), "T2": (0.8, 1.6), "T3": (0.8, 1.6),
    "H1": (9.0, 16.0), "H2": (4.0, 8.5), "H3": (9.0, 17.0),
    "J1": (16.0, 30.0), "J2": (6.0, 12.0), "V1": (10.0, 19.0), "V2": (7.0, 14.0),
    "S1": (1.0, 2.0), "S2": (1.0, 2.0), "A1": (1.5, 3.5), "A2": (0.8, 1.6), "A3": (0.8, 1.8), "A4": (0.3, 0.8), "A5": (0.2, 0.5),
}
# one-off set-up per item (DT): digitising + screens + pattern/grading + 2 prototypes
SETUP = {
    "T1": (120, 420), "T2": (150, 520), "T3": (130, 460),
    "H1": (380, 1150), "H2": (320, 980), "H3": (380, 1200),
    "J1": (700, 2100), "J2": (300, 900), "V1": (420, 1300), "V2": (260, 800),
    "S1": (350, 1600), "S2": (280, 1200), "A1": (180, 520), "A2": (90, 300), "A3": (80, 260), "A4": (100, 360), "A5": (60, 220),
}
VOLUME = {50: 1.00, 100: 0.93, 200: 0.87}           # EST blank-price discount by run size
WASTE = 0.05                                       # misprints / size swaps, EST


def unit(it, n):
    b0, b1, _ = BLANK[it]
    d0 = d1 = 0.0
    for key, q, _ in PLAN[it]:
        lo, hi, _ = DECO[key]
        d0 += lo * q; d1 += hi * q
    t0, t1 = TRIMS[it]
    s0, s1 = SETUP[it]
    f = VOLUME[n]
    lo = (b0 * f + d0 + t0) * (1 + WASTE) + s0 / n
    hi = (b1 * f + d1 + t1) * (1 + WASTE) + s1 / n
    return lo, hi


def fabric_area(it):
    mp = ROOT / "production" / "measures.json"
    if mp.exists():
        m = json.load(open(mp)).get(it)
        if m:
            a = m.get("surface_m2", 0) + m.get("hood_surface_m2", 0)
            return a
    return None


def main():
    rows = []
    out = {}
    for it in ITEMS:
        r = {}
        for n in (50, 100, 200):
            r[n] = unit(it, n)
        out[it] = dict(unit_dt={str(n): [round(v[0], 1), round(v[1], 1)] for n, v in r.items()},
                       fabric_area_m2=fabric_area(it), blank=BLANK[it][:2], deco=[(k, q, d) for k, q, d in PLAN[it]])
        rows.append((it, r))
    (ROOT / "production").mkdir(exist_ok=True)
    json.dump(out, open(ROOT / "production" / "cost_model.json", "w"), indent=1, ensure_ascii=False)
    L = []
    A = L.append
    A("# Cost assessment (TND) — Bac Sciences 2027 3D collection")
    A("")
    A("> **Read this first.** No supplier was contacted and no quote exists. Prices below are an *order-of-magnitude budget model*, not offers. "
      "Lines are tagged **VERIFIED** (a public Tunisian tariff seen in the 2D-phase research, `research/manufacturing-tunisia.md` §2 — retail/entry prices, "
      "1 to 3 years old, some pages contradict each other) or **EST** (our own assumption, always given as a low–high range). "
      "The research tool could not open pages directly, so even the VERIFIED lines come from search-result summaries and must be re-checked on the live page.")
    A("")
    A("## 1. Verified public tariffs used as anchors")
    A("")
    A("| Shop | Item / service | Public figure | Source |")
    A("|---|---|---|---|")
    for s, i, f, u in VERIFIED:
        A(f"| {s} | {i} | {f} | {u} |")
    A("")
    A("Reading: these are retail or entry-level prices (light blanks, simple marking). Our specifications (380 gsm fleece, zip, embroidery, melton/PU, bonded fleece) "
      "are heavier and more complex, therefore the *blank* lines below are **estimates** with a premium over those anchors.")
    A("")
    A("## 2. Decoration rates used (DT per piece and placement)")
    A("")
    A("| Technique | Low | High | Status |")
    A("|---|---:|---:|---|")
    for k, (lo, hi, st) in DECO.items():
        A(f"| {k} | {lo:g} | {hi:g} | {st} |")
    A("")
    A("## 3. Model")
    A("")
    A("`unit(N) = [ blank × volume(N) + Σ decoration + trims ] × (1 + 5 % waste) + set-up / N`  — set-up = digitising + screens + pattern/grading + 2 prototypes (EST). "
      "`volume(50/100/200) = 1.00 / 0.93 / 0.87` (EST). All values in TND, excl. VAT unless a supplier says otherwise (the two Modcom anchors are 'HT').")
    A("")
    A("## 4. Result: unit cost range per item (TND) at three run sizes")
    A("")
    A("| ID | Item | Blank (EST) | Decoration (see plan) | N = 50 | N = 100 | N = 200 | Fabric area (3D model) |")
    A("|---|---|---|---|---|---|---|---|")
    for it, r in rows:
        meta = ITEMS[it]
        deco = "; ".join(f"{d}" for _, _, d in PLAN[it])
        b = BLANK[it]
        fa = fabric_area(it)
        fas = f"{fa:.2f} m² (shell, excl. waste)" if fa else "—"
        A(f"| {it} | {meta['title']} | {b[0]:g}–{b[1]:g} | {deco} | {r[50][0]:.0f}–{r[50][1]:.0f} | {r[100][0]:.0f}–{r[100][1]:.0f} | {r[200][0]:.0f}–{r[200][1]:.0f} | {fas} |")
    A("")
    A("## 5. Example bundles (per student, N = 100 per item)")
    bundles = [("Essential: T2 + A1 cap", ["T2", "A1"]), ("Class pack: H1 + T1 + A1 + A3", ["H1", "T1", "A1", "A3"]),
               ("Winter: H3 + S1 + A2", ["H3", "S1", "A2"]), ("Varsity: J1 + T3", ["J1", "T3"])]
    A("")
    A("| Bundle | Low (DT) | High (DT) |")
    A("|---|---:|---:|")
    for nm, ids in bundles:
        lo = sum(unit(i, 100)[0] for i in ids); hi = sum(unit(i, 100)[1] for i in ids)
        A(f"| {nm} | {lo:.0f} | {hi:.0f} |")
    A("")
    A("## 6. What drives the price, and what to ask first")
    A("")
    A("1. **J1 varsity** — melton + faux-leather + chenille is the single most expensive line and the one for which *no* Tunisian supplier was found. Ask IB PRO; consider the V1 vest or a screen-printed felt version if the quote is out of range.")
    A("2. **H1 / H3 hoodies** — fleece weight, zip, taped seams. H3's bonded fleece needs a specialist CMT; H2 (French terry) is the cheapest of the three.")
    A("3. **Embroidery** — the only decoration with verified Tunisian rates (12–25 DT small). Large back embroidery (H1 tiles, J1/V1 arch) is estimated at ~1.8× and should be requested per stitch count after digitising.")
    A("4. **S1 jacquard scarf** — fabric-mill minimums are unknown (ITS, Dym-Tex, Skytex are leads only). A printed or knitted alternative may be the only way to run < 100 pieces.")
    A("5. **Set-up (one-off)** — dominates small runs: at N = 50 it adds 3–30 DT per piece. Reuse of digitised files and screens across colourways is free; ask for it.")
    A("")
    A("## 7. What is **not** in these numbers")
    A("")
    A("- Fabric purchase by the metre (no Tunisian fabric price was found; the model prices finished garments instead).")
    A("- Delivery to Tébourba, VAT (19 % may apply on top of 'HT' prices), customs, a contingency of 10–15 %.")
    A("- Any permission or fee related to the school's name or logo (see research §4.1).")
    A("- Size-run fitting samples beyond the two prototypes already counted in set-up.")
    A("")
    A("## 8. Next step")
    A("")
    A("Send the RFQ questionnaire in `research/manufacturing-tunisia.md` §6 together with the tech packs in `tech-packs/` to: IB PRO, Labasni, Teewinek, Modcom, Strasstex; ask JC2S whether a pooled small order is possible. "
      "Replace every **EST** value by the quoted figure and re-run `pipeline/cost_model.py`.")
    (ROOT / "production" / "cost-assessment.md").write_text("\n".join(L), encoding="utf-8")
    # BOM csv
    with open(ROOT / "production" / "bom.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "fabric_spec", "decoration_plan", "trims_dt_low", "trims_dt_high", "blank_dt_low", "blank_dt_high", "setup_dt_low", "setup_dt_high"])
        for it in ITEMS:
            w.writerow([it, ITEMS[it]["title"], ITEMS[it]["fabric"], " | ".join(d for _, _, d in PLAN[it]),
                        TRIMS[it][0], TRIMS[it][1], BLANK[it][0], BLANK[it][1], SETUP[it][0], SETUP[it][1]])
    print("written cost-assessment.md, cost_model.json, bom.csv")


if __name__ == "__main__":
    main()
