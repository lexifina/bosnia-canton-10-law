"""Canton 10 (Hercegbosanska županija): scan the Narodne novine Hercegbosanske županije issues -> <OUT>/<sha256>.json:
issue number, date, edition language and every act the Assembly (Skupština / Županijska skupština Hercegbosanske
županije) published as a law ('ZAKON'), with its lines in reading order. Private (never published). Used through
scripts/bosnia-tuzla-canton-law/live/canton_build.py (cc hbz), which sets CACHE/OUT.

Acts: from 2021 on the gazette separates acts by a '***' line and prints the act number only in the issue's table of
contents (PREGLED SADRŽAJA: '234. ODLUKA o ...'); earlier issues print the number in bold before the act, as the other
cantons do. An act is a law when a ZAKON heading follows its legal basis ('Temeljem' / 'Na temelju' / 'Na osnovu')
within 40 lines and the text before the heading names the Assembly of the canton. Its number: the bold number before
it, else the k-th 'NNN. ZAKON' entry of the contents for the k-th law of the issue (both in page order), else none
(the act is then left to parse.py's holds).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gzread as tkread  # noqa: E402

# The running header differs by period (2021 on: three lines, baselines 54-73; 1990s: a masthead-like line set in
# spaced capitals). Per page, the cut sits just below the last line, from the top of the page down to 110 pt, that is
# a header line: the gazette's name, 'Str. N - Broj N' / 'Broj N - Strana N', the issue date, or a page number.
# Nothing below the first other line is dropped.
_page_lines = tkread.page_lines
_HDR_TOKENS = re.compile(r'(?i)(\d{1,2}\.\s?[^\W\d_]+\s?(19|20)\d\d\.?(\s?god\w*\.?)?|\d{1,2}\.\s?\d{1,2}\.\s?(19|20)\d\d\.?'
                         r'|Str(\.|ana)\s*\d+|Broj\s*\d+|N\s?A\s?R\s?O\s?D\s?N\s?E\s*N\s?O\s?V\s?I\s?N\s?E'
                         r'|HERCEG-?\s?BOSANSKE|[ŽZ]UPANIJE|\d+|[-–,.\s])')


def is_header(t: str) -> bool:
    """A running-header line: only the gazette's name, the issue date, 'Str. N', 'Broj N' and page numbers, in any
    order and combination ('17. lipnja 2014. NARODNE NOVINE Str. 639 - Broj 8')."""
    s = t.strip()
    # it must name the gazette, a page/issue or a year: a lone '-' or '1.500,00' in a table is body text
    if not re.search(r'(?i)N\s?A\s?R\s?O\s?D\s?N\s?E|HERCEG|[ŽZ]UPANIJE|Str(\.|ana)\s*\d|Broj\s*\d|(19|20)\d\d', s):
        return False
    return not _HDR_TOKENS.sub('', s)


def _cut(page):
    import pymupdf
    rows = []
    for b in page.get_text('dict', flags=pymupdf.TEXT_PRESERVE_WHITESPACE)['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text'].strip()]
            if sp:
                rows.append((round(sp[0]['origin'][1], 1), ''.join(s['text'] for s in l['spans'])))
    cut = 30.0
    for y, t in sorted(rows):
        if y > 110:
            break
        if is_header(t):
            cut = y + 1
        else:
            break
    return cut


def _page_lines_cut(page):
    tkread.HEAD_Y = _cut(page)
    return _page_lines(page)


tkread.page_lines = _page_lines_cut

CACHE = HERE / '.cache'
OUT = HERE / '.tmp' / 'acts'
ACTNO = re.compile(r'^(\d{1,4})\.?$')
ZAKON = re.compile(r'^(Z ?A ?K ?O ?N|З ?А ?К ?О ?Н)$')
BASIS = re.compile(r'^(T?emeljem|Na temelju|Na osnovu|Na osnovi|На основу)')  # a drop cap can lose the T
ASSEMBLY = re.compile(r'(?i)(Skup[sš]tin\w*|Žup\w* skup[sš]tin\w*|Zup\w* skup[sš]tin\w*)\s+(Hercegbosansk|Herceg-bosansk|HB[ŽZ]|Županije? 10|Kantona? 10)'
                      r'|Županijsk\w* skup[sš]tin|Zupanijsk\w* skup[sš]tin')
MONTHS = {m: i + 1 for i, ms in enumerate([
    'januar siječanj siječnja', 'februar veljača veljače', 'mart ožujak ožujka', 'april travanj travnja', 'maj svibanj svibnja',
    'juni jun lipanj lipnja', 'juli jul srpanj srpnja', 'august kolovoz kolovoza', 'septembar rujan rujna',
    'oktobar listopad listopada', 'novembar studeni studenoga studenog', 'decembar prosinac prosinca']) for m in ms.split()}
DATE = re.compile(r'(\d{1,2})\.\s*(\d{1,2}\.|[^\W\d_]+)\s*((?:19|20)\d\d)\.?')


def _date(t):
    for d in DATE.finditer(t):
        mon = d.group(2).rstrip('.')
        mon = int(mon) if mon.isdigit() else next((v for k, v in MONTHS.items() if mon.lower()[:4] == k[:4]), None)
        if mon and 1 <= mon <= 12 and 1 <= int(d.group(1)) <= 31:
            return f'{int(d.group(3)):04d}-{mon:02d}-{int(d.group(1)):02d}'
    return None


def issue_meta(doc, url):
    """Issue number from the masthead ('BROJ 6') or the running header ('Str. 749 - Broj 6'); date from the masthead
    ('LIVNO, 21. SVIBNJA 2025.') or the running header's date line. The edition is Croatian (the gazette has one)."""
    head = doc[0].get_text()
    num = date = None
    m = re.search(r'(?i)LIVNO,?\s+(.{6,30}?(?:19|20)\d\d)', head)
    if m:
        date = _date(m.group(1))
    for pno in range(0, min(6, doc.page_count)):
        t = doc[pno].get_text()[:300]
        n = re.search(r'(?i)Str(?:\.|ana)\s*\d+\s*[-–]\s*Broj\s+(\d+)', t)
        if n and num is None:
            num = int(n.group(1))
        if date is None and n:
            date = _date(t[n.end():n.end() + 60])
        if num and date:
            break
    m = re.search(r'(?i)\bBROJ\s+(\d{1,3})\b', head)
    if num is None and m:  # the running header's number first; the masthead's only when there is none
        num = int(m.group(1))
    return num, date, 'hrvatskom'


