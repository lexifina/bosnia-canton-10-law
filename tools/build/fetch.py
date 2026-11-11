"""Fetch Zenica-Doboj Canton gazette issues (zdk.ba) into .cache/. Private: never published.

    python -X utf8 fetch.py urls <list>    # URLs named in a text file, one per line
    python -X utf8 fetch.py one <url>

One request at a time, >= 4 s apart (robots.txt 404; we start slow). Stops on any 403, 429, 5xx
twice in a row, or a challenge page. Every request is logged in .cache/requests.jsonl.
"""
import hashlib, json, re, subprocess, sys, time, urllib.parse
from pathlib import Path

import psutil
psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)

HERE = Path(__file__).resolve().parent
CACHE = HERE / '.cache'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
GAP = 4.0
last = [0.0]
bad = [0]


def path_for(url):
    return CACHE / 'by-url' / hashlib.sha256(url.encode()).hexdigest()


def get(url):
    p = path_for(url)
    if p.exists():
        return p
    wait = GAP - (time.time() - last[0])
    if wait > 0:
        time.sleep(wait)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.part')
    r = subprocess.run(['curl', '-s', '-L', '--max-redirs', '3', '-m', '60', '-A', UA, '--compressed', '-o', str(tmp), '-w', '%{http_code}', url],
                       capture_output=True, text=True)
    last[0] = time.time()
    code = r.stdout.strip()
    with open(CACHE / 'requests.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps({'t': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'url': url, 'code': code,
                            'exit': r.returncode}) + '\n')
    if r.returncode or code in ('403', '429'):
        raise SystemExit(f'stop: {code} exit {r.returncode} on {url}')
    body = tmp.read_bytes()[:4000].lower() if tmp.exists() else b''
    if b'just a moment' in body or b'captcha' in body or b'cf-chl' in body:
        raise SystemExit(f'stop: challenge page on {url}')
    if code.startswith('5'):
        bad[0] += 1
        tmp.unlink(missing_ok=True)
        if bad[0] >= 2:
            raise SystemExit(f'stop: two 5xx in a row ({url})')
        time.sleep(20)
        return get(url)
    bad[0] = 0
    if code != '200':
        tmp.unlink(missing_ok=True)
        print('skip', code, url)
        return None
    tmp.replace(p)
    return p


def main():
    if sys.argv[1] == 'urls':
        for url in Path(sys.argv[2]).read_text(encoding='utf-8').splitlines():
            if url.strip():
                p = get(url.strip())
                print(p.name if p else None, url, flush=True)
    elif sys.argv[1] == 'one':
        p = get(sys.argv[2]); print(p)


if __name__ == '__main__':
    main()
