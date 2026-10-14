#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import ssl
import time
import math
import json
import base64
import warnings
import threading
import html as _html
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlencode, urljoin, parse_qsl

import requests
from requests.adapters import HTTPAdapter
from base.spider import Spider

_CIPHERS = 'TLS_AES_128_GCM_SHA256:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_256_GCM_SHA384:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES128-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:AES128-SHA:AES256-SHA'

_PUBLISH = 'https://x99dh.pro/'
_DOMAINS = ['jable1.nl', 'jable888.net', 'jable1.net', 'jable888.com', 'jable.cfd', 'jable.sbs', '91jable.sbs', '91jable.top', '91jable.icu', 'jable1.cc', 'jable1.xyz', 'jable1.lat', 'jable1.vip', 'jable18.top']

_TAGS = [("黑丝", "black-pantyhose"), ("过膝袜", "knee-socks"), ("运动装", "sportswear"), ("肉丝", "flesh-toned-pantyhose"), ("丝袜", "pantyhose"), ("眼镜娘", "glasses"), ("兽耳", "kemonomimi"), ("渔网", "fishnets"), ("水着", "swimsuit"), ("校服", "school-uniform"), ("旗袍", "cheongsam"), ("婚纱", "wedding-dress"), ("女仆", "maid"), ("和服", "kimono"), ("吊带袜", "stockings"), ("兔女郎", "bunny-girl"), ("黑肉", "suntan"), ("长身", "tall"), ("软体", "flexible-body"), ("贫乳", "small-tits"), ("美腿", "beautiful-leg"), ("美尻", "beautiful-butt"), ("纹身", "tattoo"), ("短发", "short-hair"), ("白虎", "hairless-pussy"), ("熟女", "mature-woman"), ("巨乳", "big-tits"), ("少女", "girl"), ("娇小", "dainty"), ("颜射", "facial"), ("脚交", "footjob"), ("肛交", "anal-sex"), ("痉挛", "spasms"), ("潮吹", "squirting"), ("深喉", "deep-throat"), ("接吻", "kiss"), ("口爆", "cum-in-mouth"), ("口交", "blowjob"), ("乳交", "tit-wank"), ("中出", "creampie"), ("露出", "outdoor"), ("集团进犯", "gang-intrusion"), ("进犯", "intrusion"), ("调教", "tune"), ("捆绑", "bondage"), ("瞬间插入", "quickie"), ("痴汉", "chikan"), ("痴女", "chizyo"), ("男M", "masochism-guy"), ("泥醉", "crapulence"), ("泡姬", "soapland"), ("母乳", "breast-milk"), ("放尿", "piss"), ("按摩", "massage"), ("多P", "groupsex"), ("刑具", "grip"), ("凌辱", "insult"), ("一日十回", "10-times-a-day"), ("3P", "3p"), ("黑人", "black"), ("丑男", "ugly-man"), ("诱惑", "temptation"), ("亲属", "kinship"), ("童贞", "virginity"), ("时间停止", "time-stop"), ("复仇", "avenge"), ("年龄差", "age-difference"), ("巨汉", "giant"), ("媚药", "love-potion"), ("夫目前犯", "sex-beside-husband"), ("出轨", "affair"), ("催眠", "hypnosis"), ("偷拍", "private-cam"), ("下雨天", "rainy-day"), ("NTR", "ntr"), ("风俗娘", "club-hostess-and-sex-worker"), ("医生", "doctor"), ("逃犯", "fugitive"), ("护士", "nurse"), ("老师", "teacher"), ("空姐", "flight-attendant"), ("球队经理", "team-manager"), ("未亡人", "widow"), ("搜查官", "detective"), ("情侣", "couple"), ("家政妇", "housewife"), ("家庭教师", "private-teacher"), ("偶像", "idol"), ("人妻", "wife"), ("主播", "female-anchor"), ("OL", "ol"), ("魔镜号", "magic-mirror"), ("电车", "tram"), ("处女", "first-night"), ("监狱", "prison"), ("温泉", "hot-spring"), ("洗浴场", "bathing-place"), ("泳池", "swimming-pool"), ("汽车", "car"), ("厕所", "toilet"), ("学校", "school"), ("图书馆", "library"), ("健身房", "gym-room"), ("便利店", "store"), ("录像", "video-recording"), ("处女作/引退作", "debut-retires"), ("综艺", "variety-show"), ("节日主题", "festival"), ("感谢祭", "thanksgiving"), ("4小时以上", "more-than-4-hours")]
_CATS = [("主奴调教", "bdsm"), ("纯爱", "sex-only"), ("中文字幕", "chinese-subtitle"), ("凌辱", "insult"), ("制服", "uniform"), ("角色扮演", "roleplay"), ("偷拍自拍", "private-cam"), ("无码破解", "uncensored"), ("脚交指交", "fingering"), ("成人动画", "anime")]

