#!/usr/bin/python
from base.spider import Spider
import re
import ssl
import json
import time
import base64
import os
import ast
import hashlib
import glob
import warnings
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, unquote, urlparse

import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

_CIPHERS = 'TLS_AES_128_GCM_SHA256:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_256_GCM_SHA384:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES128-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:AES128-SHA:AES256-SHA'
_PUBLISH = ('https://x99dh.pro/', 'https://x99dh.cc/')
_DOMAINS = ['jae1.nl', 'ja88.net']
_PIC_CDN = 'https://spic1-66.piccdn1.cc'
_LOGO = _PIC_CDN + '/assets-cdn.jable.tv/assets/images/logo.png'
_PIC_HOSTS = ('spic1-66.piccdn1.cc', 'piccdn1.cc', 'assets-cdn.jable.tv')

_CACHE_TTL = 1800
_WRITE_BACK = True
_FASTEST_N = 2
_PROBE_BUDGET = 12.0
_SHELL_CFG = {
    'com.fongmi.android.tv': ('shared_prefs/com.fongmi.android.tv_preferences.xml',),
    'com.fongmi.vodplus': ('shared_prefs/com.fongmi.vodplus_preferences.xml',),
    'com.example.peekpro': ('files/hive/setting.hive',),
    'com.example.peekpili': ('files/hive/setting.hive',),
}
_SHELL_CFG_GLOB = ('shared_prefs/*.xml', 'files/hive/*.hive', 'app_flutter/*.json', 'files/*.json')

_SH_T = {'t': None}
_SH_ST = {'cur': '', 'keep': False, 'seq': 0}


class _CFAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.sc = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        try:
            self.sc.check_hostname = False
            self.sc.verify_mode = ssl.CERT_NONE
        except Exception:
            pass
        try:
            self.sc.set_ciphers(_CIPHERS)
        except Exception:
            pass
        try:
            self.sc.set_ecdh_curve('prime256v1')
        except Exception:
            pass
        super(_CFAdapter, self).__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self.sc
        return super(_CFAdapter, self).init_poolmanager(*args, **kwargs)