def _pre(lines):
    """The text before the ZAKON heading, with words split at line ends joined ('Her-' + 'cegbosanske')."""
    return re.sub(r'-\s+(?=\w)', '', ' '.join(l['text'] for l in lines))


def toc_laws(lines):
    """'NNN. ZAKON ...' entries of the table of contents, in order (they come before the first act's body)."""
    out = []
    for i, l in enumerate(lines):
        m = re.match(r'^(\d{1,4})\.\s*(ZAKON|Z A K O N|Zakon)\b', l['text'])  # 1998: '77.Zakon o ...'
        if m:
            out.append(int(m.group(1)))
        elif ACTNO.match(l['text']) and i + 1 < len(lines) and re.match(r'^(ZAKON|Z A K O N)\b', lines[i + 1]['text']):
            out.append(int(ACTNO.match(l['text']).group(1)))  # '21.' and 'ZAKON o ...' on two lines (2003)
    return out


PROMULGATE = re.compile(r'(?i)progla[sš]\w*\s+(se\s+)?Zakon')


def _is_sep(l):
    return l['text'].replace(' ', '') == '***'


def _is_num(lines, i):
    return lines[i]['bold'] and lines[i]['size'] >= 9 and bool(ACTNO.match(lines[i]['text']))


def _section(l):
    """An issuer heading between acts ('SKUPŠTINA HERCEGBOSANSKE', 'ŽUPANIJE', 'DOM ZDRAVLJA LIVNO')."""
    t = l['text']
    return l['bold'] and t.upper() == t and not ZAKON.match(t) and not ACTNO.match(t) and len(t) < 60


def acts_of(lines):
    """Every Assembly law of the issue, found from its ZAKON heading. The act begins after the nearest boundary above
    the heading (a '***' line or a bold act number), issuer headings and running headers skipped; it ends at the next
    boundary. A law when the text between the start and the heading has a legal basis naming the Assembly, or (the
    1990s layout) the heading comes first and the act before it is the Župan's promulgation of a law the Assembly
    passed. Number: the bold act number at the start, else the k-th 'NNN. ZAKON' contents entry for the k-th law of
    the issue when the counts agree, else the promulgation's number, else the law is not returned."""
    n = len(lines)
    bnd = [i for i in range(n) if _is_sep(lines[i]) or _is_num(lines, i)]
    heads = [i for i in range(n) if ZAKON.match(lines[i]['text'])]  # bold from 2003 on; regular weight in 1998
    cands = []
    for z in heads:
        above = [b for b in bnd if b < z]
        if not above:
            continue  # the contents (before any act)
        b0 = above[-1]
        s = b0 + 1
        while s < z and (is_header(lines[s]['text']) or _section(lines[s])):
            s += 1
        below = [b for b in bnd if b > z]
        e = below[0] if below else n
        pre = lines[s:z]
        kind = None
        if pre and BASIS.match(pre[0]['text']) and ASSEMBLY.search(_pre(pre)) and len(pre) <= 40:
            kind = 'basis'
        elif not pre:
            prev = [b for b in bnd if b < b0]
            ptxt = _pre(lines[(prev[-1] + 1 if prev else 0):b0])
            if PROMULGATE.search(ptxt) and ASSEMBLY.search(ptxt):
                kind = 'promulgated'
        if kind is None:
            continue
        no = int(ACTNO.match(lines[b0]['text']).group(1)) if _is_num(lines, b0) else None
        if no is None:  # the 1990s: the law follows the Zupan's promulgation of it, which carries the act number
            prev = [b for b in bnd if b < b0]
            if prev and _is_num(lines, prev[-1]) and PROMULGATE.search(_pre(lines[prev[-1] + 1:b0])):
                no = int(ACTNO.match(lines[prev[-1]]['text']).group(1))
        cands.append({'no': no, 'page': lines[s]['page'], 'lines': lines[s:e]})
    if any(c['no'] is None for c in cands):
        toc = toc_laws(lines[:heads[0]])  # contents entries ('NNN. ZAKON o ...') stand before the first law's heading
        if len(toc) == len(cands):
            for c, t in zip(cands, toc):
                c['no'] = c['no'] if c['no'] is not None else t
    return [c for c in cands if c['no'] is not None]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    urls = [u for u in (CACHE / 'issues.txt').read_text(encoding='utf-8').split() if u]
    for u in urls:
        p = CACHE / 'by-url' / hashlib.sha256(u.encode()).hexdigest()
        if not p.exists():
            continue
        lines, doc = tkread.issue_lines(p)
        num, date, lang = issue_meta(doc, u)
        acts = acts_of(lines)
        print(num, date, lang, len(acts), u.split('/')[-1], flush=True)


if __name__ == '__main__':
    main()
