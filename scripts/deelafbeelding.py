#!/usr/bin/env python3
"""Deelafbeelding (Open Graph, 1200×630) per pagina voor LinkedIn, WhatsApp, Teams, X en Facebook.

Gebruikt door maak-seo.py: maak(titel, ondertitel, rubriek, uitvoerpad).
Huisstijl: navy #003057, goud #e5a138; lettertype Inter (systeem). Deterministisch: zelfde invoer → zelfde bestand.
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1200, 630
NAVY, NAVY2, GOUD, WIT, LICHT = (0, 48, 87), (10, 66, 112), (229, 161, 56), (255, 255, 255), (198, 214, 230)
FD = '/usr/share/fonts/opentype/inter/'


def font(naam, grootte):
    for p in (FD + naam, '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, grootte)
    return ImageFont.load_default()


def regels(d, tekst, f, breedte, max_regels):
    woorden, uit, cur = tekst.split(), [], ''
    for w in woorden:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= breedte:
            cur = t
        else:
            if cur:
                uit.append(cur)
            cur = w
    if cur:
        uit.append(cur)
    if len(uit) > max_regels:
        uit = uit[:max_regels]
        while d.textlength(uit[-1] + ' …', font=f) > breedte and ' ' in uit[-1]:
            uit[-1] = uit[-1].rsplit(' ', 1)[0]
        uit[-1] += ' …'
    return uit


def maak(titel, ondertitel, rubriek, pad):
    im = Image.new('RGB', (W, H), NAVY)
    d = ImageDraw.Draw(im)
    # decoratie rechts: oplopende staafjes + lijn (rekentool-motief), subtiel
    bx = 860
    for i, h in enumerate([90, 140, 120, 190, 240, 300]):
        x = bx + i * 52
        d.rounded_rectangle([x, 520 - h, x + 34, 520], 6, fill=NAVY2)
    d.line([(bx + 17 + i * 52, 520 - h - 18) for i, h in enumerate([90, 140, 120, 190, 240, 300])], fill=GOUD, width=5, joint='curve')
    # logo
    lp = os.path.join(ROOT, 'assets', 'logo.webp')
    if os.path.exists(lp):
        lg = Image.open(lp).convert('RGBA')
        lg.thumbnail((150, 86))
        im.paste(lg, (72, 56), lg)
    # rubriek-label
    y = 172
    if rubriek:
        fr = font('Inter-SemiBold.otf', 24)
        tw = d.textlength(rubriek.upper(), font=fr)
        d.rounded_rectangle([72, y, 72 + tw + 32, y + 42], 21, fill=GOUD)
        d.text((88, y + 8), rubriek.upper(), font=fr, fill=NAVY)
        y += 66
    # titel: grootste maat die in max. 3 regels past
    # titel: grootste maat in max. 2 regels; anders 3 regels in een kleinere maat
    keus = None
    for gr, mx in ((72, 2), (64, 2), (58, 2), (54, 3), (48, 3), (44, 3)):
        ft = font('InterDisplay-ExtraBold.otf', gr)
        rg = regels(d, titel, ft, 760, mx)
        keus = (gr, ft, rg)
        if not rg[-1].endswith('…'):
            break
    gr, ft, rg = keus
    for r in rg:
        d.text((72, y), r, font=ft, fill=WIT)
        y += int(gr * 1.14)
    # ondertitel
    if ondertitel:
        fo = font('Inter-Medium.otf', 28)
        y += 14
        for r in regels(d, ondertitel, fo, 760, 2 if len(rg) < 3 else 1):
            d.text((72, y), r, font=fo, fill=LICHT)
            y += 38
    # onderbalk
    d.rectangle([0, H - 78, W, H], fill=GOUD)
    fb = font('InterDisplay-Bold.otf', 30)
    d.text((72, H - 59), 'adviseurstools.nl', font=fb, fill=NAVY)
    fs = font('Inter-SemiBold.otf', 24)
    rechts = 'Gratis rekentools · normen 2026 en 2027'
    d.text((W - 72 - d.textlength(rechts, font=fs), H - 54), rechts, font=fs, fill=NAVY)
    os.makedirs(os.path.dirname(pad), exist_ok=True)
    im.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(pad, optimize=True)
