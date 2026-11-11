"""Canton 10 (Hercegbosanska županija): laws as published in the Narodne novine Hercegbosanske županije (copied from
the Zenica-Doboj reader, gitlaw-bosnia-deep 2026-11-11; used through canton_build.py --cc hbz).
Reads only .tmp/acts/ (scan.py) and .cache/. Private (never published).

    python -X utf8 parse.py list                 # every candidate law, with the reason it is in or out
    python -X utf8 parse.py <n> <from> <to>      # part n: the unamended laws [from:to], oldest first

A law is taken as enacted, dated the day it took effect (the issue date plus the days its final article names), and
credited to itself, only when nothing later in the scanned issues touches it: no later law cites its gazette number
next to a word of its subject (amendment, repeal or reference alike), it is not itself an amending or budget law,
and it is not a consolidated text.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'world-law'))
import ba_lib  # noqa: E402
sys.path.insert(0, str(HERE))
import dehyph  # noqa: E402  (line-end hyphens: joined or kept by the dictionary rule)

TMP = HERE / '.tmp' / 'acts'
LANGS = {'hrvatskom': 'Croatian', 'bosanskom': 'Bosnian', 'српском': 'Serbian', 'srpskom': 'Serbian'}
# left out after verify.py: the two PDF readers order the law's tables differently
LEFT_OUT = {}
RETRIEVED = '2026-11-11'
FROM = '1996-01-01'  # every issue on the Government's page was read
GAZETTE = 'https://www.vladahbz.com/narodne-novine/'
LICENCE = 'Official text, not protected: Zakon o autorskom i srodnim pravima BiH (Sl. glasnik BiH 63/10), čl. 8(1)(b)'
COUNTRY = {
    'code': 'BA-10', 'name': 'Canton 10', 'slug': 'bosnia-canton-10', 'lang': 'hr',
    'tz': 'Europe/Sarajevo', 'future_branch': 'buducnost',
    'publisher': {'name': 'Vlada Hercegbosanske županije (vladahbz.com)', 'email': 'zakoni@vladahbz.com.invalid'},
    'default_in_force_rule': {
        'text': 'A law takes effect on the day its own final article names, counted from its publication in the Narodne novine Hercegbosanske županije.',
        'source': GAZETTE},
    'licence_note': 'Text: Vlada Hercegbosanske županije, Narodne novine Hercegbosanske županije, https://www.vladahbz.com/narodne-novine/. Official texts are not protected by copyright in Bosnia and Herzegovina (Zakon o autorskom i srodnim pravima, Službeni glasnik BiH 63/10, član 8(1)(b)).',
}
ART = re.compile(r'^(Član|Članak|Члан|Чланак)\s+(\d+)\s*\.?\s*([a-zа-ш]?)\s*\.?$')
ZAKON = re.compile(r'^(Z ?A ?K ?O ?N|З ?А ?К ?О ?Н)$')
CHAPTER = re.compile(r'^(POGLAVLJE|ПОГЛАВЉЕ|GLAVA|ГЛАВА|DIO|ДИО|DIJEL|ODJELJAK|ОДЈЕЉАК|[IVX]+\.?\s|[IVX]+\.?$)')
REPEAL = re.compile(r'prestaj\w* (da )?važ|prestaj\w* (da )?vaz|van snage|stavlja\w* se van|ukida\w* se')
SIGN = re.compile(r'^(BOSNA I HERCEGOVINA|Bosna i Hercegovina|БОСНА И ХЕРЦЕГОВИНА|Broj:|Број:|Predsjed|PREDSJED|Предсједни)')
ORD = {'prvog': 1, 'drugog': 2, 'trećeg': 3, 'petog': 5, 'osmog': 8, 'desetog': 10, 'petnaestog': 15,
       'tridesetog': 30, 'narednog': 1, 'sljedećeg': 1, 'slijedećeg': 1, 'idućeg': 1,
       # Croatian forms (Narodne novine HBŽ)
       'prvoga': 1, 'drugoga': 2, 'trećega': 3, 'petoga': 5, 'osmoga': 8, 'desetoga': 10, 'petnaestoga': 15,
       'tridesetoga': 30, 'idućega': 1, 'sljedećega': 1, 'slijedećega': 1, 'narednoga': 1}
CYR = dict(zip('абвгдђежзијклљмнњопрстћуфхцчџшАБВГДЂЕЖЗИЈКЛЉМНЊОПРСТЋУФХЦЧЏШ',
               ['a', 'b', 'v', 'g', 'd', 'đ', 'e', 'ž', 'z', 'i', 'j', 'k', 'l', 'lj', 'm', 'n', 'nj', 'o', 'p', 'r', 's',
                't', 'ć', 'u', 'f', 'h', 'c', 'č', 'dž', 'š'] * 2))
PROPER = ['Hercegbosanske županije', 'Hercegbosanskoj županiji', 'Hercegbosanska županija', 'Livno', 'Livnu', 'Tomislavgrad', 'Federacije Bosne i Hercegovine',
          'Bosne i Hercegovine', 'Тузланског кантона', 'Тузланском кантону', 'Тузли', 'Федерације Босне и Херцеговине',
          'Босне и Херцеговине']


def lat(s):
    return ''.join(CYR.get(c, c) for c in s)


def cite_re(issue, year):
    return re.compile(rf'(?<![\d/]){issue}/{year % 100:02d}(?!\d)')


def load():
    issues = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(TMP.glob('*.json'))]
    bad = [d['url'] for d in issues if d['date'] is None and d['acts']]
    if bad:
        raise SystemExit(f'undated issues with laws: {bad}')
    issues = [d for d in issues if d['date'] is not None]
    issues.sort(key=lambda d: (d['date'], d['issue']))
    laws = []
    for d in issues:
        for a in d['acts']:
            laws.append({'issue': d['issue'], 'date': d['date'], 'lang': d['lang'], 'url': d['url'],
                         'sha256': d['sha256'], 'no': a['no'], 'lines': a['lines'],
                         'text': lat(' '.join(l['text'] for l in a['lines'])),
                         'head': ' '.join(l['text'] for l in a['lines'][:40] if l['bold'])[:400]})
    return issues, laws


def split_units(lines):
    """-> (units: key -> list of paragraphs, labels, title, in_force_days); ValueError when the act is not simple."""
    z = next((i for i, l in enumerate(lines) if l['bold'] and ZAKON.match(l['text'])), None)
    if z is None:
        raise ValueError('no title')
    left = {}
    for l in lines:
        if not l['bold'] and l['size'] >= 8.8:
            k = (l['page'], l['col'])
            left[k] = min(left.get(k, 999), l['x0'])

    def indent(l):
        return l['x0'] - left.get((l['page'], l['col']), l['x0'])

    arts = [i for i, l in enumerate(lines) if l['bold'] and ART.match(l['text'])]
    if len(arts) < 2:
        raise ValueError('fewer than two articles')
    consolidated = bool(re.search(r'utvrdi\w* (je )?prečišćen', lat(' '.join(l['text'] for l in lines[:z])).lower())
                        or 'prečišćen' in lat(' '.join(l['text'] for l in lines[z:z + 6] if l['bold'])).lower())
    s = next((i for i in range(arts[-1], len(lines)) if SIGN.match(lines[i]['text'])), None)
    if s is None and not consolidated:
        raise ValueError('no signature block')
    if s is None:  # a consolidated text ends with its last article; drop the next act's issuer heading
        s = len(lines)
        while s > arts[-1] + 1 and lines[s - 1]['bold'] and lines[s - 1]['size'] >= 11:
            s -= 1
    body, sig = lines[:s], [l for l in lines[s:] if not re.fullmatch(r'[.…_\s]+', l['text'])]
    pre_sig = []
    units, labels = {}, {'uvod': 'Uvod', 'naslov': 'Naslov'}
    key, cur, pending, para = 'uvod', [], [], None
    title, after_art = [], False

    def flush():
        nonlocal para
        if para is not None:
            (pending if para[0] == 'pend' else cur).append(para[1])
        para = None

    for i, l in enumerate(body):
        t = l['text']
        if i < z and l['size'] < 8.8:
            continue
        if i == z:
            flush()
            if pre_sig:
                x0 = min(p['x0'] for p in pre_sig)
                cur += [p['text'] for p in sorted(pre_sig, key=lambda p: (p['x0'] >= x0 + 115, p['page'], p['y']))]
            flush()
            units[key] = cur
            key, cur = 'naslov', [t]
            continue
        m = ART.match(t) if l['bold'] else None
        if key == 'naslov' and l['bold'] and not m and not CHAPTER.match(t) and not pending and para is None:
            title[:] = [dehyph.join(title[0], t)] if title else [t]  # the law's name under 'Z A K O N', on one line
            if len(cur) == 1:
                cur.append(t)
            else:
                cur[-1] = dehyph.join(cur[-1], t)
            continue
        if m:
            flush()
            units[key] = cur
            n, suf = int(m.group(2)), m.group(3) or ''
            key = ba_lib.art_key(n, suf)
            if key in units:
                raise ValueError(f'duplicate {key}')
            labels[key] = t
            cur, pending, after_art = pending + [t], [], True
            continue
        if l['bold']:
            if after_art:  # the article's own heading, under its number
                if para and para[0] == 'head' and not para[1].endswith(')') and not t.startswith('('):
                    para = ('head', dehyph.join(para[1], t))
                else:
                    flush()
                    para = ('head', t)
                continue
            # a heading between articles (chapter, part): it goes with the next article
            if para and para[0] == 'pend' and not CHAPTER.match(t):
                para = ('pend', dehyph.join(para[1], t))
            else:
                flush()
                para = ('pend', t)
            continue
        after_art = False
        if (para is None or para[0] != 'body' or indent(l) >= 8 or ba_lib.LIST_MARK.match(t)
                or re.match(r'^(Broj|Број|Livno|Tomislavgrad|Kupres|Drvar|Glamoč|Datum),?\s', t)):
            flush()
            para = ('body', t)
        else:
            p = para[1]
            para = ('body', dehyph.join(p, t))
    flush()
    if pending:
        raise ValueError('heading after the last article')
    units[key] = cur
    if not title:
        raise ValueError('no law name')
    # signature: left half first, then right half (each top to bottom)
    if sig:
        x0 = min(l['x0'] for l in sig)
        sig = sorted(sig, key=lambda l: (l['x0'] >= x0 + 115, l['page'], l['y']))
        units['potpis'] = [l['text'] for l in sig]
        labels['potpis'] = 'Potpis'
    if consolidated:
        return units, labels, re.sub(r'\s*\((prečišćeni tekst|пречишћени текст)\)\s*$', '', ' '.join(title), flags=re.I), 'consolidated'
    days = None
    for k in reversed([k for k in units if k.startswith('clan-')][-4:]):
        tx = lat(' '.join(units[k])).lower()
        mm = re.search(r'stupa na snagu\s+(\w+)\s+dana\s+od\s+dana\s+(?:njegovog\s+|njegove\s+)?objav', tx)
        if mm and mm.group(1) in ORD:
            days = ORD[mm.group(1)]
        elif re.search(r'stupa na snagu\s+(?:danom|na dan|dan)\s+(?:njegovog\s+)?objav', tx):
            days = 0
        if 'stupa na snagu' in tx:
            break
    return units, labels, ' '.join(title), days


def nice_title(title):
    t = re.sub(r'\s+', ' ', title).strip().lower()
    for p in PROPER:
        t = t.replace(p.lower(), p)
    return t


def stems(title):
    words = [w for w in re.findall(r'\w+', lat(title).lower())
             if len(w) >= 5 and w not in ('zakon', 'zakona', 'hercegbosanske', 'zupanije', 'zupaniji', 'izmjenama', 'dopunama')]
    return [w[:5] for w in words]


def classify(laws):
    out = []
    for i, x in enumerate(laws):
        if x['date'] < FROM:
            out.append((x, None, f'before {FROM}: not every issue of 2021 was read, so a later amendment could be missed'))
            continue
        try:
            units, labels, title, days = split_units(x['lines'])
        except ValueError as e:
            out.append((x, None, f'unreadable: {e}'))
            continue
        x['title'] = title
        tl = lat(title).lower()
        if re.search(r'izmjen|dopun|prestank|izmjeni', tl):
            out.append((x, None, 'amending law'))
            continue
        if re.search(r'budžet|proračun|budzet', tl):
            out.append((x, None, 'budget law'))
            continue
        if days is None:
            out.append((x, None, 'in-force clause not found'))
            continue
        c = cite_re(x['issue'], int(x['date'][:4]))
        st = stems(title)
        hit = None
        for y in laws[i + 1:]:
            amending = bool(re.search(r'izmjen|dopun|prestank|izmjeni|prečišćen', lat(y.get('head', '')).lower()))
            for m in c.finditer(y['text']):
                win = y['text'][max(0, m.start() - 300):m.end() + 120].lower()
                if (not st or any(s in win for s in st)) and (amending or REPEAL.search(win)):
                    hit = y
                    break
            if hit:
                break
        if hit:
            out.append((x, None, f'touched later: {hit["issue"]}/{hit["date"][:4]} no. {hit["no"]}'))
            continue
        if (x['date'], x['no']) in LEFT_OUT:
            out.append((x, None, LEFT_OUT[(x['date'], x['no'])]))
            continue
        frm = x['date'] if days == 'consolidated' else (dt.date.fromisoformat(x['date']) + dt.timedelta(days=days)).isoformat()
        if frm > RETRIEVED:
            out.append((x, None, f'takes effect {frm}, after retrieval'))
            continue
        out.append((x, (units, labels, days, frm), 'in'))
    return out


def slugify(s):
    tr = str.maketrans({'č': 'c', 'ć': 'c', 'š': 's', 'ž': 'z', 'đ': 'dj'})
    s = re.sub(r'[^a-z0-9]+', '-', lat(s).lower().translate(tr)).strip('-')
    return s[:60].strip('-')


def main():
    issues, laws = load()
    res = classify(laws)
    if sys.argv[1] == 'list':
        for x, ok, why in res:
            print(x['date'], f"{x['issue']}/{x['date'][2:4]}", x['no'], x.get('title', '?')[:70], '->', why)
        print(sum(1 for r in res if r[1]), 'in of', len(res), '; issues scanned', len(issues),
              issues[0]['date'], '..', issues[-1]['date'])
        return
    n, a, b = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    part = {'sources': [{'name': 'Zeničko-dobojski kanton: Službene novine Zeničko-dobojskog kantona (each issue as a PDF, Bosnian edition)',
                         'url': GAZETTE, 'retrieved': RETRIEVED, 'licence': LICENCE}],
            'laws': {}, 'acts': [], 'applies': [], 'decisions': [], 'ai_use': []}
    if n == 1:
        part['country'] = COUNTRY
    slugs = set()
    for p in sorted(HERE.glob('corpus.d/*.json')):
        if not p.name.startswith(f'{20 + n}-'):
            slugs |= {a['slug'] for a in json.loads(p.read_text(encoding='utf-8'))['acts']}
    for x, ok, why in [r for r in res if r[1]][a:b]:
        units, labels, days, frm = ok
        x['lang'] = LANGS.get(x['lang'], x['lang'])
        cyr = bool(re.search('[а-яА-Я]', x['title']))
        name = ('Закон ' if cyr else 'Zakon ') + nice_title(x['title'])
        slug = slugify(nice_title(x['title']))
        if slug in slugs:
            slug = f'{slug}-{x["date"][:4]}'
        slugs.add(slug)
        yy = int(x['date'][:4]) % 100
        lk = f'snzdk-{x["date"][:4]}-{x["issue"]:03d}-{x["no"]}'
        part['laws'][lk] = {'label': f'Službene novine Zeničko-dobojskog kantona {x["issue"]}/{yy:02d}', 'title': name,
                            'kind': 'law', 'enacted': None, 'published': x['date'], 'url': x['url'],
                            'temporary_until': None, 'restores': None, 'note': None}
        u = {}
        for k, ps in units.items():
            if ps:
                kind = 'art' if k.startswith('clan-') else ('heading' if k == 'naslov' else 'note')
                u[k] = {'label': labels[k], 'kind': kind, 'text': '\n'.join(ps) + '\n'}
        cons = days == 'consolidated'
        part['acts'].append({'slug': slug, 'short': name[:60].rstrip(' ,-'), 'title': name, 'url': x['url'],
                             'first_law': None if cons else lk, 'earlier_laws': [lk] if cons else [],
                             'versions': [{'from': frm, 'source_url': x['url'], 'sha256': x['sha256'], 'units': u,
                                           'credits': {k: [lk] for k in u},
                                           'note': (f'Official consolidated text (prečišćeni tekst) established by the Assembly of Zenica-Doboj Canton, published in the Službene novine Zeničko-dobojskog kantona {x["issue"]}/{yy:02d} of {x["date"]} (act {x["no"]}, {x["lang"]} edition); it applies from its publication, as its last article says. Earlier versions are not in the record.'
                                                    if days == 'consolidated' else
                                                    f'As published in the Službene novine Zeničko-dobojskog kantona {x["issue"]}/{yy:02d} of {x["date"]} (act {x["no"]}, {x["lang"]} edition); in force {days} day(s) after publication, as its final article says.')}]})
    first, last = issues[0], issues[-1]
    part['decisions'].append(f'Laws part {n}: laws the Assembly of Zenica-Doboj Canton published in the Službene novine Zeničko-dobojskog kantona from {FROM} to {last["date"]} (the Bosnian edition of every issue on zdk.ba in that span; laws are checked against every later issue) that no later law in those issues amends, repeals or consolidates: a law is left out when any later amending law or consolidated text cites its gazette number next to a word of its subject, or any later law cites it next to words of repeal. Amending and budget laws are left out. Each is its text as enacted, dated the issue date plus the days its final article names, credited to the law; or, where the Legislative Committee of the Assembly has published an official consolidated text (prečišćeni tekst) that nothing later touches, that text, dated the day it was published (it applies from its publication, as its last article says). Amendments published after {last["date"]}, and decisions of the Constitutional Court, are not in the record.')
    part['decisions'].append('Each law is taken from the Bosnian edition of the gazette (the Canton also publishes a Croatian edition of every issue).')
    part['decisions'].append('Units: uvod.md is the preamble (legal basis and adoption), naslov.md the title, clan-NNN.md each article with its heading (chapter headings stay with the article after them), potpis.md the signature block.')
    part['ai_use'].append('none: the text is read from the gazette PDFs\' text layer by a deterministic parser; no model output is legal text.')
    d = HERE / 'corpus.d'
    d.mkdir(exist_ok=True)
    nm = f'{20 + n}-zakoni-{n:02d}'
    tmp = d / (nm + '.json.tmp')
    tmp.write_text(json.dumps(part, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    tmp.replace(d / (nm + '.json'))
    print(len(part['acts']), 'acts in', nm)


if __name__ == '__main__':
    main()
