"""Line-end hyphens in Canton 10's gazette (copied from Bosnian-Podrinje, gitlaw-bosnia-deep 2026-11-11; the dictionary is built from Canton 10's own issues). Private.
'odras-/lih', but also break real compounds at their own hyphen: 'Bosansko-/podrinjskog'). Private.

The dictionary is every word the 64 cached issues print unbroken inside a line (the last word of a line ending in '-'
and the first word of every line are left out, since either may be a fragment), lowercased, with its count; a word
with an inner hyphen ('bosansko-podrinjskog') is a compound seen whole.

RULE (also written into each part's decisions): a line ending 'A-' followed by a line starting 'B' is joined as 'AB'
when 'AB' occurs unbroken in the dictionary more often than 'A-B'; as 'A-B' when 'A-B' occurs more often than 'AB';
when neither occurs (or both equally often): 'A-B' if B starts with a capital letter or a digit, or A ends in a digit,
or A's last part (6 letters or more) ends in 'o' and B (4 letters or more) occurs at least twice as a whole word in
the dictionary (a compound adjective such as 'sigurnosno-/tehničkih'); otherwise 'AB'. A line ending ' -' (a dash after a space) is never a break inside a word.
"""
import collections
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORDS = HERE / '.tmp' / 'words.json'
TOK = re.compile(r'\w+(?:-\w+)*')
STATS = collections.Counter()
DECIDED = collections.defaultdict(collections.Counter)  # (A, B) -> chosen form counts: the same pair always the same way
UNSEEN = []
_dict = None


def build():
    import gzread
    c = collections.Counter()
    urls = [u for u in (HERE / '.cache' / 'issues.txt').read_text(encoding='utf-8').split() if u]
    for u in urls:
        p = HERE / '.cache' / 'by-url' / hashlib.sha256(u.encode()).hexdigest()
        lines, _ = gzread.issue_lines(p)
        for l in lines:
            toks = TOK.findall(l['text'])
            if not toks:
                continue
            toks = toks[1:]  # the first word of a line may be the tail of a broken word
            if toks and l['text'].rstrip().endswith('-') and not l['text'].rstrip().endswith(' -'):
                toks = toks[:-1]  # the head of a broken word
            c.update(t.lower() for t in toks)
    WORDS.parent.mkdir(parents=True, exist_ok=True)
    WORDS.write_text(json.dumps(c, ensure_ascii=False), encoding='utf-8')
    return c


def words():
    global _dict
    if _dict is None:
        _dict = json.loads(WORDS.read_text(encoding='utf-8')) if WORDS.exists() else build()
    return _dict


def broken(p):
    p = p.rstrip()
    return p.endswith('-') and not p.endswith(' -') and len(p) > 1 and p[-2].isalnum()


def join(p, t):
    """Join a wrapped line t onto paragraph p (one space, or no space across a line-end hyphen, by RULE)."""
    p = p.rstrip()
    if not broken(p):
        return p + ' ' + t
    ma = re.search(r'(\w+(?:-\w+)*)-$', p)
    mb = TOK.match(t)
    if not ma or not mb:
        STATS['hyphen kept: no word on one side'] += 1
        return p + t
    a, b = ma.group(1), mb.group(0)
    w = words()
    cj, ck = w.get((a + b).lower(), 0), w.get((a + '-' + b).lower(), 0)
    if cj > ck:
        keep, why = False, 'joined: joined word seen unbroken'
    elif ck > cj:
        keep, why = True, 'hyphen kept: hyphenated word seen unbroken'
    elif b[0].isupper() or b[0].isdigit() or a[-1].isdigit():
        keep, why = True, 'hyphen kept: unseen, capital or digit'
    elif (len(a.split('-')[-1]) >= 6 and a.lower().endswith('o') and len(b) >= 4 and w.get(b.lower(), 0) >= 2):
        keep, why = True, 'hyphen kept: unseen, two whole words (A ends in -o)'
    else:
        keep, why = False, 'joined: unseen, lowercase'
    STATS[why] += 1
    DECIDED[(a.lower(), b.lower())]['keep' if keep else 'join'] += 1
    if 'unseen' in why:
        UNSEEN.append(a + '-/' + b + (' -> kept' if keep else ' -> joined'))
    return p + t if keep else p[:-1] + t


def inconsistent():
    return {f'{a}-/{b}': dict(v) for (a, b), v in DECIDED.items() if len(v) > 1}


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(HERE))
    c = build()
    print(len(c), 'distinct words')
