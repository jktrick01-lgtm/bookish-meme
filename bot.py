
# language: Python 3.10+, file: wp2_fixed.py
# Telegram bot — analyze, bypass, cycles, fire, txt
# FIXES: cancel mid-job | batch send every N numbers | crash-safe partial save | faster
# deps: requests

import re, random, time, json, base64, threading
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# ================= CONFIG =================
TG_TOKEN = "8885488628:AAF05OaKbNZeG5fNzUk4CCzndDz-HkjyZjQ"
ALLOWED_CHATS = {8753914631, 8565258976}

THREADS      = 30          # ↑ was 20 — faster parallel workers
MAX_HOPS     = 15
MAX_ATTEMPTS = 8
TIMEOUT      = 10          # ↓ was 12 — tighter so slow workers don't block
HOP_DELAY    = 0
WORK_DIR     = Path("/sdcard/wp1")
WORK_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SEND_EVERY = 20      # har 20 unique numbers pe auto-send karo

API = "https://api.telegram.org/bot" + TG_TOKEN

# ================= UA / IP =================
UA_POOL = [
    'Mozilla/5.0 (Linux; Android 16; CPH2665 Build/BP2A.250605.015) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{c}.0.7922.202 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 15; SM-S928B Build/AP3A.240905.015) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{c}.0.7204.179 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 14; 23021RAAEG Build/UKQ1.231003.002) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{c}.0.6943.137 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 15; V2312 Build/AP3A.240905.015) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{c}.0.7204.157 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 16; CPH2591 Build/BP2A.250605.015) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{c}.0.7922.187 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 16; SM-S921B Build/AP3A.240905.015) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{c}.0.7922.190 Mobile Safari/537.36',
]
CHROME_VERSIONS = [148, 149, 150, 151, 152, 153]

INDIAN_IP_PREFIXES = [
    "49.36.", "49.37.", "49.44.", "49.45.", "106.51.", "106.192.", "106.193.",
    "117.96.", "117.97.", "117.98.", "117.99.", "122.160.", "122.161.", "122.162.",
    "182.64.", "182.65.", "182.66.", "182.67.", "223.176.", "223.177.", "223.178.",
    "43.241.", "43.242.", "43.243.", "59.144.", "59.145.", "59.146.",
    "27.56.", "27.57.", "27.58.", "27.59.", "106.79.", "106.80.", "106.81.",
]

# ================= AES-128 pure python =================
SBOX = [
0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
]
INV_SBOX = [0]*256
for _i, _v in enumerate(SBOX): INV_SBOX[_v] = _i
RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36]

def _xtime(a): return ((a << 1) ^ 0x1b) & 0xff if a & 0x80 else (a << 1)

def _mul(a, b):
    r = 0
    for _ in range(8):
        if b & 1: r ^= a
        b >>= 1; a = _xtime(a)
    return r

