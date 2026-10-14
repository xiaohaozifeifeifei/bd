import requests
from bs4 import BeautifulSoup
import re
from base.spider import Spider
import sys
import json
import base64
import urllib.parse

sys.path.append('..')
# https://www.avple.tv  实际访问会落到 https://avple.tv
# 注意：本站不是原脚本那种 MacCMS / stui 模板，而是 Next.js SSR，
# 列表是 ul>li 卡片，详情和播放是同一个 /video/{id} 页面，
# 播放地址不在 video 标签里，要从详情页 __NEXT_DATA__ 里的
# play + play_source_type 字段按规则拼出来（见 playerContent）。
xurl = "https://avple.tv"
headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://avple.tv/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# play_source_type 为 2,3,4,7,8 时，站点会随机用一个 *.cdnedge.live 主机，
# 同一路径在边缘节点上是通用的，这里用实测出现过的一个主机作默认；
# 为 12,13,14,17,18 时规则是把该主机首段 +1 且目录换成 avple-asserts。
CDN_HOST = "d862cp.cdnedge.live"
CDN_HOST_ASSERTS = "d862cp1.cdnedge.live"


class Spider(Spider):
    global xurl
    global headerx

    def getName(self):
        return "AV看到饱"

    def init(self, extend):
        # 可选：源配置的 ext 里传 cookie 可帮过盾。
        # 支持三种写法：{"cookie":"cf_clearance=xxx; ..."}、{"cf_clearance":"xxx"}、
        # 或直接传一串 cookie 文本。cf_clearance 要和你浏览器过盾时用的
        # 同一个 IP（同一 VPN 节点）和 UA 配套，见文件末尾说明。
        self._cookie = ''
        self._good_transport = ''
        if extend:
            try:
                if isinstance(extend, str) and extend.strip().startswith('{'):
                    data = json.loads(extend)
                    if isinstance(data, dict):
                        if data.get('cookie'):
                            self._cookie = str(data['cookie'])
                        elif data.get('cf_clearance'):
                            self._cookie = f"cf_clearance={data['cf_clearance']}"
                elif isinstance(extend, str) and '=' in extend:
                    self._cookie = extend.strip()
                elif isinstance(extend, dict):
                    if extend.get('cookie'):
                        self._cookie = str(extend['cookie'])
                    elif extend.get('cf_clearance'):
                        self._cookie = f"cf_clearance={extend['cf_clearance']}"
            except Exception:
                pass

    def _headers(self):
        h = dict(headerx)
        cookie = getattr(self, '_cookie', '')
        if cookie:
            h['Cookie'] = cookie
        return h

    def isVideoFormat(self, url):
        pass

    # ---------- 工具方法（原脚本没有单独抽，原站结构需要，故新增） ----------
    def _make_soup(self, text):
        # 有的环境没装 lxml，硬写 lxml 会直接抛错导致列表为空，这里做兜底
        try:
            return BeautifulSoup(text, "lxml")
        except Exception:
            return BeautifulSoup(text, "html.parser")

    # ---------- 多种请求方式（过盾用） ----------
    # 实测：普通 requests 在用户设备上被 Cloudflare 返回 403 Just a moment。
    # 不同请求库的 TLS 指纹不同，过盾结果可能不同，所以逐个试，
    # 哪个先拿到 200+正文就记住它，后续请求直接用它。
    def _t_requests(self, url):
        resp = requests.get(url=url, headers=self._headers(), timeout=10)
        return getattr(resp, 'status_code', ''), resp.text or ''

    def _t_requests_full(self, url):
        # requests + 一整套 Chrome 的 sec-* 请求头
        h = self._headers()
        h.update({
            'sec-ch-ua': '"Chromium";v="120", "Google Chrome";v="120", "Not=A?Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        })
        resp = requests.get(url=url, headers=h, timeout=10)
        return getattr(resp, 'status_code', ''), resp.text or ''

    def _t_fetch(self, url):
        # 框架自带的 fetch（如果有）：底层实现和直连 requests 可能不同
        if not hasattr(super(), 'fetch'):
            raise ImportError('no base fetch')
        resp = super().fetch(url, headers=self._headers())
        if hasattr(resp, 'text'):
            return getattr(resp, 'status_code', 200), resp.text or ''
        return 200, str(resp or '')

    def _t_urllib(self, url):
        import urllib.request
        import urllib.error
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read().decode('utf-8', 'ignore')
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8', 'ignore')

    def _t_httpx(self, url):
        import httpx
        with httpx.Client(http2=True, follow_redirects=True, timeout=10) as c:
            resp = c.get(url, headers=self._headers())
            return resp.status_code, resp.text or ''

    def _t_curlcffi(self, url):
        # curl_cffi 能模拟 Chrome 的 TLS 指纹，是过 CF 盾最常用的一招
        from curl_cffi import requests as creq
        resp = creq.get(url, headers=self._headers(), timeout=10, impersonate='chrome')
        return getattr(resp, 'status_code', ''), resp.text or ''

    def _t_cloudscraper(self, url):
        import cloudscraper
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url, headers=self._headers(), timeout=15)
        return getattr(resp, 'status_code', ''), resp.text or ''

    def _transports(self):
        # 顺序按用户设备实测结果排：urllib 实测 200 能过盾，放第一，
        # 免得每次先白挨几次 403；其余留作兜底，环境不同顺序可能不同，
        # _fetch_text 会记住第一个能用的方式。
        return [
            ('urllib', self._t_urllib),
            ('完整头', self._t_requests_full),
            ('requests', self._t_requests),
            ('框架fetch', self._t_fetch),
            ('curlcffi', self._t_curlcffi),
            ('httpx', self._t_httpx),
            ('cloudscraper', self._t_cloudscraper),
        ]

    def _weserv_url(self, pic):
        """weserv 图片代理的正确格式：url 参数是不带 scheme 的 host/path，
        https 源要在前面加 ssl:（官方文档写法）。上一版把整个
        https:// 地址 URL 编码塞进去，代理返回 400，是格式错了。
        代理会把图转成 jpg，并由代理服务器去取原图。
        """
        if pic.startswith('https://'):
            return 'https://images.weserv.nl/?url=ssl:' + pic[len('https://'):] + '&output=jpg'
        if pic.startswith('http://'):
            return 'https://images.weserv.nl/?url=' + pic[len('http://'):] + '&output=jpg'
        return pic

    def _ddg_url(self, pic):
        """DuckDuckGo 的图片代理，格式是 iu/?u=完整地址编码。"""
        return 'https://external-content.duckduckgo.com/iu/?u=' + urllib.parse.quote(pic, safe='') + '&f=1&nofb=1'

    def _pic_url(self, pic):
        """封面统一走 DuckDuckGo 图片代理（实测对比格验证）：
        直链和 @headers 标注在用户设备上都不出图（App 加载图片那一环
        被图床按客户端特征拦了），weserv 代理回 400，只有 DDG 代理
        Python 实测 200、且 App 里对比格真出了封面照片。
        所以列表/详情的封面都换成代理地址，播放地址不受影响。
        """
        if not pic:
            return ''
        pic = str(pic).split('@headers=')[0]
        if 'external-content.duckduckgo.com' in pic:
            return pic
        if not pic.startswith('http'):
            return pic
        return self._ddg_url(pic)

    def _is_good(self, status, text):
        return status == 200 and ('__NEXT_DATA__' in (text or '') or '/video/' in (text or ''))

    def _fetch_text(self, url):
        """逐个方式试，返回 (text, status)。全失败时返回最后一次的结果供诊断。"""
        order = self._transports()
        good = getattr(self, '_good_transport', '')
        if good:
            order = sorted(order, key=lambda x: 0 if x[0] == good else 1)
        last_text, last_status, last_name = '', '', ''
        first_error = None
        for name, fn in order:
            try:
                status, text = fn(url)
            except ImportError:
                continue  # 这个库没装，跳过
            except Exception as e:
                if first_error is None:
                    first_error = e
                continue
            last_text, last_status, last_name = text, status, name
            if self._is_good(status, text):
                self._good_transport = name
                self._last_transport = name
                return text, status
        self._last_transport = last_name
        if not last_text and first_error is not None:
            raise first_error
        return last_text, last_status

    def _get_soup(self, url):
        text, status = self._fetch_text(url)
        try:
            print(f"[Avple] GET {url} -> {status} via {getattr(self, '_last_transport', '')} len={len(text)} next={'__NEXT_DATA__' in text}")
        except Exception:
            pass
        self._last_info = {
            'status': status,
            'final_url': url,
            'len': len(text or ''),
            'has_next': '__NEXT_DATA__' in (text or ''),
            'video_links': (text or '').count('/video/'),
            'transport': getattr(self, '_last_transport', '')
        }
        return self._make_soup(text), text

    def _diag_videos(self, url, html='', videos_count=0, error=None):
        """把诊断结果做成几条假视频，标题就是诊断内容。
        用户在分类列表里看到这些标题、截图或念出来，就能定位问题，
        不需要去找日志。
        """
        lines = []
        if error is not None:
            lines.append(f"【诊断】请求失败:{type(error).__name__}")
            lines.append(f"【诊断】{str(error)[:80]}")
        else:
            info = getattr(self, '_last_info', {}) or {}
            lines.append(f"【诊断】状态{info.get('status', '?')} 长度{info.get('len', '?')}")
            lines.append(f"【诊断】NEXT有={info.get('has_next')} 视频链接数={info.get('video_links')} 解析到={videos_count}")
            if html:
                text = re.sub(r'<[^>]+>', ' ', html[:3000])
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    lines.append(f"【诊断】页面开头:{text[:60]}")
        lines.append(f"【诊断】请求:{url}")
        videos = []
        for i, line in enumerate(lines):
            videos.append({
                "vod_id": f"/diag/{i}",
                "vod_name": line,
                "vod_pic": "",
                "vod_remarks": "诊断结果，不是视频"
            })
        return videos

    def _run_diag(self, url):
        """把每种请求方式都试一遍，返回一行行的结果（短句，方便列表里看）。
        同时把能用的方式记下来，后面正常请求会优先用它。
        """
        lines = []
        lines.append(f"Cookie:{'有' if getattr(self, '_cookie', '') else '无'}")
        for name, fn in self._transports():
            try:
                status, text = fn(url)
                has = '__NEXT_DATA__' in (text or '')
                if self._is_good(status, text):
                    self._good_transport = name
                    lines.append(f"{name}:{status} 长{len(text)} NEXT有 能用★")
                else:
                    lines.append(f"{name}:{status} 长{len(text or '')} NEXT{'有' if has else '无'}")
            except ImportError:
                lines.append(f"{name}:没装这个库")
            except Exception as e:
                lines.append(f"{name}:异常{type(e).__name__}:{str(e)[:40]}")
        # ---- 封面图实测：拿到第一条数据的图，带/不带 Referer 各测一次 ----
        try:
            import urllib.request as _ureq
            import urllib.error as _uerr
            text, _st = self._fetch_text(url)
            payload = self._next_data(self._make_soup(text))
            data = ((payload.get('props', {}) or {}).get('pageProps', {}) or {}).get('data', [])
            pic = data[0].get('img_preview', '') if data and isinstance(data[0], dict) else ''
            if pic:
                lines.append(f"测试图:{pic}")
                # 列表实际返回给 App 的封面值也报出来，确认不是空/被改坏
                try:
                    listed = self._videos_from_records(data[:1])
                    lp = listed[0].get('vod_pic', '') if listed else ''
                    lines.append(f"列表封面值长{len(lp)}:{lp[:60]}")
                except Exception as e:
                    lines.append(f"列表封面值:异常{type(e).__name__}")

                def _img_get(u, hdrs):
                    req = _ureq.Request(u, headers=hdrs)
                    with _ureq.urlopen(req, timeout=10) as resp:
                        return resp.status, resp.headers.get_content_type(), resp.read()

                # 不同 UA 各测一次（之前的测试全用的是 Chrome UA，
                # App 的图片加载器一般是 okhttp/Dalvik UA，是个盲区）
                chrome = {'User-Agent': headerx['User-Agent']}
                for label, hdrs in [('图ChromeUA', chrome),
                                    ('图无UA', {}),
                                    ('图okhttpUA', {'User-Agent': 'okhttp/4.12.0'}),
                                    ('图DalvikUA', {'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 13)'})]:
                    try:
                        st, ct, body = _img_get(pic, hdrs)
                        if label == '图ChromeUA':
                            magic = ''.join([chr(b) if 32 <= b < 127 else '.' for b in body[:12]])
                            lines.append(f"{label}:{st} 类型{ct} 长{len(body)} 文件头[{magic}]")
                        else:
                            lines.append(f"{label}:{st} 类型{ct} 长{len(body)}")
                    except _uerr.HTTPError as e:
                        lines.append(f"{label}:{e.code}")
                    except Exception as e:
                        lines.append(f"{label}:异常{type(e).__name__}:{str(e)[:30]}")
                # 同一张图换扩展名试试（有些图床 webp/jpg 都存了，
                # 要是 jpg 能通，主列表直接换 jpg 就绕开 webp 解码问题）
                for ext in ['jpg', 'png']:
                    if '.' in pic.rsplit('/', 1)[-1]:
                        alt = pic.rsplit('.', 1)[0] + '.' + ext
                        try:
                            st, ct, body = _img_get(alt, chrome)
                            lines.append(f"图换{ext}:{st} 类型{ct} 长{len(body)}")
                        except _uerr.HTTPError as e:
                            lines.append(f"图换{ext}:{e.code}")
                        except Exception as e:
                            lines.append(f"图换{ext}:异常{type(e).__name__}")
                # 公共图片代理从本机测一下通不通（代理通 + 对比格能出图才算真通）
                for label, purl in [('图weserv代理', self._weserv_url(pic)),
                                    ('图ddg代理', self._ddg_url(pic))]:
                    try:
                        st, ct, body = _img_get(purl, chrome)
                        lines.append(f"{label}:{st} 类型{ct} 长{len(body)}")
                    except _uerr.HTTPError as e:
                        lines.append(f"{label}:{e.code}")
                    except Exception as e:
                        lines.append(f"{label}:异常{type(e).__name__}:{str(e)[:30]}")
            else:
                lines.append("图测试:没拿到封面地址")
        except Exception as e:
            lines.append(f"图测试失败:{type(e).__name__}:{str(e)[:40]}")
        return lines

    def _next_data(self, soup):
        """取 __NEXT_DATA__ 的 JSON。实测结构：
        分类/搜索页 props.pageProps.data 就是列表（每页24条），
        字段：_id, title, img_preview, timeLengh（原文拼写）, view_count,
        release, createdAt, tags, acters, code；pageProps.totalPage 是总页数。
        """
        tag = soup.select_one('script#__NEXT_DATA__')
        if not tag:
            return {}
        text = ''
        try:
            text = tag.get_text() or ''
        except Exception:
            text = tag.string or ''
        if not text:
            text = tag.string or ''
        try:
            return json.loads(text)
        except Exception:
            return {}

    def _videos_from_records(self, records):
        videos = []
        seen = set()
        for v in records:
            if not isinstance(v, dict):
                continue
            vid = str(v.get('_id', '')).strip()
            if not vid or vid in seen:
                continue
            seen.add(vid)
            videos.append({
                "vod_id": f"/video/{vid}",
                "vod_name": v.get('title', '') or '',
                "vod_pic": self._pic_url(v.get('img_preview', '') or v.get('img_normal', '') or ''),
                "vod_remarks": v.get('timeLengh', '') or ''
            })
        return videos

    def _parse_next_videos(self, soup):
        """优先从 __NEXT_DATA__ 取列表，比解析 DOM 稳。
        返回 (videos, pageProps)；取不到时 videos 为空，调用方再走 DOM 兜底。
        """
        payload = self._next_data(soup)
        if not payload:
            return [], {}
        props = {}
        try:
            props = payload.get('props', {}).get('pageProps', {}) or {}
        except Exception:
            props = {}
        if isinstance(props.get('data'), list):
            return self._videos_from_records(props['data']), props
        # 首页没有单一 data，是多个分区列表，递归收集所有视频记录去重
        records = []

        def walk(node):
            if isinstance(node, dict):
                if node.get('_id') and node.get('title') and ('img_preview' in node or 'img_normal' in node):
                    records.append(node)
                    return
                for val in node.values():
                    walk(val)
            elif isinstance(node, list):
                for val in node:
                    walk(val)

        walk(payload)
        return self._videos_from_records(records), props

    def _parse_videos(self, soup):
        # 第一选择：__NEXT_DATA__ 结构化数据
        videos, _props = self._parse_next_videos(soup)
        if videos:
            return videos
        # 第二选择：DOM 卡片解析（下面的原逻辑）
        """全站共用卡片结构：
        li > a[href=/video/{id}] > img[src=封面, alt=标题]
        li 里 h2 是标题，时长是独立小 div，p 是「xx次观看 • x天前」
        """
        videos = []
        seen = set()

        cards = soup.select('li')
        for item in cards:
            link_tag = item.select_one('a[href^="/video/"]')
            if not link_tag:
                continue
            detail_url = link_tag.get('href', '')
            if not detail_url or detail_url in seen:
                continue
            seen.add(detail_url)

            img_tag = item.select_one('img')
            pic = img_tag.get('src', '') if img_tag else ''
            title = ''
            title_tag = item.select_one('h2')
            if title_tag:
                title = title_tag.get_text().strip()
            if not title and img_tag:
                title = img_tag.get('alt', '').strip()

            # 时长：卡片里文本正好是 12:34 / 1:02:03 的 div（旧源卡片可能为空）
            subtitle = ''
            for div in item.find_all('div'):
                text = div.get_text().strip()
                if re.fullmatch(r'\d{1,2}:\d{2}(:\d{2})?', text):
                    subtitle = text
                    break
            if not subtitle:
                remark_tag = item.select_one('p')
                subtitle = remark_tag.get_text().strip() if remark_tag else ''

            videos.append({
                "vod_id": detail_url,
                "vod_name": title,
                "vod_pic": self._pic_url(pic),
                "vod_remarks": subtitle
            })

        # 兜底：没有 li 卡片时，直接按 /video/ 链接合并去重
        if not videos:
            for link_tag in soup.select('a[href^="/video/"]'):
                detail_url = link_tag.get('href', '')
                if not detail_url or detail_url in seen:
                    continue
                seen.add(detail_url)
                img_tag = link_tag.select_one('img')
                pic = img_tag.get('src', '') if img_tag else ''
                title = link_tag.get_text().strip()
                if not title and img_tag:
                    title = img_tag.get('alt', '').strip()
                videos.append({
                    "vod_id": detail_url,
                    "vod_name": title,
                    "vod_pic": self._pic_url(pic),
                    "vod_remarks": ''
                })
        return videos

    def _find_instance(self, soup):
        """从 __NEXT_DATA__ 里递归找详情数据：
        带 _id / title，且带 play 或 img_normal 的 dict 就是单片数据，
        字段原样：_id, title, img_normal, play, play_source_type,
        tags, acters（站点原文拼写）, code
        """
        data = self._next_data(soup)
        if not data:
            return {}

        found = []

        def walk(node):
            if isinstance(node, dict):
                if node.get('_id') and node.get('title') and ('play' in node or 'img_normal' in node):
                    found.append(node)
                    return
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(data)
        return found[0] if found else {}

    def _build_play_url(self, play, play_source_type):
        if not play:
            return ''
        play = str(play).strip()
        if play.startswith('http'):
            return play
        try:
            source_type = int(play_source_type)
        except Exception:
            source_type = None
        rel = play.lstrip('/')
        # 空或 5：play 本身就是完整地址，直接返回
        if source_type is None or source_type == 5:
            return play
        if source_type in (1, 1001):
            return f"https://hqua8q61at.cdnedge.live/file/avple-images/{rel}"
        if source_type in (2, 3, 4, 7, 8):
            return f"https://{CDN_HOST}/file/avple-images/{rel}"
        if source_type in (12, 13, 14, 17, 18):
            return f"https://{CDN_HOST_ASSERTS}/file/avple-asserts/{rel}"
        return play

    def homeContent(self, filter):
        # 分类配置，type_id 直接用站点的 tag id，
        # 分类页 URL 就是 /tags/{type_id}/{page}/{排序}
        class_items = [
            {"type_id": "121", "type_name": "麻豆传媒"},
            {"type_id": "122", "type_name": "SWAG"},
            {"type_id": "123", "type_name": "果冻传媒"},
            {"type_id": "124", "type_name": "皇家华人"},
            {"type_id": "125", "type_name": "精东影业"},
            {"type_id": "126", "type_name": "天美传媒"},
            {"type_id": "127", "type_name": "星空无限传媒"},
            {"type_id": "128", "type_name": "乐播传媒"},
            {"type_id": "129", "type_name": "蜜桃传媒"},
            {"type_id": "130", "type_name": "乌鸦传媒"},
            {"type_id": "131", "type_name": "国产自拍"},
            {"type_id": "132", "type_name": "探花精选"},
            {"type_id": "135", "type_name": "FC2PPV"},
            {"type_id": "138", "type_name": "台湾AV"},
            {"type_id": "139", "type_name": "最新影片"},
            {"type_id": "140", "type_name": "热门影片"},
            {"type_id": "142", "type_name": "国产AV"},
            {"type_id": "143", "type_name": "自拍流出"},
            {"type_id": "trend_daily", "type_name": "近期热门"},
            {"type_id": "1", "type_name": "巨乳"},
            {"type_id": "15", "type_name": "黑丝"},
            {"type_id": "13", "type_name": "丝袜"},
            {"type_id": "2", "type_name": "中出"},
            {"type_id": "33", "type_name": "多P"}
        ]

        # 筛选配置，站点分类页只支持排序：date 时间 / view_count 播放量
        sort_filter = [{
            "key": "by",
            "name": "排序",
            "value": [{"n": "时间", "v": "date"},
                      {"n": "播放量", "v": "view_count"}]
        }]
        static_filters = {}
        for item in class_items:
            if not item["type_id"].startswith("trend_") and item["type_id"] != "diag":
                static_filters[item["type_id"]] = sort_filter

        return {
            "class": class_items,
            "filters": static_filters
        }

    def homeVideoContent(self):
        # 首页和 /home 内容相同，区块和分类页用的是同一套卡片结构
        try:
            soup, html = self._get_soup(xurl)
            videos = self._parse_videos(soup)
            if not videos:
                return {'list': self._diag_videos(xurl, html, 0)}
            return {'list': videos}
        except Exception as e:
            return {'list': self._diag_videos(xurl, '', 0, e)}

    def categoryContent(self, cid, pg, filter, ext):
        page = int(pg) if pg else 1
        cateId = ext.get('cateId', cid) if ext else cid
        by = ext.get('by', 'date') if ext else 'date'
        if not by:
            by = 'date'

        # 诊断分类：逐个请求方式试过盾，每种方式一行结果；
        # 第一条是报告入口，点进去在简介里能看完整报告（列表标题会被截断）
        if str(cateId) == 'diag':
            test_url = f"{xurl}/tags/121/1/date"
            report = self._run_diag(test_url)
            diag = [{
                "vod_id": "/diag/report",
                "vod_name": "★诊断报告点我看详情",
                "vod_pic": "",
                "vod_remarks": "点我看完整报告"
            }]
            for line in report:
                diag.append({
                    "vod_id": f"/diag/{len(diag)}",
                    "vod_name": line,
                    "vod_pic": "",
                    "vod_remarks": line[:12]
                })
            # ---- 封面对比格：同一张图，用不同方式给 App 加载 ----
            # 哪一格能显示出真封面（而不是首字色块），就说明哪种方式能用，
            # 截图时重点看这几格。
            try:
                text, _st = self._fetch_text(test_url)
                payload = self._next_data(self._make_soup(text))
                data = ((payload.get('props', {}) or {}).get('pageProps', {}) or {}).get('data', [])
                pic = data[0].get('img_preview', '') if data and isinstance(data[0], dict) else ''
                if pic:
                    tiles = [
                        ("测图A直链", pic),
                        ("测图Cweserv转jpg", self._weserv_url(pic)),
                        ("测图Eddg代理", self._ddg_url(pic)),
                    ]
                    for name, p in tiles:
                        diag.append({
                            "vod_id": f"/diag/{len(diag)}",
                            "vod_name": name,
                            "vod_pic": p,
                            "vod_remarks": name
                        })
            except Exception:
                pass
            return {'list': diag, 'page': 1, 'pagecount': 1, 'limit': 24, 'total': len(diag)}

        # 适配站点分类页 URL 规则
        if str(cateId).startswith('trend_'):
            # 排行：/trend/daily/{page}、/trend/weekly/{page}、/trend/monthly/{page}
            url = f"{xurl}/trend/{str(cateId).replace('trend_', '')}/{page}"
        elif str(cateId).startswith('search_'):
            # 少数抽屉分类站点本身就是走搜索的，预留这种 type_id
            key = str(cateId).replace('search_', '')
            url = f"{xurl}/search?key={urllib.parse.quote(key)}&page={page}&sort={by}"
        else:
            url = f"{xurl}/tags/{cateId}/{page}/{by}"

        try:
            soup, html = self._get_soup(url)
            videos, props = self._parse_next_videos(soup)
            if not videos:
                videos = self._parse_videos(soup)
            if not videos:
                # 解析为空也别返回空列表，把页面到底拿到了什么显示出来
                return {'list': self._diag_videos(url, html, 0),
                        'page': page, 'pagecount': 1, 'limit': 24, 'total': 4}
        except Exception as e:
            return {'list': self._diag_videos(url, '', 0, e),
                    'page': page, 'pagecount': 1, 'limit': 24, 'total': 4}

        result = {'list': videos}
        result['page'] = page
        try:
            result['pagecount'] = int(props.get('totalPage') or 99)
        except Exception:
            result['pagecount'] = 99
        result['limit'] = 24
        result['total'] = 9999
        return result

        # 详情
    def detailContent(self, ids):
        did = ids[0]
        result = {}
        # 诊断条目不是真视频：报告入口点进来，在简介里给完整报告
        if '/diag' in str(did):
            if 'report' in str(did):
                try:
                    lines = self._run_diag(f"{xurl}/tags/121/1/date")
                    content = "每种请求方式过盾的结果：\n" + "\n".join(lines) + \
                        "\n\n看法：有一行写「能用★」就是那个方式能过，正常分类会自动优先用它；" \
                        "如果全是403，就是这个IP+指纹被Cloudflare挡死，下一步要用浏览器过盾后的cf_clearance cookie（源配置ext里传）。"
                except Exception as e:
                    content = f"诊断本身失败：{type(e).__name__}:{e}"
                return {'list': [{"vod_id": did, "vod_name": "诊断报告",
                                  "vod_pic": "", "vod_content": content,
                                  "vod_play_from": "Avple", "vod_play_url": "诊断$/diag/0"}]}
            return {'list': [{"vod_id": did, "vod_name": "诊断条目，不用点进来",
                              "vod_pic": "", "vod_content": "回到分类看标题上的诊断文字，截图发回即可",
                              "vod_play_from": "Avple", "vod_play_url": "诊断$/diag/0"}]}
        if 'http' not in did:
            did = xurl + did
        # 请求详情页（详情和播放是同一个 /video/{id} 页面，没有单独播放页）
        soup, _ = self._get_soup(did)
        instance = self._find_instance(soup)

        # 初始化VOD字典
        vod = {}

        # ========== 提取视频基本信息 ==========
        # 视频ID
        vod["vod_id"] = did

        # 标题：优先 __NEXT_DATA__，其次 h1
        title = instance.get('title', '')
        if not title:
            title_tag = soup.select_one('h1')
            title = title_tag.get_text().strip() if title_tag else ''
        vod["vod_name"] = title

        # 封面图：img_normal 是 /0/1.webp 的大图，取不到时用播放器 poster
        pic = instance.get('img_normal', '')
        if not pic:
            video_tag = soup.select_one('video')
            if video_tag:
                pic = video_tag.get('poster', '') or video_tag.get('data-poster', '')
        vod["vod_pic"] = self._pic_url(pic)

        # 演员：站点字段就叫 acters（原文拼写），本站没有独立导演栏
        actors = instance.get('acters', '')
        if isinstance(actors, list):
            actors = ','.join([str(a) for a in actors])
        vod["vod_actor"] = actors
        vod["vod_director"] = ""

        # 标签 / 番号：tags 里混有 code、演员、题材，整体作分类和标签
        tags = instance.get('tags', '')
        if isinstance(tags, list):
            tags = ','.join([str(t) for t in tags])
        vod["vod_class"] = tags
        vod["vod_tag"] = tags
        vod["vod_remarks"] = instance.get('code', '')

        # 简介：本站详情页没有简介字段，有才取，没有就留空
        vod["vod_content"] = instance.get('description', '') or ''

        # ========== 提取播放列表 ==========
        # 单片单源，没有分集，剧集链接就是详情页本身，
        # 真正的 m3u8 在 playerContent 里按 play 字段拼
        path = urllib.parse.urlparse(did).path
        vod["vod_play_from"] = 'Avple'
        vod["vod_play_url"] = f'正片${path}'

        result = {'list': [vod]}
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        try:
            # 传进来的本身就是直链时直接播
            if '.m3u8' in id or '.mp4' in id:
                result["parse"] = 0
                result["playUrl"] = ''
                result["url"] = id if 'http' in id else xurl + id
                result["header"] = self._headers()
                return result

            full_url = id if 'http' in id else xurl + id
            soup, html = self._get_soup(full_url)

            # 第一步：页面里万一直接有 m3u8 直链，优先用它
            match = re.search(r'https?://[^\s\"\'<>]+?\.m3u8[^\s\"\'<>]*', html)
            if match:
                url = match.group(0)
            else:
                # 第二步：从 __NEXT_DATA__ 的 play + play_source_type 拼地址
                instance = self._find_instance(soup)
                url = self._build_play_url(instance.get('play', ''),
                                            instance.get('play_source_type'))
            if not url or not url.startswith('http'):
                raise Exception('no direct url')

            # 正则/拼址成功，使用直链播放
            result["parse"] = 0
            result["playUrl"] = ''
            result["url"] = url
            result["header"] = self._headers()

        except (AttributeError, Exception):
            # 提取失败（字段没取到或拼址失败），使用嗅探播放
            result["parse"] = 1
            result["playUrl"] = ''
            result["url"] = id if 'http' in id else xurl + id
            result["header"] = self._headers()
        return result

    def searchContentPage(self, key, quick, page):
        result = {}
        if not page:
            page = '1'
        # 搜索无 form action，是前端跳转到 /search?key=xx&page=页&sort=date
        url = f"{xurl}/search?key={urllib.parse.quote(key)}&page={page}&sort=date"
        try:
            soup, html = self._get_soup(url)
            videos, props = self._parse_next_videos(soup)
            if not videos:
                videos = self._parse_videos(soup)
            if not videos:
                return {'list': self._diag_videos(url, html, 0),
                        'page': page, 'pagecount': 1, 'limit': 24, 'total': 4}
        except Exception as e:
            return {'list': self._diag_videos(url, '', 0, e),
                    'page': page, 'pagecount': 1, 'limit': 24, 'total': 4}

        result = {'list': videos}
        result['page'] = page
        try:
            result['pagecount'] = int(props.get('totalPage') or 60)
        except Exception:
            result['pagecount'] = 60
        result['limit'] = 24
        result['total'] = 999999
        return result

    def searchContent(self, key, quick, page='1'):
        return self.searchContentPage(key, quick, page)

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None


if __name__ == "__main__":
    spider = Spider()
    spider.init("")

    # 调用首页视频内容测试
    # result = spider.homeVideoContent()
    # print("首页视频内容测试结果：")
    # print(result)

    # 调用分类内容测试
    # category_result = spider.categoryContent("121", "1", {}, {})
    # print("\n分类内容测试结果：")
    # print(category_result)

    # 调用详情内容测试
    # detail_result = spider.detailContent(["/video/150505402400156"])
    # print("\n详情内容测试结果：")
    # print(detail_result)

    # 调用播放内容测试
    # player_result = spider.playerContent("", "/video/150505402400156", {})
    # print("\n播放内容测试结果：")
    # print(player_result)

    # 调用搜索内容测试
    # search_result = spider.searchContent("麻豆", False)
    # print("\n搜索内容测试结果：")
    # print(search_result)
