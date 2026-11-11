"""FBiH canton gazette (two-column PDFs) -> lines in reading order. Private.

pymupdf spans; each line is placed by its baseline (span origin), not its bbox top (Cambria's bbox runs high).
Fragments of one justified line on the same baseline in the same column are joined. Running headers (above the
first text baseline, y < 55) are dropped. A line crossing the middle of the page is full width: it closes the
two-column section above it.
"""
import re
import unicodedata

import pymupdf

HEAD_Y = 45  # running headers sit at baseline 34.6; the first text line at 51.6


def clean(s):
    s = unicodedata.normalize('NFC', s.replace('\xa0', ' ').replace('­', '').replace('\t', ' '))
    return re.sub(r' {2,}', ' ', s).strip()


def page_lines(page):
    mid = page.rect.width / 2
    frags = []
    for b in page.get_text('dict', flags=pymupdf.TEXT_PRESERVE_WHITESPACE)['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text'].strip()]
            if not sp:
                continue
            y = round(sp[0]['origin'][1], 1)
            if y < HEAD_Y:
                continue  # running header
            x0, x1 = l['bbox'][0], l['bbox'][2]
            text = ''.join(s['text'] for s in l['spans'])
            bold = all('Bold' in s['font'] or s['flags'] & 16 for s in sp)
            size = max(s['size'] for s in sp)
            col = -1 if (x0 < mid - 20 and x1 > mid + 20) else (0 if x0 < mid else 1)
            frags.append([col, y, x0, x1, text, bold, size])
    # join fragments on one baseline in one column (left to right); a gap wider than 25 pt keeps them apart
    # (the two halves of a signature block share baselines)
    frags.sort(key=lambda f: (f[0], f[1]))
    clusters = []
    for f in frags:
        if clusters and clusters[-1][0][0] == f[0] and abs(clusters[-1][0][1] - f[1]) < 1.5:
            clusters[-1].append(f)
        else:
            clusters.append([f])
    lines = []
    for c in clusters:
        c.sort(key=lambda f: f[2])
        cur = list(c[0])
        for f in c[1:]:
            gap = f[2] - cur[3]
            if gap > 25 or (max(cur[6], f[6]) < 8.8 and gap > 3):
                lines.append(cur)
                cur = list(f)
                continue
            cur[4] = cur[4].rstrip() + ' ' + f[4].lstrip() if gap > 1 else cur[4] + f[4]
            cur[3] = max(cur[3], f[3]); cur[5] = cur[5] and f[5]
        lines.append(cur)
    # reading order: sections cut by full-width lines; in a section, left column then right
    fulls = sorted(l[1] for l in lines if l[0] == -1)
    def section(y):
        return sum(1 for fy in fulls if fy < y)
    def key(l):
        if l[0] == -1:
            return (section(l[1]) - 0.5, 0, l[1])
        return (section(l[1]), l[0], l[1])
    lines.sort(key=key)
    return [{'col': l[0], 'y': l[1], 'x0': l[2], 'x1': l[3], 'text': clean(l[4]), 'bold': l[5], 'size': l[6]}
            for l in lines if clean(l[4])]


def issue_lines(path):
    d = pymupdf.open(path)
    out = []
    for pno, page in enumerate(d):
        for l in page_lines(page):
            l['page'] = pno
            out.append(l)
    return out, d