def _expand_key(key):
    w = [list(key[i*4:i*4+4]) for i in range(4)]
    for i in range(4, 44):
        t = list(w[i-1])
        if i % 4 == 0:
            t = t[1:] + t[:1]; t = [SBOX[x] for x in t]; t[0] ^= RCON[i//4 - 1]
        w.append([w[i-4][j] ^ t[j] for j in range(4)])
    return [bytes(b for word in w[i*4:i*4+4] for b in word) for i in range(11)]

def _add_round_key(state, rk): return bytearray(a ^ b for a, b in zip(state, rk))

def _inv_shift_rows(state):
    new = bytearray(16)
    for c in range(4):
        for r in range(4): new[4*c + r] = state[4*((c - r) % 4) + r]
    return new

def _inv_mix_columns(state):
    new = bytearray(16)
    for c in range(4):
        a0, a1, a2, a3 = state[4*c], state[4*c+1], state[4*c+2], state[4*c+3]
        new[4*c+0] = _mul(a0,14) ^ _mul(a1,11) ^ _mul(a2,13) ^ _mul(a3, 9)
        new[4*c+1] = _mul(a0, 9) ^ _mul(a1,14) ^ _mul(a2,11) ^ _mul(a3,13)
        new[4*c+2] = _mul(a0,13) ^ _mul(a1, 9) ^ _mul(a2,14) ^ _mul(a3,11)
        new[4*c+3] = _mul(a0,11) ^ _mul(a1,13) ^ _mul(a2, 9) ^ _mul(a3,14)
    return new

def _decrypt_block(block, rks):
    state = _add_round_key(bytearray(block), rks[10])
    for r in range(9, 0, -1):
        state = _inv_shift_rows(state); state = bytearray(INV_SBOX[b] for b in state)
        state = _add_round_key(state, rks[r]); state = _inv_mix_columns(state)
    state = _inv_shift_rows(state); state = bytearray(INV_SBOX[b] for b in state)
    state = _add_round_key(state, rks[0])
    return bytes(state)

def aes_cbc_decrypt(ct, key, iv):
    rks = _expand_key(key); out = bytearray(); prev = iv
    for i in range(0, len(ct), 16):
        block = ct[i:i+16]; dec = _decrypt_block(block, rks)
        out.extend(a ^ b for a, b in zip(dec, prev)); prev = block
    return bytes(out)

def aes_ecb_decrypt(ct, key):
    rks = _expand_key(key); out = bytearray()
    for i in range(0, len(ct), 16): out.extend(_decrypt_block(ct[i:i+16], rks))
    return bytes(out)

# ================= helpers =================
def random_ua(): return random.choice(UA_POOL).format(c=random.choice(CHROME_VERSIONS))

def random_indian_ip():
    return random.choice(INDIAN_IP_PREFIXES) + str(random.randint(1,254)) + "." + str(random.randint(1,254))

def build_headers():
    return {
        "User-Agent": random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Upgrade-Insecure-Requests": "1", "dnt": "1",
        "X-Requested-With": "via.bolte",
        "Sec-Fetch-Site": "none", "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1", "Sec-Fetch-Dest": "document",
        "sec-ch-ua": '"Not=A?Brand";v="99", "Android WebView";v="151", "Chromium";v="151"',
        "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": '"Android"',
        "Connection": "keep-alive",
        "X-Forwarded-For": random_indian_ip(),
    }

def make_session():
    s = requests.Session()
    a = requests.adapters.HTTPAdapter(pool_connections=THREADS, pool_maxsize=THREADS*2)
    s.mount("https://", a); s.mount("http://", a)
    return s

def resolve_url(base, loc):
    if not loc: return None
    if loc.startswith("/"):
        p = urlparse(base); return p.scheme + "://" + p.netloc + loc
    if not loc.startswith("http"):
        p = urlparse(base); return p.scheme + "://" + p.netloc + "/" + loc.lstrip("/")
    return loc

# ================= bypass detectors =================
def try_decode_b64(s):
    try:
        s2 = s.strip(); s2 += "=" * ((-len(s2)) % 4)
        return base64.b64decode(s2).decode("utf-8", "ignore")
    except Exception: return None

def find_b64_redirects(html):
    out = []
    for m in re.finditer(r"atob\(\s*[\x22\x27]([A-Za-z0-9+/=]+)[\x22\x27]\s*\)", html):
        dec = try_decode_b64(m.group(1))
        if dec and ("wa.me" in dec or "whatsapp.com" in dec or "http" in dec):
            out.append(dec.strip())
    for m in re.finditer(r"location(?:\.href|\.replace)?\s*\(?\s*[\x22\x27]?atob\(\s*[\x22\x27]([A-Za-z0-9+/=]+)[\x22\x27]", html):
        dec = try_decode_b64(m.group(1))
        if dec: out.append(dec.strip())
    seen = set(); res = []
    for x in out:
        if x not in seen: seen.add(x); res.append(x)
    return res

def find_js_string_redirects(html):
    out = []
    for m in re.finditer(r"location\.(?:replace|href|assign)\s*\(?\s*[\x22\x27]([^\x22\x27]+)[\x22\x27]", html):
        v = m.group(1)
        if v.startswith("http") or v.startswith("/"): out.append(v)
    for m in re.finditer(r"(?:window\.|document\.)?location\s*=\s*[\x22\x27]([^\x22\x27]+)[\x22\x27]", html):
        v = m.group(1)
        if v.startswith("http") or v.startswith("/"): out.append(v)
    return out

def find_meta_refresh(html):
    out = []
    for m in re.finditer(r'<meta[^>]+http-equiv\s*=\s*[\x22\x27]?refresh[\x22\x27]?[^>]+content\s*=\s*[\x22\x27][^\x22\x27]*url=([^\x22\x27]+)[\x22\x27]', html, re.I):
        out.append(m.group(1))
    return out

# ================= testcookie =================
def solve_testcookie(html):
    m = re.search(r"slowAES\.decrypt\(\s*(\w+)\s*,\s*(\d+)\s*,\s*(\w+)\s*,\s*(\w+)\s*\)", html)
    if not m: return None
    c_var, mode, a_var, b_var = m.group(1), int(m.group(2)), m.group(3), m.group(4)

    def grab_hex(v):
        m2 = re.search(v + r"\s*=\s*toNumbers\(\s*[\x22\x27]([0-9a-fA-F]+)[\x22\x27]\s*\)", html)
        if m2:
            h = m2.group(1); return bytes(int(h[i:i+2], 16) for i in range(0, len(h), 2))
        m3 = re.search(v + r"\s*=\s*\[([^\]]+)\]", html)
        if m3:
            nums = [int(x) for x in re.findall(r"\d+", m3.group(1))]
            if nums: return bytes(nums)
        return None

    key, iv, ct = grab_hex(a_var), grab_hex(b_var), grab_hex(c_var)
    if not key or not iv or not ct: return None

    m_name = re.search(r"document\.cookie\s*=\s*[\x22\x27]([^=;]+)=", html)
    cookie_name = m_name.group(1).strip() if m_name else "__test"

    try:
        pt = aes_cbc_decrypt(ct, key, iv) if mode == 2 else aes_ecb_decrypt(ct, key)
    except Exception: return None
    if pt:
        pad = pt[-1]
        if 1 <= pad <= 16 and pt.endswith(bytes([pad]) * pad): pt = pt[:-pad]
    return pt.hex(), cookie_name

def bypass_testcookie(session, url, headers, resp):
    if "slowAES" not in resp.text and "__test" not in resp.text: return None
    result = solve_testcookie(resp.text)
    if not result: return None
    cookie_val, cookie_name = result
    session.cookies.set(cookie_name, cookie_val, domain=urlparse(url).hostname, path="/")
    retry_url = url
    m_loc = re.search(r"location\.href\s*=\s*[\x22\x27]([^\x22\x27]+)[\x22\x27]", resp.text)
    if m_loc: retry_url = resolve_url(url, m_loc.group(1))
    return session.get(retry_url, headers=headers, timeout=TIMEOUT, allow_redirects=False)

# ================= extract =================
WA_ME_RE    = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send/?\?phone=|web\.whatsapp\.com/send\?phone=|whatsapp\.com/send/?\?phone=)(\d{6,15})")
ANY_PHONE_RE = re.compile(r"(?:\+?91[\-\s]?)?([6-9]\d{9})\b")

