# Cost assessment (TND) — Bac Sciences 2027 3D collection

> **Read this first.** No supplier was contacted and no quote exists. Prices below are an *order-of-magnitude budget model*, not offers. Lines are tagged **VERIFIED** (a public Tunisian tariff seen in the 2D-phase research, `research/manufacturing-tunisia.md` §2 — retail/entry prices, 1 to 3 years old, some pages contradict each other) or **EST** (our own assumption, always given as a low–high range). The research tool could not open pages directly, so even the VERIFIED lines come from search-result summaries and must be re-checked on the live page.

## 1. Verified public tariffs used as anchors

| Shop | Item / service | Public figure | Source |
|---|---|---|---|
| Teewinek | Unisex hoodie (blank, promo) | 45 DT (struck-through 55 DT; other hoodies 'often 50-55 DT'), excl. delivery | https://www.teewinek.com/produit/sweat-a-capuche-unisexe/ |
| Teewinek | Sweatshirt (blank) | 39 DT (was 45 DT) | https://www.teewinek.com/categorie-produit/acheter/sweat-capuche-acheter/ |
| Teewinek | HD DTF cotton T-shirt, printed | from 25 DT | https://www.teewinek.com/grossiste-tee-shirt-personnalise-impression-t-shirt-t-shirt-publicitaire-en-tunsie/ |
| Labasni | Screen print per tee | 3-5 DT for large quantities on one page, 'from 7 DT' on another (inconsistent) | https://www.labasni.com/prix-impression-tshirt-tunisie/ |
| Labasni | Flocage / flex per tee | 5-12 DT (two pages disagree) | https://www.labasni.com/prix-impression-tshirt-tunisie/ |
| Labasni | Digital / DTF print per tee | 7-15 DT | https://www.labasni.com/prix-impression-tshirt-tunisie/ |
| Labasni | Embroidery per tee (small logo) | 12-25 DT | https://www.labasni.com/prix-impression-tshirt-tunisie/ |
| Modcom | Custom sweatshirt (blank + marking not clear) | from 20.90 HT (currency ambiguous) | https://modcom.tn/sweat-shirt-personnalise-tunisie/ |
| Modcom | Custom hoodie | from 23.90 HT | https://modcom.tn/sweat-capuche-personnalise-tunisie/ |
| Modcom | Custom cap | 6.90 HT | https://modcom.tn/casquette-personnalisee-tunisie/ |
| Modcom | Custom vest (gilet) | from 16.90 HT | https://modcom.tn/gilet-personnalise-tunisie/ |
| Modcom | Custom padded jacket (doudoune) | from 29.90 HT | https://modcom.tn/doudoune-personnalisee-tunisie/ |

Reading: these are retail or entry-level prices (light blanks, simple marking). Our specifications (380 gsm fleece, zip, embroidery, melton/PU, bonded fleece) are heavier and more complex, therefore the *blank* lines below are **estimates** with a premium over those anchors.

## 2. Decoration rates used (DT per piece and placement)

| Technique | Low | High | Status |
|---|---:|---:|---|
| screen1 | 3 | 7 | VERIFIED range (Labasni, inconsistent pages) |
| screen_multi | 5 | 11 | EST: Labasni range + 1-2 DT per extra colour |
| dtf | 7 | 15 | VERIFIED range (Labasni) |
| emb_small | 12 | 25 | VERIFIED range (Labasni, small chest logo) |
| emb_large | 22 | 45 | EST: 1.8-1.9 x the verified small-logo range (stitch count scales) |
| patch | 1.5 | 5 | EST: no Tunisian rate found (Strasstex lists patches, price not published) |
| woven_label | 0.5 | 1.8 | EST: no Tunisian rate found; European makers quote ~500 pc MOQ |
| chenille | 9 | 22 | EST: appliqué/chenille letter, no Tunisian rate found |
| jacquard | 0 | 0 | included in the knitted/woven fabric price |

## 3. Model

`unit(N) = [ blank × volume(N) + Σ decoration + trims ] × (1 + 5 % waste) + set-up / N`  — set-up = digitising + screens + pattern/grading + 2 prototypes (EST). `volume(50/100/200) = 1.00 / 0.93 / 0.87` (EST). All values in TND, excl. VAT unless a supplier says otherwise (the two Modcom anchors are 'HT').

## 4. Result: unit cost range per item (TND) at three run sizes

