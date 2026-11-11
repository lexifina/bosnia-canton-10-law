"""Independent check of a corpus.d part against the cached gazette PDFs. Private.

A different reader (pypdf, not pymupdf) extracts the text of the whole issue; the running headers ('Broj N - Strana
P', the gazette's name, the date line) are removed. Then, for every law: the file's sha256 equals the one recorded;
every paragraph's letters and digits occur in the issue's text, in order (the signature block, printed in two halves,
only has to occur); and from the first paragraph to the last article, the issue's letters and digits equal ours
exactly (nothing left out, nothing added).

    python -X utf8 verify.py 21-zakoni-01.json
"""
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

import pypdf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'world-law'))
import ba_lib  # noqa: E402

# Canton 10 (Narodne novine HBŽ): running headers 'Str. 749 - Broj 6' / '17. lipnja 2014. NARODNE NOVINE Str. 639 -
# Broj 8' and 'HERCEGBOSANSKE ŽUPANIJE' on their own lines are not text of any act.
HEADER = re.compile(r'(?mi)^.*Str(?:\.|ana)\s*\d+\s*[-–]\s*Broj\s+\d+.*$|^.*Broj\s+\d+\s*[-–]\s*Str(?:\.|ana)\s*\d+.*$'
                    r'|^\s*N\s?A\s?R\s?O\s?D\s?N\s?E\s*N\s?O\s?V\s?I\s?N\s?E\s*$|^\s*HERCEG-?\s?BOSANSKE\s+[ŽZ]UPANIJE\s*$'
                    r'|^\s*\d{1,2}\.\s*[^\W\d_]+\s*(?:19|20)\d\d\.?\s*$')
MASTHEAD = re.compile(r'(?:narodnenovine|hercegbosanskežupanije)+')
_text = {}


def issue_text(path):
    if path not in _text:
        r = pypdf.PdfReader(str(path))
        _text[path] = HEADER.sub(' ', '\n'.join(p.extract_text() or '' for p in r.pages))
    return _text[path]


def main(part):
    c = json.loads((HERE / 'corpus.d' / part).read_text(encoding='utf-8'))
    bad = 0
    for a in c['acts']:
        v = a['versions'][0]
        p = HERE / '.cache' / 'by-url' / hashlib.sha256(v['source_url'].encode()).hexdigest()
        assert ba_lib.sha256(p) == v['sha256'], 'sha256 differs'
        src = issue_text(p)
        body = [l for k, u in v['units'].items() if k != 'potpis' for l in u['text'].splitlines()]
        sig = v['units'].get('potpis', {'text': ''})['text'].splitlines()
        found, missing, _ = ba_lib.check_in_order(body, src)
        smiss, _, _ = ba_lib.check_present(sig, src)
        s = ba_lib.letters_digits(src)
        ours = ''.join(ba_lib.letters_digits(x) for x in body)
        first = ba_lib.letters_digits(body[0])
        starts = [m.start() for m in re.finditer(re.escape(first), s)]  # a preamble can repeat word for word
        i = next((k for k in starts if s[k:k + len(ours)] == ours), starts[0] if starts else -1)
        exact = i >= 0 and s[i:i + len(ours)] == ours
        if not exact and i >= 0:
            # the first page's masthead title ('SLUŽBENE NOVINE TUZLANSKOG KANTONA', printed large) may come out of
            # the other reader in the middle of the first column: allow the source extra text only when it is that
            i = next((k for k in starts if s.find(ba_lib.letters_digits(body[1]), k) - k < 3 * len(first) + 50), i)
            j = s.find(ba_lib.letters_digits(body[-1]), i)
            span = s[i:j + len(ba_lib.letters_digits(body[-1]))] if j >= 0 else ''
            sm = difflib.SequenceMatcher(None, span, ours, autojunk=False)
            ops = [o for o in sm.get_opcodes() if o[0] != 'equal']
            exact = bool(span) and all(o[0] == 'delete' and MASTHEAD.fullmatch(span[o[1]:o[2]]) for o in ops)
        ok = not missing and not smiss and exact
        bad += not ok
        print('OK  ' if ok else 'FAIL', a['slug'][:50], f'in order {found}/{len(body)}, signature lines missing {len(smiss)}, exact span {exact}')
        for m in (missing + smiss)[:3]:
            print('      missing:', m[:150])
        if not exact and i >= 0:
            k = next((n for n in range(min(len(ours), len(s) - i)) if s[i + n] != ours[n]), None)
            if k is not None:
                print('      first difference at', k, 'source:', s[i + k - 30:i + k + 40], '| ours:', ours[k - 30:k + 40])
    print('acts failing:', bad)
    return bad


if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1]) else 0)