def extract_numbers(text):
    if not text: return set()
    nums = set()
    for m in WA_ME_RE.finditer(text): nums.add(m.group(1))
    for m in ANY_PHONE_RE.finditer(text): nums.add(m.group(1))
    return nums

# ================= core scraper =================
CACHE_BUST_PARAMS = ["_r", "igshid", "fbclid", "utm_content", "v", "t", "s", "ref"]

def _bust_url(url):
    r = random.randint(100000, 9999999)
    pname = random.choice(CACHE_BUST_PARAMS)
    sep = "&" if "?" in url else "?"
    return url + sep + pname + "=" + str(r)

def worker_scrape(seed_url, stop_event=None):
    """
    Rotating link handling + cancel support via stop_event.
    Returns set of found numbers. Checks stop_event each attempt.
    """
    for attempt in range(MAX_ATTEMPTS):
        # --- CANCEL CHECK ---
        if stop_event and stop_event.is_set():
            return set()

        session = make_session()
        found   = set()
        url     = _bust_url(seed_url)
        headers = build_headers()
        visited = set()
        landed_wa = False

        for hop in range(MAX_HOPS):
            if stop_event and stop_event.is_set():
                return found  # return partial even on cancel

            if url in visited: break
            visited.add(url)
            try:
                r = session.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=False)
            except requests.RequestException:
                break

            body = r.text or ""
            found |= extract_numbers(body)
            found |= extract_numbers(url)

            # testcookie challenge
            if r.status_code == 200 and ("slowAES" in body or "__test" in body):
                solved = bypass_testcookie(session, url, headers, r)
                if solved is not None:
                    r = solved; body = r.text or ""
                    found |= extract_numbers(body); found |= extract_numbers(url)

            # in-page JS / b64 / meta redirects
            if r.status_code == 200 and body:
                redirects = find_b64_redirects(body) + find_js_string_redirects(body) + find_meta_refresh(body)
                for tgt in redirects:
                    tgt = resolve_url(url, tgt)
                    if not tgt: continue
                    found |= extract_numbers(tgt)
                    if "t.me" in tgt or "telegram" in tgt:
                        break  # next attempt
                    if "wa.me" in tgt or "whatsapp.com" in tgt:
                        try:
                            r2 = session.get(tgt, headers=headers, timeout=TIMEOUT, allow_redirects=True)
                            found |= extract_numbers(r2.text or ""); found |= extract_numbers(r2.url or "")
                        except requests.RequestException: pass
                        landed_wa = True; break
                    try:
                        r2 = session.get(tgt, headers=headers, timeout=TIMEOUT, allow_redirects=False)
                        found |= extract_numbers(r2.text or ""); found |= extract_numbers(tgt)
                        loc2 = r2.headers.get("Location")
                        if loc2:
                            loc2 = resolve_url(tgt, loc2)
                            found |= extract_numbers(loc2)
                            if "t.me" in loc2 or "telegram" in loc2:
                                break
                            if "wa.me" in loc2 or "whatsapp.com" in loc2:
                                try:
                                    r3 = session.get(loc2, headers=headers, timeout=TIMEOUT, allow_redirects=True)
                                    found |= extract_numbers(r3.text or ""); found |= extract_numbers(r3.url or "")
                                except requests.RequestException: pass
                                landed_wa = True; break
                    except requests.RequestException: pass
                if landed_wa: break

            # HTTP redirect
            if r.status_code in (301, 302, 303, 307, 308):
                loc = r.headers.get("Location")
                if not loc: break
                loc = resolve_url(url, loc)
                found |= extract_numbers(loc)

                if "t.me" in loc or "telegram" in loc:
                    break  # next attempt

                if "wa.me" in loc or "whatsapp.com" in loc:
                    try:
                        r2 = session.get(loc, headers=headers, timeout=TIMEOUT, allow_redirects=True)
                        found |= extract_numbers(r2.text or ""); found |= extract_numbers(r2.url or "")
                    except requests.RequestException: pass
                    landed_wa = True; break

                url = loc
                if HOP_DELAY > 0: time.sleep(HOP_DELAY)
                continue
            break

        if landed_wa and found:
            return found
        time.sleep(0.2 + random.random() * 0.5)  # slightly shorter delay

    return set()