| ID | Item | Blank (EST) | Decoration (see plan) | N = 50 | N = 100 | N = 200 | Fabric area (3D model) |
|---|---|---|---|---|---|---|---|
| T1 | T-shirt minimal premium | 11–21 | left-chest DNA 4 cm (~3,800 stitches, EST); back DNA double helix 2 colours | 33–70 | 31–64 | 29–61 | — |
| T2 | T-shirt graphique audacieux | 12–23 | chest tiles B·Ac·Sc·I 4 colours; back 2027 1 colour; sleeve Sc tile | 37–81 | 35–74 | 34–70 | — |
| T3 | T-shirt illustration scientifique | 11–21 | caffeine front + Punnett back, 2 colours each | 25–56 | 23–50 | 22–46 | — |
| H1 | Hoodie zippé oversize | 62–105 | woven crest 7 cm; sleeve script + 2027; back tiles B·Ac·Sc·I; hem label | 120–231 | 112–211 | 106–199 | — |
| H2 | Hoodie pull collégial | 50–88 | chest wordmark; back collage 3 colours; sleeve 2027 / HΛNNIBΛL; hem label | 88–175 | 81–159 | 76–149 | — |
| H3 | Hoodie technique | 68–118 | mini crest; back cosmic print 40 cm (full colour gradients); sleeve orbit bands; violet hem label | 103–200 | 94–180 | 88–166 | — |
| J1 | Varsity jacket | 150–270 | chest H; sleeve patches; back SCIENCES arch + crest; label | 225–440 | 206–399 | 194–371 | — |
| J2 | Veste coach légère | 52–95 | wordmark; back molecule + formula; label | 87–174 | 81–158 | 76–148 | — |
| V1 | Gilet varsity | 70–125 | chest crest; back arch SCIENCES + crest | 117–230 | 108–208 | 101–193 | — |
| V2 | Gilet de superposition | 46–82 | back orbit tone-on-tone; label | 65–126 | 59–112 | 54–103 | — |
| S1 | Écharpe motif orbites | 22–48 | all-over orbit jacquard + contrast ends | 31–84 | 26–65 | 23–54 | — |
| S2 | Écharpe minimale bordée | 18–40 | typographic border jacquard; end monogram | 38–94 | 34–79 | 31–71 | — |
| A1 | Casquette 6 panneaux | 8–17 | front monogram; back 2027 | 39–84 | 36–78 | 35–74 | — |
| A2 | Bonnet côtelé | 7–15 | woven tab | 11–25 | 9–21 | 8–19 | — |
| A3 | Tote bag | 5–12 | caffeine centre 2 colours; back crest | 16–39 | 15–35 | 14–33 | — |
| A4 | Écusson brodé / tissé | 0–0 | 80 mm merrow-border patch | 4–13 | 3–10 | 2–8 | — |
| A5 | Étiquette tissée | 0–0 | 60 x 12 mm damask label | 2–7 | 1–5 | 1–4 | — |

## 5. Example bundles (per student, N = 100 per item)

| Bundle | Low (DT) | High (DT) |
|---|---:|---:|
| Essential: T2 + A1 cap | 71 | 152 |
| Class pack: H1 + T1 + A1 + A3 | 194 | 389 |
| Winter: H3 + S1 + A2 | 129 | 266 |
| Varsity: J1 + T3 | 230 | 449 |

## 6. What drives the price, and what to ask first

1. **J1 varsity** — melton + faux-leather + chenille is the single most expensive line and the one for which *no* Tunisian supplier was found. Ask IB PRO; consider the V1 vest or a screen-printed felt version if the quote is out of range.
2. **H1 / H3 hoodies** — fleece weight, zip, taped seams. H3's bonded fleece needs a specialist CMT; H2 (French terry) is the cheapest of the three.
3. **Embroidery** — the only decoration with verified Tunisian rates (12–25 DT small). Large back embroidery (H1 tiles, J1/V1 arch) is estimated at ~1.8× and should be requested per stitch count after digitising.
4. **S1 jacquard scarf** — fabric-mill minimums are unknown (ITS, Dym-Tex, Skytex are leads only). A printed or knitted alternative may be the only way to run < 100 pieces.
5. **Set-up (one-off)** — dominates small runs: at N = 50 it adds 3–30 DT per piece. Reuse of digitised files and screens across colourways is free; ask for it.

## 7. What is **not** in these numbers

- Fabric purchase by the metre (no Tunisian fabric price was found; the model prices finished garments instead).
- Delivery to Tébourba, VAT (19 % may apply on top of 'HT' prices), customs, a contingency of 10–15 %.
- Any permission or fee related to the school's name or logo (see research §4.1).
- Size-run fitting samples beyond the two prototypes already counted in set-up.

## 8. Next step

Send the RFQ questionnaire in `research/manufacturing-tunisia.md` §6 together with the tech packs in `tech-packs/` to: IB PRO, Labasni, Teewinek, Modcom, Strasstex; ask JC2S whether a pooled small order is possible. Replace every **EST** value by the quoted figure and re-run `pipeline/cost_model.py`.