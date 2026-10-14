#!/usr/bin/python
import sys, os, json, re, base64, subprocess, tempfile
from urllib.parse import urljoin, urlparse, quote

sys.path.append('..')

from base.spider import Spider


# ============ 纯 Python AES-128-CBC 解密 ============
_Sbox = [
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
_InvSbox = [_Sbox.index(i) for i in range(256)]
_Rcon = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36]

def _xt(a):
    return ((a << 1) ^ 0x1b) & 0xff if a & 0x80 else a << 1

def _mul(a, b):
    p = 0
    for _ in range(8):
        if b & 1: p ^= a
        a = _xt(a); b >>= 1
    return p

def _expand_key(key):
    w = [list(key[i*4:(i+1)*4]) for i in range(4)]
    for i in range(4, 44):
        t = list(w[i-1])
        if i % 4 == 0:
            t = [_Sbox[t[1]], _Sbox[t[2]], _Sbox[t[3]], _Sbox[t[0]]]
            t[0] ^= _Rcon[i//4 - 1]
        w.append([w[i-4][j] ^ t[j] for j in range(4)])
    return w

def _add_rk(state, w, rnd):
    for c in range(4):
        for r in range(4):
            state[r][c] ^= w[rnd*4 + c][r]

def _inv_shift(state):
    for r in range(1, 4):
        state[r] = state[r][-r:] + state[r][:-r]

def _inv_sub(state):
    for r in range(4):
        for c in range(4):
            state[r][c] = _InvSbox[state[r][c]]

def _inv_mix(state):
    for c in range(4):
        a = [state[r][c] for r in range(4)]
        state[0][c] = _mul(a[0],14) ^ _mul(a[1],11) ^ _mul(a[2],13) ^ _mul(a[3],9)
        state[1][c] = _mul(a[0],9) ^ _mul(a[1],14) ^ _mul(a[2],11) ^ _mul(a[3],13)
        state[2][c] = _mul(a[0],13) ^ _mul(a[1],9) ^ _mul(a[2],14) ^ _mul(a[3],11)
        state[3][c] = _mul(a[0],11) ^ _mul(a[1],13) ^ _mul(a[2],9) ^ _mul(a[3],14)

def _dec_block(blk, w):
    st = [[blk[r + 4*c] for c in range(4)] for r in range(4)]
    _add_rk(st, w, 10)
    for rnd in range(9, 0, -1):
        _inv_shift(st); _inv_sub(st); _add_rk(st, w, rnd); _inv_mix(st)
    _inv_shift(st); _inv_sub(st); _add_rk(st, w, 0)
    return bytes(st[r][c] for c in range(4) for r in range(4))

def aes_cbc_decrypt(data, key, iv):
    w = _expand_key(key)
    out = b""; prev = iv
    for i in range(0, len(data), 16):
        blk = data[i:i+16]
        dec = _dec_block(blk, w)
        out += bytes(a ^ b for a, b in zip(dec, prev))
        prev = blk
    pad = out[-1]
    if 1 <= pad <= 16 and out[-pad:] == bytes([pad]) * pad:
        out = out[:-pad]
    return out


class Spider(Spider):
    """MM热点（ommjs4.xxsxlz.top）大分类 + 子分类筛选版"""

    HOST = "https://ommjs4.xxsxlz.top"
    AES_KEY = b"a9yX32LpQvUt7wBc"
    AES_IV = b"N7cPk2Bv38hWqFzM"

    # 大分类 -> 子分类列表（type_id 格式: "大分类ID_子分类ID"，子分类用 filters 筛选）
    BIG_CATEGORIES = [
        {"type_id": "jk", "type_name": "日韩系列"},
        {"type_id": "gc", "type_name": "国产自拍"},
        {"type_id": "cm", "type_name": "传媒厂牌"},
        {"type_id": "hl", "type_name": "黑料吃瓜"},
        {"type_id": "jp", "type_name": "精品专区"},
        {"type_id": "zq", "type_name": "猎奇专区"},
    ]

    # 大分类 -> 子分类映射（filters 筛选值 = 子分类 API ID）
    SUB_MAP = {
        "jk": [
            {"n": "日韩超清", "v": "2445"},
            {"n": "日韩精品", "v": "2444"},
            {"n": "日韩无码", "v": "2443"},
            {"n": "异族风情", "v": "2442"},
            {"n": "中文字幕", "v": "2411"},
            {"n": "华语AV",   "v": "2428"},
        ],
        "gc": [
            {"n": "国产自拍", "v": "2440"},
            {"n": "国产精品", "v": "2429"},
            {"n": "自拍偷拍", "v": "2433"},
            {"n": "探花约炮", "v": "2438"},
            {"n": "主播诱惑", "v": "2439"},
            {"n": "主播网红", "v": "2420"},
            {"n": "抖音短片", "v": "2435"},
            {"n": "偷拍偷窥", "v": "2437"},
            {"n": "国产盗摄", "v": "2425"},
        ],
        "cm": [
            {"n": "传媒剧情", "v": "2434"},
            {"n": "麻豆视频", "v": "2410"},
            {"n": "91制片厂", "v": "2409"},
            {"n": "天美传媒", "v": "2408"},
            {"n": "蜜桃传媒", "v": "2407"},
            {"n": "星空传媒", "v": "2405"},
            {"n": "开心鬼传媒", "v": "2395"},
            {"n": "MINI传媒", "v": "2397"},
            {"n": "大象传媒", "v": "2396"},
            {"n": "乌鸦传媒", "v": "2401"},
            {"n": "兔子先生", "v": "2400"},
            {"n": "玩偶姐姐", "v": "2398"},
            {"n": "杏吧原创", "v": "2399"},
            {"n": "糖心vlog", "v": "2393"},
            {"n": "海角社区", "v": "2403"},
            {"n": "成人头条", "v": "2402"},
            {"n": "皇家华人", "v": "2406"},
            {"n": "焦点影业", "v": "2404"},
            {"n": "国产厂牌", "v": "2422"},
        ],
        "hl": [
            {"n": "网曝吃瓜", "v": "2436"},
            {"n": "网曝黑料", "v": "2423"},
            {"n": "网曝门",   "v": "2413"},
            {"n": "吃瓜黑料", "v": "2431"},
            {"n": "黑料吃瓜", "v": "2427"},
        ],
        "jp": [
            {"n": "精品推荐", "v": "2415"},
            {"n": "女优明星", "v": "2441"},
            {"n": "国产色情", "v": "2414"},
            {"n": "丝袜制服", "v": "2421"},
            {"n": "国内换脸", "v": "2432"},
        ],
        "zq": [
            {"n": "SM调教",   "v": "2412"},
            {"n": "群交多P",  "v": "2419"},
            {"n": "强奸迷奸", "v": "2424"},
            {"n": "直播裸聊", "v": "2430"},
            {"n": "国产裸聊", "v": "2426"},
            {"n": "学生萝莉", "v": "2418"},
            {"n": "萝莉社",   "v": "2392"},
            {"n": "原创乱伦", "v": "2387"},
            {"n": "乱伦毁三观","v": "2383"},
            {"n": "偷情少妇", "v": "2384"},
            {"n": "反差母狗", "v": "2390"},
            {"n": "野战车震", "v": "2389"},
            {"n": "野外露出", "v": "2388"},
            {"n": "粉穴学妹", "v": "2386"},
            {"n": "撸管必看", "v": "2385"},
            {"n": "psycho",  "v": "2394"},
            {"n": "性视界",   "v": "2391"},
        ],
    }

    # 大分类默认子分类（进入大分类时默认选第一个子分类）
    DEFAULT_SUB = {
        "jk": "2444",  # 日韩精品（最大）
        "gc": "2440",  # 国产自拍
        "cm": "2434",  # 传媒剧情
        "hl": "2423",  # 网曝黑料
        "jp": "2415",  # 精品推荐
        "zq": "2412",  # SM调教
    }

    def getName(self):
        return "MM热点"

    def init(self, extend=""):
        self.host = self.HOST
        self.api = self.host + "/api"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": self.host + "/",
        }
        self.session = None
        self.proxy = None
        self.ext = {}
        self.classes = list(self.BIG_CATEGORIES)
        self._key_w = _expand_key(self.AES_KEY)
        self.filters = {}
        # 构建每个大分类的筛选器
        for bc in self.BIG_CATEGORIES:
            tid = bc["type_id"]
            subs = self.SUB_MAP.get(tid, [])
            if subs:
                self.filters[tid] = [{
                    "key": "sub",
                    "name": "分类",
                    "value": subs,
                }]

    # ---------- 网络 ----------
    def _init_session(self):
        if self.session is not None:
            return
        import requests as _req
        self.session = _req.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False
        self._probe_proxy()
        if self.proxy:
            self.session.proxies.update(self.proxy)

    def _probe_proxy(self):
        p = self.ext.get("proxy", "") if isinstance(self.ext, dict) else ""
        if p:
            if not p.startswith("http"):
                p = "http://" + p
            self.proxy = {"http": p, "https": p}
            return
        for port in ["7890", "7891", "1080", "1087", "10809", "24780",
                     "2333", "6153", "16666", "20170", "9090", "7070"]:
            try:
                t = "http://127.0.0.1:" + port
                self.session.get("http://www.gstatic.com/generate_204",
                                 timeout=1, proxies={"http": t, "https": t})
                self.proxy = {"http": t, "https": t}
                return
            except Exception:
                pass
        for k in ["HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy",
                   "ALL_PROXY", "all_proxy"]:
            v = os.environ.get(k)
            if v:
                if not v.startswith("http"):
                    v = "http://" + v
                self.proxy = {"http": v, "https": v}
                return

    def _dbg(self, msg):
        try:
            with open("/sdcard/debug_mm.txt", "a", encoding="utf-8") as f:
                f.write(f"{msg}\n")
        except Exception:
            pass

    def _decrypt(self, cipher_b64):
        try:
            ct = base64.b64decode(cipher_b64)
        except Exception:
            return {}
        # 方案1: openssl
        try:
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as f:
                f.write(ct)
                tmp = f.name
            try:
                cmd = ('openssl enc -aes-128-cbc -d -in ' + tmp +
                       ' -K ' + self.AES_KEY.hex() + ' -iv ' + self.AES_IV.hex())
                r = subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
                if r.returncode == 0 and r.stdout:
                    return json.loads(r.stdout.decode("utf-8"))
            finally:
                try:
                    os.unlink(tmp)
                except Exception:
                    pass
        except Exception:
            pass
        # 方案2: 纯 Python
        try:
            pt = aes_cbc_decrypt(ct, self.AES_KEY, self.AES_IV)
            return json.loads(pt.decode("utf-8"))
        except Exception:
            pass
        return {}

    def _req(self, path):
        self._init_session()
        try:
            r = self.session.get(self.api + path, timeout=15,
                                 proxies=self.session.proxies or None)
            j = r.json()
            if "cipher" in j:
                d = self._decrypt(j["cipher"])
                return d.get("data", d) if isinstance(d, dict) else d
            return j
        except Exception as e:
            self._dbg(f"REQ {path}: {e}")
            return {}

    # ---------- 数据转换 ----------
    def _vod(self, v):
        return {
            "vod_id": str(v.get("id", "")),
            "vod_name": (v.get("title") or "").strip(),
            "vod_pic": v.get("cover_url") or "",
            "vod_remarks": f"{v.get('hits', 0)}热度" if v.get("hits") else "",
        }

    def _fetch_videos(self, cid, pg):
        """获取分类视频，兼容 None"""
        d = self._req(f"/videos?category_id={cid}&page={pg}&ps=20")
        if not isinstance(d, dict):
            d = {}
        lst = d.get("list") or []
        pages = int(d.get("pages") or 1)
        total = int(d.get("total") or 0)
        return [self._vod(v) for v in lst if isinstance(v, dict)], pages, total

    # ---------- 六接口 ----------
    def homeContent(self, filter=False):
        self._init_session()
        _home_pc = max(1, 0 + 1)
        return {"class": self.classes, "filters": self.filters,
                "list": [], "page": 1, "pagecount": _home_pc, "limit": 20, "total": 0}

    def homeVideoContent(self):
        self._init_session()
        d = self._req("/videos?page=1&ps=20")
        if not isinstance(d, dict):
            d = {}
        lst = d.get("list") or []
        return {"list": [self._vod(v) for v in lst if isinstance(v, dict)]}

    def categoryContent(self, tid, pg, filter=None, extend=None):
        """
        tid = 大分类 key（如 "jk"）
        extend.sub = 子分类 ID（如 "2444"）
        """
        self._init_session()
        pg = int(pg) if str(pg).isdigit() else 1

        # 确定实际请求的分类 ID
        cid = ""
        if extend:
            if isinstance(extend, dict):
                cid = extend.get("sub", "")
            elif isinstance(extend, str):
                try:
                    ed = json.loads(extend)
                    if isinstance(ed, dict):
                        cid = ed.get("sub", "")
                except Exception:
                    pass

        # 未选子分类时用默认
        if not cid and tid in self.DEFAULT_SUB:
            cid = self.DEFAULT_SUB[tid]
        if not cid:
            return {"page": pg, "pagecount": max(pg, 1), "limit": 20, "total": 0, "list": []}

        self._dbg(f"categoryContent tid={tid} sub={cid} pg={pg}")
        items, pages, total = self._fetch_videos(cid, pg)
        return {"page": pg, "pagecount": max(1, pages),
                "limit": len(items) or 20, "total": total, "list": items}

    def detailContent(self, ids):
        self._init_session()
        if isinstance(ids, str):
            ids = [ids]
        out = []
        for vid in ids:
            if not vid:
                continue
            d = self._req(f"/movie?id={vid}")
            info = d.get("info", {}) if isinstance(d, dict) else {}
            out.append({
                "vod_id": str(vid),
                "vod_name": (info.get("title") or "").strip(),
                "vod_pic": info.get("cover_url", ""),
                "vod_remarks": f"{info.get('hits', 0)}热度" if info.get("hits") else "",
                "vod_content": info.get("category", ""),
                "vod_play_from": "MM热点",
                "vod_play_url": f"播放${vid}",
            })
        return {"list": out}

    def searchContent(self, key, quick=None, pg="1"):
        self._init_session()
        pg = int(pg) if str(pg).isdigit() else 1
        d = self._req(f"/videos?kw={quote(key)}&page={pg}&ps=20")
        if not isinstance(d, dict):
            d = {}
        lst = d.get("list") or []
        pages = int(d.get("pages") or 1)
        return {"page": pg, "pagecount": max(1, pages),
                "limit": len(lst) or 20, "total": 0,
                "list": [self._vod(v) for v in lst if isinstance(v, dict)]}

    def _validate_media(self, url):
        try:
            r = self.session.get(url, headers={"User-Agent": self.headers["User-Agent"]},
                                 timeout=8, stream=True,
                                 proxies=self.session.proxies or None)
            data = next(r.iter_content(2048), b"")
            if not r.ok:
                return False
            if ".m3u8" in url:
                return b"#EXTM3U" in data
            return True
        except Exception:
            return False

    def playerContent(self, flag, id, vipFlags=None):
        self._init_session()
        vid = str(id)
        if not vid:
            return {"url": "", "header": {}}
        d = self._req(f"/movie?id={vid}")
        info = d.get("info", {}) if isinstance(d, dict) else {}
        play = info.get("play_url") or ""
        if play and play.startswith("http") and self._validate_media(play):
            return {"parse": 0, "url": play,
                    "header": {"User-Agent": self.headers["User-Agent"],
                               "Referer": self.host + "/"}}
        self._dbg(f"播放门禁失败 vid={vid}")
        return {"url": "", "header": {}}

    def localProxy(self, params):
        url = params.get("url", "")
        if not url:
            return None
        self._init_session()
        try:
            r = self.session.get(url, timeout=10,
                                 headers={"User-Agent": self.headers["User-Agent"],
                                          "Referer": self.host + "/"},
                                 proxies=self.session.proxies or None)
            content = r.content
            if not content:
                return None
            return {"content": content,
                    "mime": r.headers.get("Content-Type", "application/octet-stream")}
        except Exception:
            return None

    def proxyPic(self, params):
        import base64 as b64
        try:
            url = b64.b64decode(params.get("url", "")).decode("utf-8")
            self._init_session()
            r = self.session.get(url, timeout=15,
                                 headers={"User-Agent": self.headers["User-Agent"],
                                          "Referer": self.host + "/"},
                                 proxies=self.session.proxies or None)
            data = r.content or b""
            if not data:
                return [404, "text/plain", ""]
            return [200, r.headers.get("Content-Type", "image/jpeg"), data]
        except Exception:
            return [500, "text/plain", "error"]