class Spider(Spider):
    ua = ('Mozilla/5.0 (Linux; Android 16; 2407FRK8EC Build/BP2A.250605.031.A3) '
          'AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/137.0.7151.115 Mobile Safari/537.36')

    TAG_GROUPS = {
        "衣著": [("黑丝", "black-pantyhose"), ("过膝袜", "knee-socks"), ("运动装", "sportswear"),
                 ("肉丝", "flesh-toned-pantyhose"), ("丝袜", "pantyhose"), ("眼镜娘", "glasses"),
                 ("兽耳", "kemonomimi"), ("渔网", "fishnets"), ("水着", "swimsuit"),
                 ("校服", "school-uniform"), ("旗袍", "cheongsam"), ("婚纱", "wedding-dress"),
                 ("女仆", "maid"), ("和服", "kimono"), ("吊带袜", "stockings"),
                 ("兔女郎", "bunny-girl"), ("Cosplay", "Cosplay")],
        "身材": [("黑肉", "suntan"), ("长身", "tall"), ("软体", "flexible-body"),
                 ("贫乳", "small-tits"), ("美腿", "beautiful-leg"), ("美尻", "beautiful-butt"),
                 ("纹身", "tattoo"), ("短发", "short-hair"), ("白虎", "hairless-pussy"),
                 ("熟女", "mature-woman"), ("巨乳", "big-tits"), ("少女", "girl"),
                 ("娇小", "dainty")],
        "交合": [("颜射", "facial"), ("脚交", "footjob"), ("肛交", "anal-sex"),
                 ("痉挛", "spasms"), ("潮吹", "squirting"), ("深喉", "deep-throat"),
                 ("接吻", "kiss"), ("口爆", "cum-in-mouth"), ("口交", "blowjob"),
                 ("乳交", "tit-wank"), ("中出", "creampie")],
        "玩法": [("露出", "outdoor"), ("集团进犯", "gang-intrusion"), ("进犯", "intrusion"),
                 ("调教", "tune"), ("捆绑", "bondage"), ("瞬间插入", "quickie"),
                 ("痴汉", "chikan"), ("痴女", "chizyo"), ("男M", "masochism-guy"),
                 ("泥醉", "crapulence"), ("泡姬", "soapland"), ("母乳", "breast-milk"),
                 ("放尿", "piss"), ("按摩", "massage"), ("多P", "groupsex"),
                 ("刑具", "grip"), ("凌辱", "insult"), ("一日十回", "10-times-a-day"),
                 ("3P", "3p")],
        "剧情": [("黑人", "black"), ("丑男", "ugly-man"), ("诱惑", "temptation"),
                 ("亲属", "kinship"), ("童贞", "virginity"), ("时间停止", "time-stop"),
                 ("复仇", "avenge"), ("年龄差", "age-difference"), ("巨汉", "giant"),
                 ("媚药", "love-potion"), ("夫目前犯", "sex-beside-husband"), ("出轨", "affair"),
                 ("催眠", "hypnosis"), ("偷拍", "private-cam"), ("下雨天", "rainy-day"),
                 ("NTR", "ntr")],
        "角色": [("风俗娘", "club-hostess-and-sex-worker"), ("医生", "doctor"), ("逃犯", "fugitive"),
                 ("护士", "nurse"), ("老师", "teacher"), ("空姐", "flight-attendant"),
                 ("球队经理", "team-manager"), ("未亡人", "widow"), ("搜查官", "detective"),
                 ("情侣", "couple"), ("家政妇", "housewife"), ("家庭教师", "private-teacher"),
                 ("偶像", "idol"), ("人妻", "wife"), ("主播", "female-anchor"),
                 ("OL", "ol")],
        "地点": [("魔镜号", "magic-mirror"), ("电车", "tram"), ("处女", "first-night"),
                 ("监狱", "prison"), ("温泉", "hot-spring"), ("洗浴场", "bathing-place"),
                 ("泳池", "swimming-pool"), ("汽车", "car"), ("厕所", "toilet"),
                 ("学校", "school"), ("图书馆", "library"), ("健身房", "gym-room"),
                 ("便利店", "store")],
        "杂项": [("录像", "video-recording"), ("处女作/引退作", "debut-retires"),
                 ("综艺", "variety-show"), ("节日主题", "festival"), ("感谢祭", "thanksgiving"),
                 ("4小时以上", "more-than-4-hours")],
    }

    SORT_VIDEOS = [
        {"n": "近期最佳", "v": "post_date_and_popularity"},
        {"n": "最近更新", "v": "post_date"},
        {"n": "最多观看", "v": "video_viewed"},
        {"n": "最高收藏", "v": "most_favourited"},
    ]
    SORT_HOT = [
        {"n": "所有时间", "v": "video_viewed"},
        {"n": "本月热门", "v": "video_viewed_month"},
        {"n": "本周热门", "v": "video_viewed_week"},
        {"n": "今日热门", "v": "video_viewed_today"},
    ]
    SORT_CATEGORY = [
        {"n": "预设排序", "v": "category_id"},
        {"n": "热度优先", "v": "avg_videos_popularity"},
        {"n": "最多影片", "v": "total_videos"},
    ]
    SORT_MODEL = [
        {"n": "热度优先", "v": "avg_videos_popularity"},
        {"n": "最近更新", "v": "last_content_date"},
        {"n": "最多影片", "v": "total_videos"},
        {"n": "名称顺序", "v": "title"},
    ]

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.name = 'Jable'
        self.base_url = 'https://jable1.nl'
        self.headers = {
            'User-Agent': self.ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.domains = ['https://' + d for d in _DOMAINS]
        self.session = None
        self._xs = None
        self._cache_time = 0
        self._cache_ttl = 1800
        self._url_cache = {}
        self._logo_cache = None
        self._model_pic_cache = {}

    def getName(self):
        return 'Jable'

    def init(self, extend=''):
        warnings.filterwarnings('ignore')
        now = time.time()
        if self.session is not None and (now - self._cache_time) < self._cache_ttl:
            return
        s = requests.Session()
        try:
            a = _CFAdapter()
            s.mount('https://', a)
            s.mount('http://', a)
        except Exception:
            pass
        s.headers.update(self.headers)
        try:
            s.cookies.set('x-index-auth', 'authed', domain='.' + self.base_url.split('//')[1], path='/')
        except Exception:
            pass
        self.session = s
        x = requests.Session()
        try:
            x.mount('https://', _CFAdapter())
            x.mount('http://', _CFAdapter())
        except Exception:
            pass
        self._xs = x
        _cached = self._load_cache()
        if _cached:
            self.domains = [d for d in _cached if d] + [d for d in self.domains if d not in _cached]
            self._set_host(self.domains[0])
            print('[Jable] 冷启动直读缓存池首: %s' % self.domains[0])
        self._probe()
        self._cache_time = now

    def _probe(self):
        start_ts = time.time()
        deadline = start_ts + _PROBE_BUDGET

        def left(d=2.0):
            return max(d, min(5.0, deadline - time.time()))

        def test(h):
            try:
                t0 = time.time()
                r = self.session.get(h + '/latest-updates/', timeout=left(),
                                     headers=self.headers, allow_redirects=True)
                if r.status_code == 200 and 'video-img-box' in r.text and not self._challenge(r.text):
                    return (time.time() - t0, h)
            except Exception:
                pass
            return None

        def probe_many(hs, w):
            try:
                with ThreadPoolExecutor(max_workers=w) as ex:
                    return list(ex.map(test, hs))
            except Exception:
                return [test(h) for h in hs]

        hosts = self.domains[:8]
        alive = sorted([x for x in probe_many(hosts, 8) if x], key=lambda x: x[0])
        if alive:
            best = [h for _, h in alive[:_FASTEST_N]]
            self._apply_hosts(best)
            print('[Jable] 优选最快 %d 域: %s' % (len(best), ', '.join(best)))
            self._persist_domains(best)
            self._save_cache(self.domains)
            return
        if time.time() > deadline:
            print('[Jable] 探活超时, 跳过发布页')
            return
        self._sh_toast('自愈中，请稍后...', True)
        try:
            fresh = self._publish_hosts(deadline)
            if fresh:
                print('[Jable] 发布页捞到域名: %d 个' % len(fresh))
                found = sorted([x for x in probe_many(fresh[:6], 6) if x], key=lambda x: x[0])
                best = [h for _, h in found[:_FASTEST_N]]
                if best:
                    self._persist_domains(best)
                    print('[Jable] 已写回源文件 _DOMAINS: %s' % ', '.join(best))
                    if time.time() - start_ts < 3.0:
                        time.sleep(3.0 - (time.time() - start_ts))
                    self._sh_toast('已满血复活，请重新加载源')
                    return
        except Exception:
            pass
        self._sh_cancel()
        print('[Jable] 探活失败, 保留默认域名: %s' % self.base_url)

    def _set_host(self, h):
        self.base_url = h.rstrip('/')
        self.headers['Referer'] = self.base_url + '/'
        try:
            if self.session:
                self.session.headers.update(self.headers)
                self.session.cookies.set('x-index-auth', 'authed',
                                         domain='.' + self.base_url.split('//')[1], path='/')
        except Exception:
            pass

    def _publish_hosts(self, deadline=None):
        """x99dh双导航站 encodedData(base64->urldecode->JSON) 提取Jable域名
        注意：发布页常返 5xx 但 body 完整，故只认 encodedData 不认状态码"""
        if deadline is None:
            deadline = time.time() + 8.0
        for pub in _PUBLISH:
            for ua in ('curl/8.0', self.ua):
                if time.time() > deadline:
                    break
                try:
                    r = self._xs.get(pub, headers={'User-Agent': ua},
                                     timeout=max(2.0, min(8.0, deadline - time.time())))
                    t = getattr(r, 'text', '') or ''
                    if 'encodedData' not in t:
                        continue
                    m = re.search(r'encodedData\s*=\s*["\']([A-Za-z0-9+/=]+)["\']', t)
                    if not m:
                        continue
                    raw = base64.b64decode(m.group(1) + '=' * (-len(m.group(1)) % 4))
                    data = json.loads(unquote(raw.decode('utf-8', 'ignore')))
                except Exception:
                    continue
                hosts, seen = [], set()
                for item in data if isinstance(data, list) else []:
                    if 'jable' not in str(item.get('name', '')).lower():
                        continue
                    for u in item.get('urls', []):
                        link = str(u.get('url') or '').strip().rstrip('/')
                        if link.endswith('/enter'):
                            link = link[:-len('/enter')]
                        if link.startswith('http') and 'x99dh' not in link and link not in seen:
                            seen.add(link)
                            hosts.append(link)
                if hosts:
                    return hosts
        return []

    def _sh_toast(self, msg, keep=False):
        try:
            from java import jclass, dynamic_proxy
            from java.lang import Runnable
        except Exception:
            return
        _SH_ST['cur'] = msg or ''
        _SH_ST['keep'] = bool(keep)
        _SH_ST['seq'] += 1
        seq = _SH_ST['seq']
        try:
            AT = jclass('java.lang.Class').forName('android.app.ActivityThread')
            cur = AT.getMethod('currentActivityThread').invoke(None)
            mf = AT.getDeclaredField('mActivities')
            mf.setAccessible(True)
            acts = mf.get(cur)
            act = None
            for k in acts.keySet().toArray():
                rec = acts.get(k)
                pf = rec.getClass().getDeclaredField('paused')
                pf.setAccessible(True)
                if not pf.getBoolean(rec):
                    af = rec.getClass().getDeclaredField('activity')
                    af.setAccessible(True)
                    act = af.get(rec)
                    break
            if act is None:
                return
            Toast = jclass('android.widget.Toast')
            h = jclass('android.os.Handler')(jclass('android.os.Looper').getMainLooper())
        except Exception:
            return
        box = {'act': act, 'T': Toast, 'h': h, 'seq': seq, 'i': 0}

        class R(dynamic_proxy(Runnable)):
            def run(s):
                if _SH_ST['seq'] != box['seq']:
                    return
                old = _SH_T.get('t')
                if old is not None:
                    try:
                        old.cancel()
                    except Exception:
                        pass
                try:
                    t = box['T'].makeText(box['act'], _SH_ST['cur'], 1)
                    t.show()
                    _SH_T['t'] = t
                except Exception:
                    pass
                if keep and box['i'] < 5:
                    box['i'] += 1
                    _SH_ST['seq'] += 1
                    box['seq'] = _SH_ST['seq']
                    try:
                        box['h'].postDelayed(R(), 2400)
                    except Exception:
                        pass

        try:
            box['h'].post(R())
        except Exception:
            try:
                box['act'].runOnUiThread(R())
            except Exception:
                pass

    def _sh_cancel(self):
        _SH_ST['keep'] = False
        _SH_ST['seq'] += 1
        try:
            t = _SH_T.get('t')
            if t is not None:
                t.cancel()
                _SH_T['t'] = None
        except Exception:
            pass

    @classmethod
    def _pkg_of(cls):
        try:
            import inspect
            f = inspect.getfile(cls)
        except Exception:
            f = ''
        m = re.search(r'/(?:data/data|data/user/0)/([^/]+)/', f or '')
        return m.group(1) if m else ''

    @classmethod
    def _shell_json_paths(cls):
        pkg = cls._pkg_of()
        if not pkg:
            return []
        bases = ['/data/data/%s/' % pkg, '/data/user/0/%s/' % pkg]
        rels = list(_SHELL_CFG.get(pkg, ())) + list(_SHELL_CFG_GLOB)
        out = []
        for base in bases:
            for rel in rels:
                if '*' in rel:
                    try:
                        out += glob.glob(base + rel)
                    except Exception:
                        pass
                else:
                    p = base + rel
                    try:
                        if os.path.isfile(p):
                            out.append(p)
                    except Exception:
                        pass
        seen, uniq = set(), []
        for x in out:
            if x not in seen:
                seen.add(x)
                uniq.append(x)
        jsons = []
        for f in uniq:
            try:
                txt = open(f, 'rb').read().decode('utf-8', 'ignore')
            except Exception:
                continue
            jsons += re.findall(r'(file://[^<\s"]+\.json)', txt)
            jsons += re.findall(r'"(/storage/[^"\s]+?\.json)"', txt)
            for m in re.findall(r'\[(\{"id":"[0-9]+".*?"isLocal":true\})\]', txt):
                jsons += [u for u in re.findall(r'"url":"([^"]+)"', m) if u.endswith('.json')]
        res = []
        for v in jsons:
            if v.startswith('file://'):
                v = v[7:]
            if v.startswith('http'):
                continue
            if not v.startswith('/'):
                v = '/storage/emulated/0/' + v
            if v not in res:
                res.append(v)
        return [(v, os.path.dirname(v) or '/') for v in res]
    @classmethod
    def _file_md5(cls, p):
        h = hashlib.md5()
        with open(p, 'rb') as f:
            for b in iter(lambda: f.read(65536), b''):
                h.update(b)
        return h.hexdigest()

    @classmethod
    def _shell_site_py(cls, paths=None):
        out = []
        for j, jd in (cls._shell_json_paths() if paths is None else paths):
            if not os.path.isfile(j):
                continue
            try:
                d = json.load(open(j, encoding='utf-8'))
            except Exception:
                continue
            for site in d.get('sites', []):
                api = site.get('api')
                if not isinstance(api, str) or not api.endswith('.py') or api.startswith('http'):
                    continue
                p = os.path.normpath(os.path.join(jd, api))
                if p not in out:
                    out.append(p)
        return out

    @classmethod
    def _locate_by_shell(cls, paths=None):
        f = cls._runtime_file()
        rt = cls._runtime_name()
        cands = cls._shell_site_py(paths)
        for p in cands:
            try:
                if rt and os.path.basename(p).strip() == rt and os.path.isfile(p):
                    return p
            except Exception:
                pass
        if not f or not os.path.isfile(f):
            return None
        try:
            mine = cls._file_md5(f)
        except Exception:
            return None
        hits = [p for p in cands if os.path.isfile(p) and cls._file_md5(p) == mine]
        return hits[0] if len(hits) == 1 else None


    @classmethod
    def _runtime_file(cls):
        for get in (lambda: __file__,
                    lambda: __import__('sys').modules[cls.__module__].__file__,
                    lambda: __import__('inspect').getfile(cls)):
            try:
                p = get()
            except Exception:
                p = ''
            if p:
                return unquote(str(p)).strip()
        return ''

    @classmethod
    def _runtime_name(cls):
        f = cls._runtime_file()
        return os.path.basename(f).strip() if f else ''

    @classmethod
    def _locate_source(cls):
        if '_SRC_CACHE' in cls.__dict__:
            return cls._SRC_CACHE
        cls._SRC_CACHE = ''
        try:
            paths = cls._shell_json_paths()
            r = cls._locate_by_shell(paths) if paths else None
        except Exception:
            r = None
        cls._SRC_CACHE = r or ''
        return cls._SRC_CACHE or None

    @classmethod
    def _cache_dir(cls):
        f = cls._runtime_file()
        d = os.path.dirname(f) if f else ''
        if d and os.path.isdir(d):
            return d
        return ''

    @classmethod
    def _cache_path(cls):
        d = cls._cache_dir()
        return os.path.join(d, '_pooldns_' + (cls._runtime_name() or 'fs') + '.json') if d else ''

    @classmethod
    def _load_cache(cls):
        p = cls._cache_path()
        if not p:
            return []
        try:
            d = json.load(open(p, encoding='utf-8'))
            if d.get('name') != (cls._runtime_name() or 'fs'):
                return []
            ts = d.get('ts', 0)
            if time.time() - ts >= _CACHE_TTL:
                return []
            f = cls._runtime_file()
            if f and os.path.isfile(f):
                try:
                    if d.get('md5') != cls._file_md5(f):
                        print('[Jable] 缓存失效: 源内容已变更')
                        return []
                except Exception:
                    pass
            return [x for x in d.get('hosts', []) if x]
        except Exception:
            pass
        return []

    @classmethod
    def _save_cache(cls, hosts, src=None):
        p = cls._cache_path()
        if not p:
            return
        try:
            if src is None:
                src = cls.__dict__.get('_SRC_CACHE') or ''
            f = cls._runtime_file()
            md5 = ''
            try:
                if f and os.path.isfile(f):
                    md5 = cls._file_md5(f)
            except Exception:
                md5 = ''
            d = os.path.dirname(p)
            if d:
                os.makedirs(d, exist_ok=True)
            tmp = p + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as fh:
                json.dump({'name': (cls._runtime_name() or 'fs'), 'ts': time.time(),
                           'src': src, 'md5': md5, 'hosts': list(hosts)}, fh)
            os.replace(tmp, p)
        except Exception:
            pass

    @classmethod
    def _persist_domains(cls, hosts):
        if not _WRITE_BACK or not hosts:
            return False
        try:
            src = cls._locate_source()
        except Exception:
            src = None
        if not src:
            print('[Jable] 写回跳过: 未定位到源文件真身')
            return False
        try:
            content = open(src, encoding='utf-8').read()
            i = content.find('_DOMAINS = [')
            j = content.find(']', i)
            if i < 0 or j < 0:
                print('[Jable] 写回跳过: 源内无 _DOMAINS 块 ->', src)
                return False
            names = []
            for h in hosts:
                n = h.rstrip('/').split('://')[-1].split('/')[0]
                if n and n not in names:
                    names.append(n)
            if not names:
                return False
            body = (',\n' + ' ' * 12).join("'%s'" % n for n in names)
            new_block = '_DOMAINS = [\n' + ' ' * 12 + body + ']'
            new_content = content[:i] + new_block + content[j + 1:]
            if new_content == content:
                print('[Jable] 写回跳过: 域名无变化')
                return False
            try:
                tree = ast.parse(new_content)
            except SyntaxError:
                print('[Jable] 写回失败: 语法错误')
                return False
            ok = False
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name) and t.id == '_DOMAINS':
                            ok = isinstance(node.value, ast.List)
            if not ok:
                print('[Jable] 写回失败: _DOMAINS 结构校验未过')
                return False
            tmp = src + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                f.write(new_content)
            os.replace(tmp, src)
            print('[Jable] 写回成功: _DOMAINS ->', names)
            return True
        except Exception as e:
            print('[Jable] 写回失败(不影响使用): %r' % e)
            return False

    def _apply_hosts(self, best):
        for h in reversed(best):
            if h in self.domains:
                self.domains.remove(h)
            self.domains.insert(0, h)
        if best:
            self._set_host(best[0])

    @staticmethod
    def _challenge(text):
        low = (text or '').lower()
        return ('cf-mitigated' in low or 'challenge-platform' in low or
                'challenge-error-text' in low or '<title>just a moment' in low or
                'enable javascript and cookies' in low)

    def _bare(self, url, timeout=15):
        try:
            r = self.session.get(url, headers=self.headers, timeout=timeout, verify=False)
            if r.status_code == 200 and r.text and not self._challenge(r.text):
                return r.text
        except Exception:
            pass
        return ''

    def _shell(self, url, timeout=20):
        try:
            r = self.fetch(url, headers=self.headers, timeout=timeout)
            t = r if isinstance(r, str) else getattr(r, 'text', '')
            if t and not self._challenge(t):
                return t
        except Exception:
            pass
        return ''

    def _reader(self, url):
        gid = 'curl/8.0'
        base = 'https://r.jina.ai/' + url
        attempts = [
            lambda: self._xs.get(base, headers={'User-Agent': gid, 'Accept': 'text/plain', 'X-Return-Format': 'html'}, timeout=35),
            lambda: self._xs.post('https://r.jina.ai/', json={'url': url}, headers={'User-Agent': gid, 'Accept': 'application/json', 'Content-Type': 'application/json'}, timeout=35),
            lambda: self._xs.get(base, headers={'User-Agent': gid, 'Accept': 'text/plain'}, timeout=35),
            lambda: self.fetch(base, headers={'User-Agent': gid, 'Accept': 'text/plain'}, timeout=35),
        ]
        for fn in attempts:
            try:
                r = fn()
                t = r if isinstance(r, str) else getattr(r, 'text', '')
                if not t:
                    continue
                if t.lstrip().startswith('{'):
                    try:
                        o = json.loads(t)
                        c = (o.get('data') or {}).get('content') or ''
                        if c:
                            t = 'URL Source: %s\n\nMarkdown Content:\n%s' % ((o.get('data') or {}).get('url') or url, c)
                    except Exception:
                        pass
                if self._challenge(t):
                    continue
                low = t.lower()
                if '<html' in low or 'markdown content:' in low:
                    return t
            except Exception:
                continue
        return ''

    def _webview(self, url):
        for name in ('render', 'renderUrl', 'webview', 'webView', 'loadWebView',
                     'openWebView', 'getHtmlByWebView', 'webViewFetch', 'renderFetch'):
            fn = getattr(self, name, None)
            if not callable(fn):
                continue
            for args, kw in (((url,), {'headers': self.headers, 'timeout': 60}), ((url,), {}), ((url,),)):
                try:
                    v = fn(*args, **kw)
                    t = v if isinstance(v, str) else getattr(v, 'text', '') or ''
                    if isinstance(v, dict):
                        for k in ('html', 'content', 'body', 'text'):
                            if isinstance(v.get(k), str) and v.get(k):
                                t = v[k]
                    if t and not self._challenge(t):
                        return t
                except TypeError:
                    continue
                except Exception:
                    break
        return ''

    def _replace_host(self, url):
        cur = re.match(r'https?://([^/]+)', url or '')
        return url if not cur else url.replace('https://' + cur.group(1), self.base_url, 1)

    def _get(self, url, timeout=15):
        url = self._replace_host(url)
        t = self._bare(url, timeout)
        if t:
            return t
        t = self._shell(url)
        if t:
            return t
        t = self._reader(url)
        if t:
            return t
        for h in self.domains[1:5]:
            try:
                alt = re.sub(r'https?://[^/]+', h, url, count=1)
                r = self.session.get(alt, headers=self.headers, timeout=10, verify=False)
                if r.status_code == 200 and r.text and not self._challenge(r.text):
                    self._set_host(h)
                    print('[Jable] 切换域名: %s' % h)
                    return r.text
            except Exception:
                continue
        return self._webview(url)

    def _request(self, path_or_url, retry=1):
        """统一请求入口：维护页/跳转页自动重探域名并重试"""
        html = ''
        for attempt in range(retry + 1):
            url = path_or_url if str(path_or_url).startswith('http') \
                else self.base_url + '/' + str(path_or_url).lstrip('/')
            html = self._get(url)
            if html and '站点维护中' not in html and '即将跳转到导航页面' not in html:
                return html
            if attempt < retry:
                print('[Jable] 请求失败, 重探域名重试: %s' % url[:60])
                self._cache_time = 0
                self.session = None
                self.init('')
        return html or ''

    @staticmethod
    def _int(v):
        try:
            n = int(str(v).strip())
            return n if n > 0 else 1
        except Exception:
            return 1

    @staticmethod
    def _fix(u):
        if not u:
            return ''
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return _PIC_CDN + u
        return u

    @staticmethod
    def _high_pic(p):
        return re.sub(r'/320x180/1\.(?:jpe?g|webp|png)(?:\?.*)?$', '/preview.jpg', p or '', flags=re.I)

    def _to_path(self, url):
        path = urlparse(url).path.strip('/') if str(url).startswith('http') else str(url).strip('/')
        return path.lstrip('/')

    def _cat_url(self, path, pg, ext=None, sort_key='sort'):
        base = str(path).rstrip('/')
        url = base + '/' if self._int(pg) == 1 else base + '/' + str(self._int(pg)) + '/'
        sort = ''
        if ext and isinstance(ext, dict):
            sort = str(ext.get(sort_key) or '')
        if sort:
            url += '?sort_by=' + quote(sort, safe='')
        return url

    def _pagecount(self, html, path):
        try:
            nums = [int(n) for n in re.findall(r'href="[^"]*' + re.escape(path) + r'/(\d+)/"', html or '')]
            return max(nums) if nums else 0
        except Exception:
            return 0

    def _wrap(self, html, page, path):
        videos = self._parse_video_grid(html)
        pc = self._pagecount(html, path)
        if pc <= 0:
            pc = page if not videos else page + 1
        return {'list': videos, 'page': page, 'pagecount': max(pc, page), 'limit': 24, 'total': 999999}

    def homeContent(self, filter):
        video_sort = [{"key": "sort", "name": "排序", "value": self.SORT_VIDEOS}]
        classes = [
            {"type_id": "latest-updates", "type_name": "新片优先"},
            {"type_id": "hot", "type_name": "热度优先"},
            {"type_id": "categories", "type_name": "影片主题"},
            {"type_id": "models", "type_name": "选女优"},
        ]
        filters = {
            "默认": video_sort,
            "latest-updates": [],
            "hot": [{"key": "sort", "name": "热门时段", "value": self.SORT_HOT}],
            "categories": [{"key": "cat_sort", "name": "排序", "value": self.SORT_CATEGORY}],
            "models": [{"key": "model_sort", "name": "排序", "value": self.SORT_MODEL}],
        }
        for gname, subs in self.TAG_GROUPS.items():
            main_id = 'tags/' + subs[0][1]
            classes.append({"type_id": main_id, "type_name": gname})
            filters[main_id] = [{
                "key": "type",
                "name": gname,
                "value": [{"n": n, "v": 'tags/' + slug} for n, slug in subs],
            }] + video_sort
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        try:
            return {'list': self._parse_video_grid(self._request('latest-updates/'))}
        except Exception as e:
            print('[Jable] 首页内容获取失败 - %s' % e)
            return {'list': []}

    def categoryContent(self, tid, pg, filter, ext):
        page = self._int(pg)
        ext = ext if isinstance(ext, dict) else {}
        try:
            if ext.get('type'):
                tid = ext['type']
            if tid in ('latest-updates', 'hot'):
                path = tid
                url = self._cat_url(path, page, ext if tid == 'hot' else None)
                return self._wrap(self._request(url), page, path)
            if tid == 'categories':
                url = self._cat_url('categories/', 1, ext, sort_key='cat_sort')
                items = self._parse_theme_list(self._request(url))
                return {'list': items, 'page': 1, 'pagecount': 1, 'limit': 24, 'total': 999999}
            if tid == 'models':
                url = self._cat_url('models/', page, ext, sort_key='model_sort')
                html = self._request(url)
                items = self._parse_model_list(html)
                pc = self._pagecount(html, 'models')
                if pc <= 0:
                    pc = page if not items else page + 1
                return {'list': items, 'page': page, 'pagecount': max(pc, page), 'limit': 24, 'total': 999999}
            inner = tid if tid.startswith('http') else tid.rstrip('/')
            if not (inner.startswith('http') or inner.startswith(('videos/', 'models/', 'categories/', 'tags/'))):
                return {'list': [], 'page': page, 'pagecount': 1, 'limit': 24, 'total': 0}
            path = urlparse(inner).path.strip('/') if inner.startswith('http') else inner
            return self._wrap(self._request(self._cat_url(path, page, ext)), page, path)
        except Exception as e:
            print('[Jable] 分类爬取失败 - %s' % e)
            return {'list': [], 'page': page, 'pagecount': 1, 'limit': 24, 'total': 0}

    def _parse_video_grid(self, html):
        videos = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            seen = set()
            for card in soup.select('div.video-img-box'):
                try:
                    a = card.find('a', href=re.compile(r'/videos/'))
                    if not a:
                        continue
                    vod_id = self._to_path(a.get('href', ''))
                    if not vod_id or vod_id in seen:
                        continue
                    seen.add(vod_id)
                    title_el = card.select_one('h6.title a') or card.select_one('h6.title')
                    name = title_el.get_text(strip=True) if title_el else ''
                    img = card.find('img')
                    pic = ''
                    if img:
                        pic = img.get('data-src') or img.get('data-original') or img.get('src') or ''
                    pic = self._high_pic(self._fix(pic))
                    label = card.select_one('span.label')
                    duration = label.get_text(strip=True) if label else ''
                    views = ''
                    tip = card.select_one('p.sub-title')
                    if tip:
                        for node in tip.find_all('use'):
                            href = node.get('xlink:href') or node.get('href') or ''
                            if 'icon-eye' in href:
                                svg = node.parent
                                nxt = svg.find_next_sibling(text=True) if svg else None
                                if nxt:
                                    views = re.sub(r'[^\d]', '', str(nxt))
                                break
                        if not views:
                            m = re.search(r'\d[\d\s,.]*', tip.get_text())
                            if m:
                                views = re.sub(r'[^\d]', '', m.group(0))
                    remark = duration
                    if views:
                        remark = (duration + '👀' if duration else '👀') + views
                    videos.append({'vod_id': vod_id, 'vod_name': name or vod_id.split('/')[-1].upper(),
                                   'vod_pic': pic or _LOGO, 'vod_remarks': remark, 'vod_tag': 'video'})
                except Exception:
                    continue
        except Exception:
            pass
        if not videos:
            videos = self._parse_md_videos(html)
        return videos

    def _parse_md_videos(self, text):
        """jina镜像markdown兜底解析"""
        out = []
        if not text or 'Markdown Content:' not in text:
            return out
        pat = (r'\[!\[Image\s+\d+(?::[^\]]*)?\]\((https?://[^)]+)\)'
               r'\s*([^\]]*)\]\((https?://[^/\s)]+)/videos/([^/?#]+)/?)\)'
               r'\s*\n+\s*#{2,6}\s*\[([^\n]*?)\]\(https?://[^/\s)]+/videos/\4/?)')
        seen = set()
        for pic, tail, href, slug, title in re.findall(pat, text, re.I):
            try:
                vod_id = 'videos/' + slug.lower()
                if vod_id in seen:
                    continue
                seen.add(vod_id)
                dm = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*$', re.sub(r'<[^>]+>', ' ', tail))
                t = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', title)).strip('[]') or slug.upper()
                p = pic if pic and 'placeholder' not in pic else _LOGO
                out.append({'vod_id': vod_id, 'vod_name': t,
                            'vod_pic': self._high_pic(self._fix(p)),
                            'vod_remarks': dm.group(1) if dm else '', 'vod_tag': 'video'})
            except Exception:
                continue
        return out

    def _parse_theme_list(self, html):
        items = []
        seen = set()
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for card in soup.select('div.video-img-box a[href*="/categories/"]'):
                try:
                    path = self._to_path(card.get('href', ''))
                    if not path.startswith('categories/') or path.count('/') < 1 or path in seen:
                        continue
                    seen.add(path)
                    name_el = card.select_one('h4')
                    name = name_el.get_text(strip=True) if name_el else path.rsplit('/', 1)[-1]
                    img = card.find('img')
                    pic = self._high_pic(self._fix((img.get('data-src') or img.get('src') or '') if img else ''))
                    label = card.select_one('span.label')
                    remark = label.get_text(strip=True) if label else '主题'
                    items.append({'vod_id': path, 'vod_name': name, 'vod_pic': pic or _LOGO,
                                  'vod_remarks': remark, 'vod_tag': 'folder'})
                except Exception:
                    continue
        except Exception:
            pass
        if not items:
            items = [{'vod_id': 'categories/' + s, 'vod_name': n, 'vod_pic': _LOGO,
                      'vod_remarks': '主题', 'vod_tag': 'folder'}
                     for n, s in [('主奴调教', 'bdsm'), ('纯爱', 'sex-only'), ('中文字幕', 'chinese-subtitle'),
                                  ('无码破解', 'uncensored'), ('制服', 'uniform'), ('角色扮演', 'roleplay')]]
        return items

    def _parse_model_list(self, html):
        items = []
        seen = set()
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for card in soup.select('div.horizontal-img-box a[href*="/models/"]'):
                try:
                    path = self._to_path(card.get('href', ''))
                    if not path.startswith('models/') or path.count('/') < 1 or path in seen:
                        continue
                    last = path.rsplit('/', 1)[-1]
                    if last.isdigit():
                        continue
                    seen.add(path)
                    name_el = card.select_one('h6.title')
                    name = name_el.get_text(strip=True) if name_el else last
                    span = card.find('span')
                    remark = span.get_text(strip=True) if span else '女优'
                    img = card.find('img')
                    pic = ''
                    if img:
                        pic = img.get('data-src') or img.get('src') or ''
                        if 'avatar.svg' in pic or 'blank.' in pic or 'placeholder' in pic:
                            pic = ''
                    items.append({'vod_id': path, 'vod_name': name,
                                  'vod_pic': self._fix(pic) or self._model_pic_proxy(last),
                                  'vod_remarks': remark, 'vod_tag': 'folder'})
                except Exception:
                    continue
        except Exception:
            pass
        return items

    def searchContent(self, key, quick, pg='1'):
        page = self._int(pg)
        try:
            kw = quote(str(key or '').strip(), safe='')
            path = 'search/' + kw
            url = path + '/' if page == 1 else path + '/' + str(page) + '/'
            html = self._request(url)
            videos = self._parse_video_grid(html)
            pc = self._pagecount(html, path)
            if pc <= 0:
                pc = page if not videos else page + 1
            print('[Jable] 搜索 %s 第%d页: %d 项' % (key, page, len(videos)))
            return {'list': videos, 'page': page, 'pagecount': max(pc, page), 'limit': 24, 'total': 999999}
        except Exception as e:
            print('[Jable] 搜索失败 - %s' % e)
            return {'list': [], 'page': page, 'pagecount': 1, 'limit': 24, 'total': 0}

    def detailContent(self, ids):
        arr = ids if isinstance(ids, list) else [ids]
        path = self._to_path(str(arr[0]))
        if not path.startswith('videos/'):
            path = 'videos/' + path.lstrip('/')
        slug = path.split('/')[-1]
        vod = {'vod_id': path, 'vod_name': slug.upper(), 'vod_pic': '', 'type_name': '日本AV',
               'vod_area': '日本', 'vod_play_from': 'Jable', 'vod_play_url': '播放$' + path}
        try:
            html = self._request(path + '/')
            if not html:
                return {'list': [vod]}
            soup = BeautifulSoup(html, 'html.parser')
            og = soup.find('meta', property='og:title')
            if og and og.get('content'):
                vod['vod_name'] = og['content']
            oi = soup.find('meta', property='og:image')
            if oi and oi.get('content'):
                vod['vod_pic'] = oi['content']
            if vod['vod_name'] == slug.upper():
                t = soup.find('title')
                if t:
                    vod['vod_name'] = t.get_text(strip=True).split(' - ')[0] or vod['vod_name']
            actors = []
            for a in soup.select('div.models a.model'):
                el = a.find('img') or a.find('span', class_='placeholder') or a
                txt = (el.get('title') or '').strip()
                if txt and txt not in actors:
                    actors.append(txt)
            tags = []
            for a in soup.find_all('a', href=re.compile(r'/categories/')):
                txt = a.get_text(strip=True)
                if txt and txt not in tags:
                    tags.append(txt)
            vod['vod_actor'] = ' | '.join(actors[:5]) if actors else ''
            if tags:
                vod['type_name'] = ' | '.join(tags[:3])
            update_time = view_count = ''
            for node in soup.find_all('use'):
                href = node.get('xlink:href') or node.get('href') or ''
                if 'icon-clock' not in href and 'icon-eye' not in href:
                    continue
                svg = node.parent
                nxt = svg.find_next_sibling() if svg else None
                if not nxt or nxt.name != 'span':
                    continue
                txt = re.sub(r'\s', '', nxt.get_text())
                if 'icon-clock' in href and not update_time:
                    update_time = txt
                elif 'icon-eye' in href and not view_count:
                    view_count = txt
            parts = []
            if update_time:
                parts.append('⏰' + update_time)
            if view_count:
                parts.append('👀' + view_count)
            if parts:
                vod['vod_content'] = '  '.join(parts)
            elif actors:
                vod['vod_content'] = '主演: ' + ' | '.join(actors)
            return {'list': [vod]}
        except Exception as e:
            print('[Jable] 详情解析失败 - %s' % e)
            return {'list': [vod]}

    def playerContent(self, flag, id, vipFlags):
        raw = str(id or '')
        url = raw.split('$')[-1] if '$' in raw else raw
        header = {'User-Agent': self.ua, 'Referer': self.base_url + '/', 'Origin': self.base_url}
        try:
            if url.startswith('http'):
                p = urlparse(url)
                header['Referer'] = p.scheme + '://' + p.netloc + '/'
                header['Origin'] = p.scheme + '://' + p.netloc
                print('[Jable] 播放: 直链 %s...' % url[:60])
                return {'parse': 0, 'playUrl': '', 'url': url, 'header': header}
            slug = url.rstrip('/').split('/')[-1]
            real = ''
            c = self._url_cache.get(slug)
            if c and time.time() - c[1] < 1800:
                real = c[0]
            if not real:
                real = self._extract_hls(slug)
            if real:
                if len(self._url_cache) > 50:
                    self._url_cache.clear()
                self._url_cache[slug] = (real, time.time())
                print('[Jable] 播放: hls %s...' % real[:60])
                return {'parse': 0, 'playUrl': '', 'url': real, 'header': header}
            print('[Jable] 播放: hls解析失败, 降级壳嗅探')
            return {'parse': 1, 'playUrl': '', 'url': self.base_url + '/videos/%s/' % quote(slug, safe='-'),
                    'header': header}
        except Exception as e:
            print('[Jable] 播放解析异常 - %s' % e)
            return {'parse': 1, 'playUrl': '', 'url': self.base_url + '/', 'header': header}

    def _extract_hls(self, slug):
        try:
            html = self._request('videos/%s/' % quote(slug, safe='-'))
            if not html:
                return ''
            m = re.search(r'var\s+hlsUrl\s*=\s*(["\'])(https?://.*?)\1', html, re.S)
            if not m:
                m = re.search(r'(https?://[^\'"\s]+\.m3u8[^\'"\s]*)', html)
            if not m:
                return ''
            url = (m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)).replace('\\/', '/')
            return url if self._probe_media(url) else ''
        except Exception:
            return ''

    def _probe_media(self, url, timeout=6):
        try:
            sess = self.session or requests.Session()
            r = sess.get(url, timeout=timeout, verify=False, allow_redirects=True,
                                 headers={'User-Agent': self.ua, 'Referer': self.base_url + '/',
                                          'Range': 'bytes=0-2047'})
            head = (r.text or '')[:512]
            return r.status_code in (200, 206) and ('#EXTM3U' in head or '.mp4' in url.lower())
        except Exception:
            return False

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(?:m3u8|mp4)(?:[?#]|$)|pumpres|/videos/', str(url or ''), re.I))

    def manualVideoCheck(self):
        return False

    def _model_pic_proxy(self, slug):
        try:
            base = self.getProxyUrl()
        except Exception:
            return _LOGO
        if not base or not str(base).startswith('http'):
            return _LOGO
        try:
            b = base64.urlsafe_b64encode(str(slug).encode('utf-8')).decode('ascii').rstrip('=')
            return base + ('&' if '?' in base else '?') + 'type=model&u=' + b
        except Exception:
            return _LOGO

    def _b64d(self, s):
        if not s:
            return ''
        s = str(s).strip()
        pad = '=' * (-len(s) % 4)
        for fn in (base64.urlsafe_b64decode, base64.b64decode):
            try:
                return fn((s + pad).encode('ascii')).decode('utf-8', 'ignore')
            except Exception:
                continue
        return ''

    def _fetch_img(self, url):
        try:
            sess = self._xs or requests.Session()
            r = sess.get(url, headers={'User-Agent': self.ua, 'Referer': self.base_url + '/'}, timeout=15)
            if r.status_code == 200 and r.content:
                ct = (r.headers.get('Content-Type') or 'image/jpeg').split(';')[0]
                return r.content, (ct if '/' in ct else 'image/jpeg')
        except Exception:
            pass
        return b'', ''

    def _logo_bytes(self):
        if self._logo_cache is None:
            data, ct = self._fetch_img(_LOGO)
            self._logo_cache = (data, ct if data else 'image/png')
        return self._logo_cache

    def _serve_model(self, slug):
        c = self._model_pic_cache.get(slug)
        if c:
            return [200, c[1], c[0], '']
        text = ''
        try:
            text = self._request('models/%s/' % quote(slug, safe='-'))
        except Exception:
            text = ''
        pic = ''
        if text:
            sec = re.search(r'content-header.*?</section>', text, re.I | re.S)
            if sec:
                am = re.search(r'<img\b[^>]*>', sec.group(0), re.I)
                if am:
                    m = re.search(r'(?:data-src|src)\s*=\s*["\']([^"\']+)', am.group(0))
                    if m:
                        u = self._fix(m.group(1))
                        if u and 'logo' not in u and 'avatar.svg' not in u and 'placeholder' not in u:
                            pic = u
            if not pic:
                vm = re.search(r'<div\b[^>]*class=["\'][^"\']*video-img-box.*?data-src=["\']([^"\']+)',
                               text, re.I | re.S)
                if vm:
                    pic = self._fix(vm.group(1))
        data, ct = self._fetch_img(pic) if pic else (b'', '')
        if not data:
            data, ct = self._logo_bytes()
        if len(self._model_pic_cache) > 200:
            self._model_pic_cache.clear()
        self._model_pic_cache[slug] = (data, ct)
        return [200, ct, data, '']

    def localProxy(self, param):
        try:
            p = param or {}
            if str(p.get('type') or '') == 'model':
                slug = self._b64d(p.get('u', ''))
                if slug and re.match(r'^[a-z0-9-]+$', slug):
                    return self._serve_model(slug)
                return [404, 'text/plain', '', '']
            url = self._b64d(p.get('url', ''))
            m = re.match(r'https?://([^/]+)', url or '')
            if not m:
                return [404, 'text/plain', '', '']
            host = m.group(1).lower()
            if not any(host == h or host.endswith('.' + h) for h in _PIC_HOSTS):
                return [403, 'text/plain', '', '']
            data, ct = self._fetch_img(url)
            if data and ct.startswith('image'):
                return [200, ct, data, '']
            return [404, 'text/plain', '', '']
        except Exception:
            return [404, 'text/plain', '', '']

    def destroy(self):
        for s in (self.session, self._xs):
            try:
                if s:
                    s.close()
            except Exception:
                pass