# ================= analyze =================
def analyze_url(url):
    session = make_session()
    headers = build_headers()
    info = {"protection": "none", "chain": [], "reachable": False, "note": ""}
    cur = _bust_url(url)
    visited = set()
    for hop in range(MAX_HOPS):
        if cur in visited: break
        visited.add(cur)
        try:
            r = session.get(cur, headers=headers, timeout=TIMEOUT, allow_redirects=False)
        except Exception as e:
            info["chain"].append("ERR " + str(e)[:60]); break
        info["reachable"] = True
        body = r.text or ""

        if r.status_code == 200 and ("slowAES" in body or "__test" in body):
            info["protection"] = "testcookie-nginx-module (AES-128-CBC)"
            r2 = bypass_testcookie(session, cur, headers, r)
            if r2 is not None:
                info["chain"].append("200 challenge → bypass OK → " + str(r2.status_code))
                if r2.status_code in (301,302,303,307,308):
                    cur = resolve_url(cur, r2.headers.get("Location")); continue
            break

        if r.status_code == 200 and body:
            b64s = find_b64_redirects(body)
            if b64s:
                info["protection"] = "base64 JS redirect (atob)"
                for t in b64s: info["chain"].append("atob → " + t[:90])
                cur = resolve_url(cur, b64s[0])
                if "wa.me" in cur or "whatsapp.com" in cur:
                    info["chain"].append("→ wa.me reached"); break
                if "t.me" in cur or "telegram" in cur:
                    info["chain"].append("→ t.me (rotating link, retry needed)")
                    info["note"] = "rotating"
                    break
                continue
            metas = find_meta_refresh(body)
            if metas:
                info["protection"] = "meta refresh"
                info["chain"].append("meta → " + metas[0][:90])
                cur = resolve_url(cur, metas[0]); continue
            jss = find_js_string_redirects(body)
            if jss:
                info["protection"] = "JS string redirect"
                info["chain"].append("js → " + jss[0][:90])
                cur = resolve_url(cur, jss[0]); continue

        if r.status_code in (301,302,303,307,308):
            loc = r.headers.get("Location")
            info["chain"].append(str(r.status_code) + " → " + (loc or "")[:70])
            cur = resolve_url(cur, loc)
            if cur and ("wa.me" in cur or "whatsapp.com" in cur):
                info["chain"].append("→ wa.me reached"); break
            if cur and ("t.me" in cur or "telegram" in cur):
                info["chain"].append("→ t.me (rotating — bot retry karega)")
                info["note"] = "rotating"
                break
            continue

        info["chain"].append(str(r.status_code) + " " + cur[:70])
        break
    return info