_SORT = {'key': 'sort', 'name': '排序', 'value': [
    {'n': '最新发布', 'v': 'post_date'},
    {'n': '最多观看', 'v': 'video_viewed'},
    {'n': '最多收藏', 'v': 'most_favourited'},
    {'n': '全部排序', 'v': 'post_date_and_popularity'},
]}
_MODEL_SORT = {'key': 'sort', 'name': '排序', 'value': [
    {'n': '热度优先', 'v': 'avg_videos_popularity'},
    {'n': '名称顺序', 'v': 'title'},
    {'n': '最近更新', 'v': 'last_content_date'},
    {'n': '最多影片', 'v': 'total_videos'},
]}


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
    host = 'https://jable1.nl'
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    logo = 'https://spic1-66.piccdn1.cc/assets-cdn.jable.tv/assets/images/logo.png'
    pic_hosts = ('spic1-66.piccdn1.cc', 'piccdn1.cc', 'assets-cdn.jable.tv')

    def __init__(self):
        self.name = 'Jable'
        self.headers = {
            'User-Agent': self.ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': self.host + '/',
        }
        self.domains = ['https://' + d for d in _DOMAINS]
        self.session = None
        self._xs = None
        self._url_cache = {}
        self._item_cache = {}
        self._model_pic_cache = {}
        self._logo_cache = None
        self._model_pages = {}
        self._tag_total_cache = {}
        self._tag_meta = {}
        self._model_meta = {}
        self._bg_started = set()
        self._bg_lock = threading.Lock()
        self._names = {}
        self._seal = False
        self.filters = {}
        self.classes = [
            {'type_id': 'latest-updates', 'type_name': '最新更新'},
            {'type_id': 'hot', 'type_name': '热门'},
            {'type_id': 'categories', 'type_name': '影片主题'},
            {'type_id': 'tags', 'type_name': '热门标签'},
            {'type_id': 'models', 'type_name': '选女优'},
        ]
        _sub = [{'n': n, 'v': 'tag-' + s} for n, s in _TAGS]
        self.filters['latest-updates'] = [_SORT, {'key': 'tag', 'name': '主题', 'value': [{'n': '全部', 'v': ''}] + _sub}]
        self.filters['hot'] = [_SORT, {'key': 'tag', 'name': '主题', 'value': [{'n': '全部', 'v': ''}] + _sub}]
        self.filters['models'] = [_MODEL_SORT]
        self.filters['categories'] = [_SORT]
        for _n, _s in _TAGS:
            self.filters['tag-' + _s] = [_SORT]
        self.filters['tags'] = [_SORT]
        for _n, _s in _CATS:
            self.filters['cat-' + _s] = [_SORT]

    def init(self, extend=''):
        warnings.filterwarnings('ignore')
        s = requests.Session()
        try:
            a = _CFAdapter()
            s.mount('https://', a)
            s.mount('http://', a)
        except Exception:
            pass
        s.headers.update(self.headers)
        try:
            s.cookies.set('x-index-auth', 'authed', domain='.' + self.host.split('//')[1], path='/')
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
        self._probe()

    def getName(self):
        return 'Jable'

    def _probe(self):
        for h in self.domains:
            try:
                r = self.session.get(h + '/status.html', timeout=6, verify=False)
                t = (r.text or '')[:8].strip().lower()
                if r.status_code == 200 and t in ('ok', ''):
                    if h != self.domains[0]:
                        self.domains.remove(h)
                        self.domains.insert(0, h)
                        self._set_host(h)
                    print('[Jable] 使用域名: %s' % h)
                    return
            except Exception:
                continue
        try:
            t = self._publish_text()
            if t:
                self._refresh_from_publish(t)
        except Exception:
            pass

    def _set_host(self, h):
        self.host = h.rstrip('/')
        self.headers['Referer'] = self.host + '/'
        try:
            self.session.headers.update(self.headers)
        except Exception:
            pass

    def _publish_text(self):
        for ua in (self.ua, 'curl/8.0'):
            try:
                r = self._xs.get(_PUBLISH, headers={'User-Agent': ua}, timeout=12)
                if r.status_code == 200 and 'encodedData' in r.text:
                    return r.text
            except Exception:
                continue
        return ''

    def _refresh_from_publish(self, text):
        m = re.search(r'encodedData\s*=\s*["\']([A-Za-z0-9+/=]+)["\']', text or '')
        if not m:
            return
        try:
            raw = base64.b64decode(m.group(1) + '=' * (-len(m.group(1)) % 4))
            data = json.loads(raw.decode('utf-8', 'ignore'))
        except Exception:
            return
        for site in data:
            if 'jable' not in str(site.get('name', '')).lower():
                continue
            urls = site.get('urls') or []
            hosts = []
            for u in urls:
                link = str(u.get('url') or '')
                dm = re.match(r'https?://([^/]+)/enter', link)
                if dm and 'x99dh' not in dm.group(1):
                    hosts.append('https://' + dm.group(1))
            if hosts:
                self.domains = list(dict.fromkeys(hosts + self.domains))
                print('[Jable] 发布页刷新域名池: %d 个' % len(self.domains))
                return

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
        for name in ('render', 'renderUrl', 'webview', 'webView', 'loadWebView', 'openWebView', 'getHtmlByWebView', 'webViewFetch', 'renderFetch'):
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
        cur = re.match(r'https?://([^/]+)', url)
        return url if not cur else url.replace('https://' + cur.group(1), self.host, 1)

    def _get(self, url, timeout=15):
        t = self._bare(self._replace_host(url), timeout)
        if t:
            return t
        t = self._shell(self._replace_host(url))
        if t:
            return t
        t = self._reader(self._replace_host(url))
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
        return self._webview(self._replace_host(url))

    def _list_text(self, url):
        t = self._bare(self._replace_host(url), 12)
        if t:
            return t
        t = self._reader(self._replace_host(url))
        if t:
            return t
        return self._get(url, 12)

    @staticmethod
    def _fix(u):
        if not u:
            return ''
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return 'https://spic1-66.piccdn1.cc' + u
        return u

    @staticmethod
    def _high_pic(p):
        return re.sub(r'/320x180/1\.(?:jpe?g|webp|png)(?:\?.*)?$', '/preview.jpg', p or '', flags=re.I)

    @staticmethod
    def _dur(s):
        try:
            seg = s.strip().split(':')
            if len(seg) == 3:
                return '%02d:%02d:%02d' % (int(seg[0]), int(seg[1]), int(seg[2]))
            if len(seg) == 2:
                return '%02d:%02d' % (int(seg[0]), int(seg[1]))
        except Exception:
            pass
        return s.strip()

    @staticmethod
    def _attr(tag, name):
        m = re.search(r'\b%s\s*=\s*(["\'])(.*?)\1' % re.escape(name), tag or '', re.I | re.S)
        return _html.unescape(m.group(2)).strip() if m else ''

    @staticmethod
    def _clean(v):
        v = re.sub(r'<script\b.*?</script>|<style\b.*?</style>', ' ', v or '', flags=re.I | re.S)
        v = re.sub(r'<[^>]+>', ' ', v)
        return re.sub(r'\s+', ' ', _html.unescape(v)).strip()

    def _ext(self, extend):
        if isinstance(extend, dict):
            return extend
        s = str(extend or '').strip()
        if not s:
            return {}
        if s.startswith('{'):
            try:
                return json.loads(s)
            except Exception:
                pass
        try:
            return dict(parse_qsl(s, keep_blank_values=True))
        except Exception:
            return {}

    def _parse_md_videos(self, text):
        out = []
        seen = set()
        pat = (r'\[!\[Image\s+\d+(?::[^\]]*)?\]\((https?://[^)]+)\)'
               r'\s*([^\]]*)\]\((https?://[^/\s)]+)/videos/([^/?#]+)/?)\)'
               r'\s*\n+\s*#{2,6}\s*\[([^\n]*?)\]\(https?://[^/\s)]+/videos/\4/?)')
        for pic, tail, href, slug, title in re.findall(pat, text or '', re.I):
            try:
                slug = slug.lower()
                if slug in seen:
                    continue
                seen.add(slug)
                dm = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*$', self._clean(tail))
                remark = dm.group(1) if dm else ''
                t = self._clean(title).strip('[]') or slug.upper()
                p = self._high_pic(pic) if pic and 'placeholder' not in pic else self.logo
                item = {'vod_id': slug, 'vod_name': t, 'vod_pic': self._fix(p), 'vod_remarks': remark}
                out.append(item)
                self._item_cache[slug] = item.copy()
            except Exception:
                continue
        return out

    def _parse_html_videos(self, text):
        out = []
        seen = set()
        marks = list(re.finditer(r'<div\b[^>]*class=["\'][^"\']*\bvideo-img-box\b[^"\']*["\'][^>]*>', text or '', re.I))
        for i, m in enumerate(marks):
            try:
                b = text[m.start():marks[i + 1].start()] if i + 1 < len(marks) else text[m.start():]
                lm = re.search(r'<a\b[^>]*href=["\']([^"\']*/videos/([^/?#]+)/?)["\']', b, re.I)
                if not lm:
                    continue
                slug = lm.group(2).lower()
                if slug in seen:
                    continue
                seen.add(slug)
                tm = re.search(r'<h6\b[^>]*class=["\'][^"\']*\btitle\b[^"\']*["\'][^>]*>.*?>([^<]+)<', b, re.I | re.S)
                if not tm:
                    tm = re.search(r'<h6[^>]*>([^<]+)<', b, re.I | re.S)
                im = re.search(r'<img\b[^>]*>', b, re.I | re.S)
                p = ''
                if im:
                    p = (self._attr(im.group(0), 'data-src') or self._attr(im.group(0), 'data-original') or self._attr(im.group(0), 'src'))
                    p = self._fix(p)
                dm = re.search(r'<span\b[^>]*class=["\'][^"\']*\blabel\b[^"\']*["\'][^>]*>([^<]+)</span>', b, re.I)
                remark = self._dur(dm.group(1)) if dm else ''
                name = self._clean(tm.group(1)) if tm else slug.upper()
                item = {'vod_id': slug, 'vod_name': name, 'vod_pic': self._high_pic(p) or p or self.logo, 'vod_remarks': remark}
                out.append(item)
                self._item_cache[slug] = item.copy()
            except Exception:
                continue
        return out

    def _parse_list(self, text):
        if not text:
            return [], 1
        if 'Markdown Content:' in text:
            items = self._parse_md_videos(text)
            if not items:
                items = self._parse_html_videos(text)
            return items, (2 if (items and self._has_next(text)) else 1)
        items = self._parse_html_videos(text)
        if not items:
            items = self._parse_md_videos(text)
            return items, (2 if (items and self._has_next(text)) else 1)
        pgs = [int(x) for x in re.findall(r'/videos/|href=["\'][^"\']*/(\d+)/["\']', text) if x and 1 < int(x) < 5000]
        hn = bool(re.search(r'(下一頁|下一页|»)', text)) or bool(pgs)
        return items, (max(pgs) if pgs else (2 if hn else 1))

    @staticmethod
    def _has_next(text):
        if 'Markdown Content:' in (text or ''):
            return bool(re.search(r'\]\(https?://[^/)]+/[^)]*/\d+/', text))
        return bool(re.search(r'(下一頁|下一页|»)', text or ''))

    def _total(self, text):
        if 'Markdown Content:' in (text or ''):
            m = re.search(r'(\d[\d, ]*)\s*部影片', text)
            return int(m.group(1).replace(',', '').replace(' ', '')) if m else 0
        body = re.sub(r'<nav\b[^>]*class=["\'][^"\']*\bapp-nav\b.*?</nav>', '', text or '', flags=re.I | re.S)
        m = re.search(r'(\d[\d, ]*)\s*部影片', self._clean(body))
        return int(m.group(1).replace(',', '').replace(' ', '')) if m else 0

    def _paged(self, text, page, items, limit=24):
        total = self._total(text)
        if total:
            pc = max(page, int(math.ceil(total / float(limit))))
        elif items:
            pc = self._parse_list(text)[1]
            if pc <= page:
                pc = page + 1
        else:
            pc = page
        if not items:
            pc = page
        return {'page': page, 'pagecount': pc, 'limit': limit, 'total': total, 'list': items}

    def _rss(self, params=None, remark='最近更新'):
        url = self._replace_host(self.host + '/rss/')
        if params:
            url += '?' + urlencode(params)
        text = self._bare(url, 12)
        out = []
        seen = set()
        for item in re.findall(r'<item\b[^>]*>(.*?)</item>', text or '', re.I | re.S):
            try:
                link = re.search(r'<link>\s*(https?://[^<\s]+/videos/([^/<\s]+)/?)\s*</link>', item, re.I)
                if not link or link.group(2).lower() in seen:
                    continue
                slug = link.group(2).lower()
                seen.add(slug)
                title = re.search(r'<title>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</title>', item, re.I | re.S)
                pic = re.search(r'<img\b[^>]*src=["\']([^"\']+)', item, re.I | re.S)
                p = self._high_pic(_html.unescape(pic.group(1))) if pic else self.logo
                it = {'vod_id': slug, 'vod_name': self._clean(title.group(1)) if title else slug.upper(), 'vod_pic': self._fix(p), 'vod_remarks': remark}
                out.append(it)
                self._item_cache[slug] = it.copy()
            except Exception:
                continue
        return out

    def _models_fast(self, text, extend=None):
        items = self._parse_models(text)
        ex = self._ext(extend)
        sort = str(ex.get('sort') or '')
        if sort == 'title':
            items.sort(key=lambda i: i['vod_name'])
        elif sort in ('avg_videos_popularity', 'total_videos'):
            items.sort(key=lambda i: int(self._re_digits(i['vod_remarks'])), reverse=True)
        need = [i['vod_id'][6:] for i in items if i['vod_pic'] == self.logo or not i['vod_pic']]
        if need:
            key = 'models-%d' % (len(need) // 20)
            with self._bg_lock:
                go = key not in self._bg_started
                if go:
                    self._bg_started.add(key)
            if go:
                def _bg():
                    for slug in need:
                        try:
                            self._model_pic_proxy(slug)
                            t = self._bare(self._url('/models/%s/' % quote(slug, safe='-'), 1), 8)
                            if t:
                                im = re.search(r'content-header.*?<img[^>]*data-src="([^"]+)"', t, re.S)
                                if im:
                                    u = self._fix(im.group(1))
                                    if u and 'logo' not in u:
                                        self._model_meta[slug] = u
                        except Exception:
                            pass
                threading.Thread(target=_bg, daemon=True).start()
        print('[Jable] 女优二级: %d 项 (补图后台:%d)' % (len(items), len(need)))
        return items

    def _category_cards(self, text, extend=None, kind='tags'):
        preset, pref = (_CATS, 'cat-') if kind == 'cats' else (_TAGS, 'tag-')
        path = 'categories' if kind == 'cats' else 'tags'
        slugs = []
        seen = set()
        pics = {}
        totals = {}
        if not text or 'Markdown Content:' in text:
            slugs = [(sc, n) for n, sc in preset]
        else:
            for slug, blk in re.findall(r'<a[^>]+href=["\'][^"\']*/%s/([^/\'"#?]+)/["\'][^>]*>(.{0,1200}?)</a>' % path, text, re.I | re.S):
                slug = slug.lower()
                if slug in seen or not slug.strip('-'):
                    continue
                seen.add(slug)
                nm = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', blk)).strip()
                im = re.search(r'<img[^>]+(?:data-src|src)=["\']([^"\']+)', blk, re.I)
                if im:
                    u = self._fix(im.group(1))
                    if u and 'logo' not in u and 'placeholder' not in u:
                        pics[slug] = u
                tm = re.search(r'([\d,]+)\s*部', nm)
                if tm:
                    totals[slug] = int(tm.group(1).replace(',', ''))
                if nm:
                    slugs.append((slug, re.sub(r'[\d,]+\s*部(影片)?', '', nm).strip()))
        if not slugs:
            slugs = [(sc, n) for n, sc in preset]
        out = []
        need = []
        for slug, name in slugs:
            meta = self._tag_meta.get((kind, slug))
            pic = pics.get(slug) or (meta[0] if meta else '') or self.logo
            total = totals.get(slug) or (meta[1] if meta else 0)
            out.append({'vod_id': pref + slug, 'vod_name': name, 'vod_pic': pic, 'vod_remarks': ('%d部' % total) if total else ('主题' if kind == 'cats' else '标签'), 'vod_tag': 'folder'})
            if pic == self.logo:
                need.append(slug)
        first = need[:20]
        if first:
            self._tag_meta_sync(first, kind)
            for o in out:
                meta = self._tag_meta.get((kind, o['vod_id'][len(pref):]))
                if meta:
                    if meta[0] and o['vod_pic'] == self.logo:
                        o['vod_pic'] = meta[0]
                    if meta[1]:
                        o['vod_remarks'] = '%d部' % meta[1]
        rest = need[24:]
        if rest:
            key = kind + '-all'
            with self._bg_lock:
                go = key not in self._bg_started
                if go:
                    self._bg_started.add(key)
            if go:
                threading.Thread(target=self._tag_meta_sync, args=(rest, kind), daemon=True).start()
        ex = self._ext(extend)
        sort = str(ex.get('sort') or '')
        if sort in ('video_viewed', 'most_favourited'):
            out.sort(key=lambda o: int(self._re_digits(o['vod_remarks'])), reverse=True)
        print('[Jable] %s 二级: %d 项 (补图后台:%d)' % (kind, len(out), len(rest)))
        return out

    @staticmethod
    def _re_digits(s):
        m = re.search(r'(\d+)', str(s or ''))
        return m.group(1) if m else '0'

    def _tag_meta_sync(self, slugs, kind='tags'):
        path = 'categories' if kind == 'cats' else 'tags'
        def _one(slug):
            key = (kind, slug)
            if key in self._tag_meta:
                return
            try:
                t = self._bare(self._url('/%s/%s/' % (path, quote(slug, safe='-')), 1), 6)
                if not t:
                    t = self._shell(self._url('/%s/%s/' % (path, quote(slug, safe='-')), 1))
            except Exception:
                t = ''
            total = self._total(t) if t else 0
            pic = ''
            if t:
                m = re.search(r'<div class="video-img-box[^"]*">.*?data-src="([^"]+)"', t, re.S) or re.search(r'<img[^>]+src=["\']([^"\']+\.(?:jpg|png|webp))', t, re.I)
                if m:
                    pic = self._high_pic(self._fix(m.group(1)))
            if pic or total:
                self._tag_meta[key] = (pic, total)
        try:
            with ThreadPoolExecutor(16) as ex2:
                list(ex2.map(_one, slugs))
        except Exception:
            pass

    def _parse_models(self, text):
        if not text:
            return []
        if 'Markdown Content:' in text:
            out = []
            seen = set()
            body = (text or '').split('選女優', 1)[-1].split('选女优', 1)[-1].split('Copyright', 1)[0]
            for label, slug in re.findall(r'\[([^\]\n]*部影片[^\]\n]*)\]\(https?://[^/\s)]+/models/([^/?#]+)/?\)', body, re.I):
                try:
                    slug = slug.lower()
                    if slug in seen or slug.isdigit():
                        continue
                    seen.add(slug)
                    cm = re.search(r'(\d[\d, ]*)\s*部影片', label)
                    name = re.sub(r'\d[\d, ]*\s*部影片', '', self._clean(label)).strip('[]# ') or slug
                    out.append({'vod_id': 'model-' + slug, 'vod_name': name, 'vod_pic': self._model_pic_proxy(slug), 'vod_remarks': (cm.group(1).replace(',', '').replace(' ', '') + '部') if cm else '女优', 'vod_tag': 'folder'})
                except Exception:
                    continue
            return out
        out = []
        seen = set()
        marks = list(re.finditer(r'<div\b[^>]*class=["\'][^"\']*\bhorizontal-img-box\b[^"\']*["\'][^>]*>', text or '', re.I))
        for i, m in enumerate(marks):
            try:
                b = text[m.start():marks[i + 1].start()] if i + 1 < len(marks) else text[m.start():]
                lm = re.search(r'href=["\'][^"\']*/models/([^/?#]+)/?["\']', b, re.I)
                if not lm:
                    continue
                slug = lm.group(1).lower()
                if slug in seen or slug.isdigit():
                    continue
                seen.add(slug)
                tm = re.search(r'<h6\b[^>]*class=["\'][^"\']*\btitle\b[^"\']*["\'][^>]*>([^<]+)</h6>', b, re.I | re.S)
                if not tm:
                    continue
                cm = re.search(r'(\d[\d, ]*)\s*部影片', self._clean(b))
                im = re.search(r'<img\b[^>]*>', b, re.I | re.S)
                p = ''
                if im:
                    p = self._attr(im.group(0), 'data-src') or self._attr(im.group(0), 'src')
                    if 'avatar.svg' in p or 'blank.' in p or 'placeholder' in p:
                        p = ''
                    p = self._fix(p)
                out.append({'vod_id': 'model-' + slug, 'vod_name': self._clean(tm.group(1)),
                            'vod_pic': p or self._model_pic_proxy(slug),
                            'vod_remarks': (cm.group(1).replace(',', '').replace(' ', '') + '部') if cm else '女优', 'vod_tag': 'folder'})
            except Exception:
                continue
        return out

    def _url(self, path, page=1, params=None):
        base = urljoin(self.host + '/', path.lstrip('/'))
        if page > 1:
            base = base.rstrip('/') + '/%d/' % page
        if params:
            base += ('&' if '?' in base else '?') + urlencode(params)
        return base

    def _list_url(self, tid, page, extend):
        ex = self._ext(extend)
        sort = str(ex.get('sort') or '')
        tag = str(ex.get('tag') or '')
        params = {'sort_by': sort} if sort else None
        if tid == 'tag-all':
            if tag.startswith('tag-'):
                return self._url('/tags/%s/' % quote(tag[4:], safe='-'), page, params)
            return self._url('/latest-updates/', page, params)
        if tid == 'latest-updates':
            if tag.startswith('tag-'):
                return self._url('/tags/%s/' % quote(tag[4:], safe='-'), page, params)
            return self._url('/latest-updates/', page)
        if tid == 'hot':
            if tag.startswith('tag-'):
                return self._url('/tags/%s/' % quote(tag[4:], safe='-'), page, params)
            return self._url('/hot/', page, params)
        if tid == 'new-release':
            return self._url('/new-release/', page)
        if tid == 'models':
            return self._url('/models/', page, params)
        if tid.startswith('cat-'):
            return self._url('/categories/%s/' % tid[4:], page, params)
        if tid.startswith('model-'):
            return self._url('/models/%s/' % quote(tid[6:], safe='-'), page, params)
        if tid.startswith('tag-'):
            return self._url('/tags/%s/' % quote(tid[4:], safe='-'), page, params)
        return self._url('/latest-updates/', page)

    def _heal_tags(self):
        try:
            for kind, path in (('cats', 'categories'), ('tags', 'tags')):
                t = self._bare(self.host + '/' + path + '/', 6)
                for slug, blk in re.findall(r'<a[^>]+href=["\'][^"\']*/%s/([^/\'"#?]+)/["\'][^>]*>(.{0,1200}?)</a>' % path, t or '', re.I | re.S):
                    slug = slug.lower()
                    nm = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', blk)).strip()
                    nm = re.sub(r'[\d,]+\s*部(影片)?', '', nm).strip()
                    if nm:
                        self._names[(kind, slug)] = nm
        except Exception:
            return
        try:
            for s2 in [k[1] for k in self._names if k[0] == 'tags']:
                if 'tag-' + s2 not in self.filters:
                    self.filters['tag-' + s2] = [_SORT]
            for s2 in [k[1] for k in self._names if k[0] == 'cats']:
                if 'cat-' + s2 not in self.filters:
                    self.filters['cat-' + s2] = [_SORT]
            subs = [{'n': self._names[('tags', s2)], 'v': 'tag-' + s2} for (k2, s2) in self._names if k2 == 'tags']
            for k in ('latest-updates', 'hot'):
                for f in self.filters.get(k, []):
                    if f.get('key') == 'tag':
                        f['value'] = [{'n': '全部', 'v': ''}] + subs
        except Exception:
            pass

    def homeContent(self, filter):
        if not self._seal:
            self._seal = True
            threading.Thread(target=self._heal_tags, daemon=True).start()
        return {'class': self.classes, 'filters': self.filters}

    def homeVideoContent(self):
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if str(pg).isdigit() and int(pg) > 0 else 1
        tid = str(tid)
        try:
            if tid in ('categories', 'tags') and not self._names:
                self._heal_tags()
            if tid == 'categories':
                items = self._category_cards(self._list_text(self.host + '/categories/'), extend, kind='cats')
                return {'page': 1, 'pagecount': 1, 'limit': len(items), 'total': len(items), 'list': items}
            if tid == 'tags':
                items = self._category_cards(self._list_text(self.host + '/tags/'), extend, kind='tags')
                return {'page': 1, 'pagecount': 1, 'limit': len(items), 'total': len(items), 'list': items}
            if tid == 'models':
                items = self._models_fast(self._list_text(self._list_url(tid, page, extend)), extend)
                return {'page': page, 'pagecount': page + 1 if items else page, 'limit': len(items), 'total': len(items) * page, 'list': items}
            url = self._list_url(tid, page, extend)
            text = self._list_text(url)
            items = self._parse_list(text)[0]
            if not items and page == 1:
                items = self._rss(None, '最新')
            return self._paged(text, page, items)
        except Exception:
            return {'page': page, 'pagecount': page, 'limit': 24, 'total': 0, 'list': []}

    def detailContent(self, ids):
        arr = ids if isinstance(ids, list) else [ids]
        vid = str(arr[0])
        slug = vid[6:] if vid.startswith('model-') else vid
        try:
            if vid.startswith('tag-'):
                return self._cat_detail(vid[4:], 'tags')
            if vid.startswith('cat-'):
                return self._cat_detail(vid[4:], 'cats')
            if vid.startswith('model-'):
                return self._model_detail(slug)
            vod = dict(self._item_cache.get(slug) or {})
            text = self._get(self.host + '/videos/%s/' % quote(slug, safe='-'), timeout=12)
            if text and 'Markdown Content:' not in text:
                t = re.search(r'<h4[^>]*>([^<]+)</h4>', text)
                if t:
                    vod['vod_name'] = _html.unescape(t.group(1)).strip()
                poster = re.search(r'<video[^>]+poster=["\']([^"\']+)', text)
                if not poster:
                    poster = re.search(r'og:image["\'][^>]*content=["\']([^"\']+)', text)
                if poster:
                    vod['vod_pic'] = self._fix(poster.group(1))
                tm = re.search(r'<span[^>]*class="[^"]*mr-3[^"]*">([^<]{2,10})</span>\s*<svg[^>]*>#icon-eye', text, re.S)
                rel = re.search(r'上市於[^0-9]{0,10}([0-9-]{8,10})', self._clean(text))
                desc = re.search(r'<h5[^>]*class="[^"]*desc[^"]*">(.*?)</h5>', text, re.S)
                if desc:
                    vod['vod_content'] = self._clean(desc.group(1))
                elif rel:
                    vod['vod_content'] = '上市於 ' + rel.group(1)
                mods = re.findall(r'<a class="model" href="[^"]*/models/([a-z0-9]+)/"[^>]*>\s*<span[^>]*title="([^"]*)"', text)
                if mods:
                    vod['vod_remarks'] = mods[0][1] or '女优:' + mods[0][0][:8]
            vod.setdefault('vod_name', (self._item_cache.get(slug) or {}).get('vod_name') or slug.upper())
            vod.setdefault('vod_pic', (self._item_cache.get(slug) or {}).get('vod_pic') or '')
            vod.setdefault('vod_remarks', '')
            vod.setdefault('vod_content', '')
            vod['vod_id'] = slug
            vod['vod_play_from'] = 'Jable原片$$$Jable嗅探'
            vod['vod_play_url'] = '播放$' + slug + '$$$播放$web$' + slug
            return {'list': [vod]}
        except Exception:
            c = self._item_cache.get(slug) or {}
            vod = {'vod_id': slug, 'vod_name': c.get('vod_name') or slug.upper(), 'vod_pic': c.get('vod_pic') or '', 'vod_remarks': c.get('vod_remarks') or '', 'vod_content': '',
                   'vod_play_from': 'Jable原片$$$Jable嗅探', 'vod_play_url': '播放$' + slug + '$$$播放$web$' + slug}
            return {'list': [vod]}

    def _cat_detail(self, slug, kind):
        path = 'categories' if kind == 'cats' else 'tags'
        text = self._get(self.host + '/%s/%s/' % (path, quote(slug, safe='-')), timeout=12)
        items = self._parse_list(text)[0]
        name = slug
        name = self._names.get((kind, slug)) or dict((s2, n2) for n2, s2 in (_CATS if kind == 'cats' else _TAGS)).get(slug, slug)
        if name == slug:
            t = re.search(r'<h2[^>]*page-title[^>]*>(.*?)</h2>', text or '', re.I | re.S)
            if t:
                name = self._clean(t.group(1))
        total = self._total(text)
        eps = '#'.join([i['vod_name'] + '$' + i['vod_id'] for i in items])
        alls = [(n2, s2) for (k2, s2), n2 in self._names.items() if k2 == ('cats' if kind == 'cats' else 'tags')] or [(n2, s2) for n2, s2 in (_CATS if kind == 'cats' else _TAGS)]
        nav = '#'.join([n + '$' + ('cat-' if kind == 'cats' else 'tag-') + s2 for n, s2 in alls if s2 != slug])
        vod = {'vod_id': ('cat-' if kind == 'cats' else 'tag-') + slug, 'vod_name': name,
               'vod_pic': self.logo, 'vod_remarks': ('%d部' % total) if total else ('%d部' % len(items)),
               'vod_content': '作品合集，点击分集播放',
               'vod_play_from': ('全部主题$$$' if kind == 'cats' else '全部标签$$$') + 'Jable原片',
               'vod_play_url': nav + '$$$' + eps}
        return {'list': [vod]}
    def _model_detail(self, h):
        text = self._get(self.host + '/models/%s/' % quote(h, safe='-'), timeout=12)
        items = self._parse_list(text)[0]
        name = h
        t = re.search(r'<section\b[^>]*class=["\'][^"\']*content-header.*?<h2\b[^>]*>(.*?)</h2>', text or '', re.I | re.S)
        if not t:
            t = re.search(r'<h1[^>]*>([^<]+)</h1>', text or '')
        if t:
            name = self._clean(t.group(1))
        total = self._total(text)
        eps = '#'.join([i['vod_name'] + '$' + i['vod_id'] for i in items])
        vod = {'vod_id': 'model-' + h, 'vod_name': name,
               'vod_pic': self._model_pic_proxy(h),
               'vod_remarks': ('%d部' % total) if total else ('%d部' % len(items)),
               'vod_content': '女优作品合集，点击分集播放',
               'vod_play_from': 'Jable原片', 'vod_play_url': eps}
        return {'list': [vod]}

    def searchContent(self, key, quick, pg='1'):
        page = int(pg) if str(pg).isdigit() and int(pg) > 0 else 1
        try:
            url = self._url('/search/%s/' % quote(str(key or '').strip(), safe=''), page)
            text = self._list_text(url)
            items = self._parse_list(text)[0]
            return self._paged(text, page, items)
        except Exception:
            return {'page': page, 'pagecount': page, 'limit': 24, 'total': 0, 'list': []}

    def playerContent(self, flag, id, vipFlags):
        slug = ''
        try:
            pid = str(id or '')
            web = pid.startswith('web$')
            if web:
                pid = pid[4:]
            slug = pid
            url = ''
            if not web:
                c = self._url_cache.get(slug)
                if c and time.time() - c[1] < 1800:
                    url = c[0]
                if not url:
                    page_url = self._replace_host(self.host + '/videos/%s/' % quote(slug, safe='-'))
                    text = self._bare(page_url, 12)
                    if not text:
                        text = self._shell(page_url)
                    if text:
                        m = re.search(r'\bvar\s+hlsUrl\s*=\s*(["\'])(https?://.*?)\1', text, re.I | re.S)
                        if not m:
                            m = re.search(r'(https?://[^\'"\s]+\.m3u8[^\'"\s]*)', text)
                        if m:
                            url = _html.unescape(m.group(2) if (m.lastindex and m.lastindex >= 2) else m.group(m.lastindex or 1))
                    if url and not self._probe_media(url):
                        url = ''
                    if url:
                        self._url_cache[slug] = (url, time.time())
                        if len(self._url_cache) > 50:
                            self._url_cache.clear()
            if url:
                return {'parse': 0, 'playUrl': '', 'url': url, 'header': {'User-Agent': self.ua, 'Referer': self.host + '/'}}
            return {'parse': 1, 'playUrl': '', 'url': self.host + '/videos/%s/' % quote(slug, safe='-'), 'header': {'User-Agent': self.ua, 'Referer': self.host + '/'}}
        except Exception:
            if slug and not slug.startswith('http'):
                return {'parse': 1, 'playUrl': '', 'url': self.host + '/videos/%s/' % quote(slug, safe='-'), 'header': {'User-Agent': self.ua, 'Referer': self.host + '/'}}
            return {'parse': 0, 'playUrl': '', 'url': '', 'header': {}}

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(?:m3u8|mp4)(?:[?#]|$)', str(url), re.I))

    def manualVideoCheck(self):
        return False

    def _probe_media(self, url, timeout=6):
        try:
            r = self.session.get(url, timeout=timeout, verify=False, allow_redirects=True, headers={'User-Agent': self.ua, 'Referer': self.host + '/', 'Range': 'bytes=0-2047'})
            head = (r.text or '')[:512]
            return r.status_code in (200, 206) and ('#EXTM3U' in head or '.mp4' in url.lower())
        except Exception:
            return False

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

    def _model_pic_proxy(self, slug):
        try:
            base = self.getProxyUrl()
        except Exception:
            return self.logo
        if not base or not base.startswith('http'):
            return self.logo
        try:
            b = base64.urlsafe_b64encode(str(slug).encode('utf-8')).decode('ascii').rstrip('=')
            return base + ('&' if '?' in base else '?') + 'type=model&u=' + b
        except Exception:
            return self.logo

    def _logo_bytes(self):
        if self._logo_cache is None:
            data, ct = self._fetch_img(self.logo)
            self._logo_cache = (data, ct if data else 'image/png')
        return self._logo_cache

    def _fetch_img(self, url):
        try:
            sess = self._xs or requests.Session()
            r = sess.get(url, headers={'User-Agent': self.ua, 'Referer': self.host + '/'}, timeout=15)
            if r.status_code == 200 and r.content:
                ct = (r.headers.get('Content-Type') or 'image/jpeg').split(';')[0]
                return r.content, (ct if '/' in ct else 'image/jpeg')
        except Exception:
            pass
        return b'', ''

    def _serve_model(self, slug):
        c = self._model_pic_cache.get(slug)
        if c:
            return [200, c[1], c[0], '']
        page_url = self._replace_host(self.host + '/models/%s/' % quote(slug, safe='-'))
        text = self._bare(page_url, 10)
        if not text:
            text = self._shell(page_url)
        pic = ''
        if text:
            sec = re.search(r'content-header.*?</section>', text, re.I | re.S)
            if sec:
                am = re.search(r'<img\b[^>]*>', sec.group(0), re.I)
                if am:
                    u = self._attr(am.group(0), 'data-src') or self._attr(am.group(0), 'src')
                    u = self._fix(u)
                    if u and 'logo' not in u and 'avatar.svg' not in u and 'placeholder' not in u:
                        pic = u
            if not pic:
                vm = re.search(r'<div\b[^>]*class=["\'][^"\']*video-img-box.*?data-src=["\']([^"\']+)', text, re.I | re.S)
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
            if not any(host == h or host.endswith('.' + h) for h in self.pic_hosts):
                return [403, 'text/plain', '', '']
            data, ct = self._fetch_img(url)
            if data and ct.startswith('image'):
                return [200, ct, data, '']
            return [404, 'text/plain', '', '']
        except Exception:
            return [404, 'text/plain', '', '']

    def destroy(self):
        pass