# ================= run cycles (with cancel + batch send) =================
def run_cycles(url, n, on_progress=None, on_batch=None, stop_event=None):
    """
    url          — seed URL
    n            — total cycles
    on_progress  — callback(cycle_i, total, unique_count)
    on_batch     — callback(new_numbers_set, total_found_so_far_set)
                   called every time BATCH_SEND_EVERY new unique numbers accumulate
    stop_event   — threading.Event; set it to cancel mid-run
    Returns final set of all unique numbers.
    """
    found       = set()          # all unique found so far
    batch_floor = 0              # how many were there at last batch send

    for i in range(1, n + 1):
        if stop_event and stop_event.is_set():
            break

        with ThreadPoolExecutor(max_workers=THREADS) as ex:
            futs = [ex.submit(worker_scrape, url, stop_event) for _ in range(THREADS)]
            for f in as_completed(futs):
                if stop_event and stop_event.is_set():
                    # cancel remaining futures quickly
                    for remaining in futs:
                        remaining.cancel()
                    break
                try:
                    new = f.result()
                    before = len(found)
                    found |= new
                    after  = len(found)

                    # ---- BATCH SEND CHECK ----
                    if on_batch and after >= batch_floor + BATCH_SEND_EVERY:
                        # which numbers are new since last batch?
                        batch_new = found - set()   # we need delta — track separately below
                        on_batch(found, after)
                        batch_floor = (after // BATCH_SEND_EVERY) * BATCH_SEND_EVERY

                except Exception:
                    pass

        if on_progress:
            try: on_progress(i, n, len(found))
            except Exception: pass

    return found

# ================= telegram api =================
TG_SESSION = make_session()

def tg(method, **kwargs):
    for attempt in range(3):          # retry on network blip
        try:
            r = TG_SESSION.post(API + "/" + method, timeout=60, **kwargs)
            return r.json()
        except Exception as e:
            print("[tg] " + method + " err: " + str(e))
            if attempt < 2: time.sleep(1.5)
    return {"ok": False}

def send_msg(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if reply_markup: data["reply_markup"] = json.dumps(reply_markup)
    return tg("sendMessage", data=data)

def edit_msg(chat_id, msg_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "message_id": msg_id, "text": text}
    if reply_markup: data["reply_markup"] = json.dumps(reply_markup)
    return tg("editMessageText", data=data)

def send_doc(chat_id, path, caption=""):
    with open(path, "rb") as f:
        return tg("sendDocument",
                  data={"chat_id": chat_id, "caption": caption},
                  files={"document": (Path(path).name, f)})

# ================= state =================
# Per-chat state now also holds a stop_event for cancel
STATE = {}

CYCLES_KB = {
    "inline_keyboard": [[
        {"text": "🚀 5",   "callback_data": "cyc:5"},
        {"text": "🚀 10",  "callback_data": "cyc:10"},
        {"text": "🚀 20",  "callback_data": "cyc:20"},
    ], [
        {"text": "🚀 50",  "callback_data": "cyc:50"},
        {"text": "🚀 100", "callback_data": "cyc:100"},
    ], [
        {"text": "❌ Cancel", "callback_data": "cyc:cancel"},
    ]]
}

def is_allowed(chat_id):
    if ALLOWED_CHATS is None: return True
    return chat_id in ALLOWED_CHATS

def get_state(chat_id): return STATE.setdefault(chat_id, {"step": "idle", "url": None, "stop_event": None})
def set_state(chat_id, **kw): get_state(chat_id).update(kw)

def cancel_running_job(chat_id):
    """Signal the running job for this chat to stop."""
    st = get_state(chat_id)
    ev = st.get("stop_event")
    if ev and isinstance(ev, threading.Event):
        ev.set()

# ================= partial / crash-safe save =================
_partial_lock = threading.Lock()

def partial_save(chat_id, numbers, ts):
    """Save numbers to a crash-safe partial file and return path."""
    fname = "partial_" + str(chat_id) + "_" + ts + ".txt"
    fpath = WORK_DIR / fname
    try:
        with _partial_lock:
            fpath.write_text("\n".join(sorted(numbers)) + ("\n" if numbers else ""), encoding="utf-8")
    except Exception as e:
        print("[save] partial save err: " + str(e))
    return fpath

# ================= extraction thread =================
def _extraction_thread(chat_id, url, n, status_id, ts):
    """Runs in a background thread. Handles progress, batch sends, cancel, and final send."""
    stop_event = get_state(chat_id)["stop_event"]
    t0         = time.time()
    last_upd   = [0]
    batch_num  = [0]                # how many batch files sent so far
    all_found  = set()              # track everything for partial save

    def on_prog(i, total, count):
        if stop_event.is_set(): return
        now = time.time()
        if now - last_upd[0] < 1.2 and i != total: return
        last_upd[0] = now
        pct = int(i * 100 / total)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        try:
            edit_msg(chat_id, status_id,
                "⏳ Cycle " + str(i) + "/" + str(total) + "\n"
                + bar + " " + str(pct) + "%\n"
                + "📊 Unique: " + str(count) + "\n"
                + "💾 Batches sent: " + str(batch_num[0]) + "\n"
                + "🛑 /cancel to stop")
        except Exception: pass

    def on_batch(all_numbers, count):
        """Called every BATCH_SEND_EVERY new unique numbers."""
        batch_num[0] += 1
        bfname = "batch" + str(batch_num[0]) + "_" + str(chat_id) + "_" + ts + ".txt"
        bfpath = WORK_DIR / bfname
        nums_sorted = sorted(all_numbers)
        try:
            bfpath.write_text("\n".join(nums_sorted) + "\n", encoding="utf-8")
            send_doc(chat_id, str(bfpath),
                caption="📦 Batch #" + str(batch_num[0]) + " — " + str(count) + " unique numbers so far")
        except Exception as e:
            print("[batch] err: " + str(e))

    # ---- CRASH-SAFE WRAPPER ----
    try:
        found = run_cycles(url, n,
                           on_progress=on_prog,
                           on_batch=on_batch,
                           stop_event=stop_event)
    except Exception as e:
        # Crash! Save whatever we have
        recovered = partial_save(chat_id, all_found, ts)
        try:
            edit_msg(chat_id, status_id, "⚠️ Error: " + str(e)[:180] + "\n\n💾 Partial save in progress...")
            if all_found:
                send_doc(chat_id, str(recovered),
                    caption="⚠️ Crash recovery — " + str(len(all_found)) + " numbers saved")
            else:
                send_msg(chat_id, "⚠️ Crashed, 0 numbers collected before crash.")
        except Exception: pass
        set_state(chat_id, step="idle", stop_event=None)
        return

    # ---- DONE or CANCELLED ----
    elapsed = round(time.time() - t0, 1)
    numbers = sorted(found)
    cancelled = stop_event.is_set()

    # Final file (always save)
    suffix   = "_cancelled" if cancelled else ""
    fname    = "whatsapp_numbers_" + str(chat_id) + "_" + ts + suffix + ".txt"
    fpath    = WORK_DIR / fname
    try:
        fpath.write_text("\n".join(numbers) + ("\n" if numbers else ""), encoding="utf-8")
    except Exception as e:
        print("[save] final save err: " + str(e))

    status_txt = (
        ("⛔ *Cancelled!*" if cancelled else "✅ *Extraction Complete!*") + "\n"
        "━━━━━━━━━━━━━━━━\n"
        "🔄 Cycles: " + (str(n) if not cancelled else "stopped early") + "\n"
        "🧵 Threads: " + str(THREADS) + " × " + str(MAX_ATTEMPTS) + " attempts\n"
        "📊 Unique: " + str(len(numbers)) + "\n"
        "📦 Batches sent: " + str(batch_num[0]) + "\n"
        "⏱️ Time: " + str(elapsed) + "s\n"
        "━━━━━━━━━━━━━━━━"
    )
    try:
        edit_msg(chat_id, status_id, status_txt)
    except Exception: pass

    # Send final file only if we have numbers AND no batch was sent yet
    # (if batches were sent, user already has all numbers)
    if numbers and batch_num[0] == 0:
        try:
            send_doc(chat_id, str(fpath),
                caption="📁 " + str(len(numbers)) + " unique" + (" (cancelled)" if cancelled else ""))
        except Exception as e:
            print("[doc] " + str(e))
    elif numbers and batch_num[0] > 0:
        # Send a final consolidated file too
        try:
            send_doc(chat_id, str(fpath),
                caption="📁 Final: " + str(len(numbers)) + " unique total" + (" (cancelled)" if cancelled else ""))
        except Exception: pass
    elif not numbers:
        send_msg(chat_id, "😶 Koi number nahi mila" + (" (cancelled)" if cancelled else ""))

    set_state(chat_id, step="await_link", url=None, stop_event=None)

# ================= handlers =================
def handle_text(chat_id, text, msg_id):
    if not is_allowed(chat_id): send_msg(chat_id, "❌ not allowed"); return
    text = text.strip()
    st   = get_state(chat_id)

    if text in ("/start", "menu"):
        cancel_running_job(chat_id)
        set_state(chat_id, step="await_link", url=None, stop_event=None)
        send_msg(chat_id,
            "🤖 *Number Extractor Bot*\n\n"
            "link bhej — analyze → cycles → fire → txt\n\n"
            "commands: /cancel /stats\n"
            "⚡ Auto-sends every " + str(BATCH_SEND_EVERY) + " numbers found")
        return

    if text in ("/cancel", "cancel"):
        if st.get("step") == "running":
            cancel_running_job(chat_id)
            send_msg(chat_id, "⛔ Cancelling... numbers collected so far bhej dega")
        else:
            set_state(chat_id, step="idle", url=None)
            send_msg(chat_id, "❌ cancelled")
        return

    if text == "/stats":
        n = 0
        p = WORK_DIR / "numbers.txt"
        if p.exists(): n = len([l for l in p.read_text().splitlines() if l.strip()])
        send_msg(chat_id, "📊 total saved: " + str(n)); return

    m = re.match(r"https?://\S+", text)
    if m:
        if st.get("step") == "running":
            send_msg(chat_id, "⏳ Job chal raha hai. /cancel karo pehle."); return
        url = m.group(0)
        set_state(chat_id, step="analyzing", url=url)
        send_msg(chat_id, "🔍 *Analyzing...*\n\n`" + url[:120] + "`")
        try:
            info = analyze_url(url)
        except Exception as e:
            send_msg(chat_id, "❌ Analyze error: " + str(e)[:150])
            set_state(chat_id, step="await_link"); return
        chain_txt = "\n".join("  " + c for c in info["chain"][:8]) or "  (none)"
        note_line = ("\n⚠️ " + info["note"] + " link detected") if info.get("note") else ""
        txt = (
            "✅ *Analysis Complete*\n"
            "━━━━━━━━━━━━━━━━\n"
            "🔒 Protection: `" + info["protection"] + "`\n"
            "🌐 Reachable: " + ("yes" if info["reachable"] else "no") + note_line + "\n"
            "🔗 Chain:\n" + chain_txt + "\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "⚙️ Kitne cycles chalaun?"
        )
        set_state(chat_id, step="await_cycles")
        send_msg(chat_id, txt, reply_markup=CYCLES_KB)
        return

    if re.match(r"^\d+$", text):
        if st["step"] != "await_cycles" or not st.get("url"):
            send_msg(chat_id, "pehle link bhej."); return
        n = int(text)
        if n < 1 or n > 5000:
            send_msg(chat_id, "1 se 5000 ke beech daal"); return
        start_extraction(chat_id, st["url"], n)
        return

    send_msg(chat_id, "link bhej (http/https) ya /start")

def handle_callback(chat_id, data, msg_id):
    if not is_allowed(chat_id): return
    st = get_state(chat_id)
    if not data.startswith("cyc:"): return
    val = data.split(":", 1)[1]
    if val == "cancel":
        if st.get("step") == "running":
            cancel_running_job(chat_id)
            edit_msg(chat_id, msg_id, "⛔ Cancelling...")
        else:
            set_state(chat_id, step="idle", url=None)
            edit_msg(chat_id, msg_id, "❌ cancelled")
        return
    if st["step"] != "await_cycles" or not st.get("url"):
        edit_msg(chat_id, msg_id, "pehle link bhej"); return
    n = int(val)
    edit_msg(chat_id, msg_id, "🚀 launching " + str(n) + " cycles...")
    start_extraction(chat_id, st["url"], n)

def start_extraction(chat_id, url, n):
    stop_event = threading.Event()
    set_state(chat_id, step="running", stop_event=stop_event)

    ts = time.strftime("%Y%m%d_%H%M%S")
    status = send_msg(chat_id,
        "⏳ *Starting extraction...*\n\n"
        "Cycles: " + str(n) + "\n"
        "Threads: " + str(THREADS) + "\n"
        "Auto-batch: every " + str(BATCH_SEND_EVERY) + " numbers\n"
        "🛑 /cancel to stop anytime")
    status_id = status.get("result", {}).get("message_id")

    # Run in background thread so polling loop is not blocked
    t = threading.Thread(
        target=_extraction_thread,
        args=(chat_id, url, n, status_id, ts),
        daemon=True
    )
    t.start()

# ================= polling =================
def handle_update(u):
    try:
        if "message" in u:
            m = u["message"]
            if m.get("text"): handle_text(m["chat"]["id"], m["text"], m["message_id"])
        elif "callback_query" in u:
            cq = u["callback_query"]
            tg("answerCallbackQuery", data={"callback_query_id": cq["id"]})
            handle_callback(cq["message"]["chat"]["id"], cq.get("data",""), cq["message"]["message_id"])
    except Exception as e:
        print("[upd] " + str(e))

def poll():
    print("[*] polling started")
    me = tg("getMe")
    if me.get("ok"): print("[*] bot: @" + me["result"].get("username", "?"))
    else: print("[!] token invalid?")

    offset = 0
    while True:
        try:
            r = TG_SESSION.get(API + "/getUpdates",
                               params={"offset": offset, "timeout": 25},
                               timeout=35)
            data = r.json()
            if not data.get("ok"): time.sleep(3); continue
            for u in data.get("result", []):
                offset = u["update_id"] + 1
                handle_update(u)
        except requests.RequestException: time.sleep(2)
        except KeyboardInterrupt: print("\n[*] stopped"); break
        except Exception as e: print("[poll] " + str(e)); time.sleep(2)

if __name__ == "__main__":
    poll()
