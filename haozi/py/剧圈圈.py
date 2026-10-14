# -*- coding: utf-8 -*-
"""
剧圈圈在线 (jqqzx) 站点爬虫 — FongMi/TV & WebHomeTV/PeekPro 兼容
================================================================
功能:
  - 首页分类 + 推荐
  - 分类列表 (电影/电视剧/动漫/综艺/短剧) 分页 + 筛选
  - 详情页 (标题/封面/简介/导演/主演/集数/多线路)
  - 搜索
  - 播放: 直接解析 m3u8/mp4 直链 (parse=0)
  - 多域名备用: 永久域名 .com, 备用 .me/.one/.vip/.cc

数据来源: 苹果CMS (MacCMS) 模板站, HTML 页面解析
  - 首页: /
  - 分类: /vodshow/id/{cateId}/area/{area}/by/{by}/class/{class}/lang/{lang}/page/{catePg}/year/{year}.html
  - 详情: /vod/{vod_id}.html
  - 播放: /play/{vod_id}-{sid}-{nid}.html
  - 搜索: /vodsearch.html?wd={wd}

关键: 需要带 Cookie (gg_iscookie=1) 才能正常访问
播放策略:
  1. 从播放页提取 player_aaaa JSON 获取 vid
  2. POST /jx/api.php 获取加密的视频URL
  3. 使用 sign 函数解密获取 m3u8/mp4 直链
  4. 返回 parse=0 直接播放
"""

import sys
import json
import re
import html as html_mod
import urllib.parse
import base64
import hashlib

# ===== 兼容导入 =====
try:
    from base.spider import Spider as BaseSpider
except Exception:
    try:
        import requests as rq

        class BaseSpider:
            def fetch(self, url, headers=None, **kw):
                kw.pop('timeout', None)
                kw.pop('allow_redirects', None)
                r = rq.get(url, headers=headers, timeout=15, allow_redirects=True, **kw)
                r.encoding = 'utf-8'
                return r

            def post(self, url, headers=None, **kw):
                kw.pop('timeout', None)
                r = rq.post(url, headers=headers, timeout=15, **kw)
                r.encoding = 'utf-8'
                return r
    except Exception:
        class BaseSpider:
            pass


# ===== 域名列表 =====
# 永久域名: jqqzx.com (当前可能连不上, 探测时自动跳过)
# 备用域名: jqqzx.me, jqqzx.one, jqqzx.vip, jqqzx.cc
# 发布页 www.jqqzx.vip 实为镜像, 无额外新域名
DOMAINS = [
    'https://www.jqqzx.me',
    'https://www.jqqzx.one',
    'https://www.jqqzx.vip',
    'https://www.jqqzx.cc',
    'https://www.jqqzx.com',
]

# 访问必须带的 Cookie
COOKIE_STR = 'gg_iscookie=1; mx_style=white; showBtn=true;'

UA = ('Mozilla/5.0 (Linux; U; Android 6.0.1; en-us; TESLA Build/JOP24G) '
      'AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 '
      'Chrome/43.0.2357.65 Mobile Safari/534.30')

# ===== Base64 编解码 (与网站 player.js 一致) =====
_B64_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='


def _b64_decode(inp):
    """网站自定义 Base64 解码"""
    inp = re.sub(r'[^A-Za-z0-9\+\/\=]', '', inp)
    result = ''
    i = 0
    while i < len(inp):
        c1 = _B64_CHARS.index(inp[i]); i += 1
        c2 = _B64_CHARS.index(inp[i]); i += 1
        c3 = _B64_CHARS.index(inp[i]); i += 1
        c4 = _B64_CHARS.index(inp[i]); i += 1
        d1 = (c1 << 2) | (c2 >> 4)
        d2 = ((c2 & 15) << 4) | (c3 >> 2)
        d3 = ((c3 & 3) << 6) | c4
        result += chr(d1)
        if c3 != 64:
            result += chr(d2)
        if c4 != 64:
            result += chr(d3)
    return result


def _custom_str_decode(encoded):
    """customStrDecode: base64解码 → XOR(md5('test')) → base64解码"""
    key = hashlib.md5(b'test').hexdigest()  # 098f6bcd4621d373cade4e832627b4f6
    # Step 1: base64 解码
    decoded = base64.b64decode(encoded).decode('latin-1')
    # Step 2: XOR with key
    code = ''
    for i in range(len(decoded)):
        k = i % len(key)
        code += chr(ord(decoded[i]) ^ ord(key[k]))
    # Step 3: base64 解码
    result = base64.b64decode(code).decode('utf-8', errors='replace')
    return result


def _de_string(search_list, replace_list, url):
    """deString: 根据 search/replace 列表替换 URL 中的字符"""
    result = ''
    for ch in url:
        if ch.isalpha() and ch in search_list:
            idx = search_list.index(ch)
            result += replace_list[idx]
        else:
            result += ch
    return result


def _sign_url(encrypted_url):
    """sign 函数: 解密 API 返回的加密视频URL
    
    JS 原始调用: deString(parts[1], parts[0], combined)
    - parts[1] = search_list (在URL中查找的字符)
    - parts[0] = replace_list (替换为的字符)
    - combined = 实际URL (base64编码)
    """
    decoded = _custom_str_decode(encrypted_url)
    parts = decoded.split('/')
    # 拼接 (跳过前两部分)
    combined = ''
    for i, part in enumerate(parts):
        sep = '' if i == len(parts) - 1 else '/'
        if i == 0 or i == 1:
            pass  # skip
        else:
            combined += part + sep
    # 去掉末尾多余的 /
    if combined.endswith('/'):
        combined = combined[:-1]
    # 解码三部分参数
    # JS: deString(parts[1], parts[0], combined)
    search_list = json.loads(_b64_decode(parts[1]))
    replace_list = json.loads(_b64_decode(parts[0]))
    url = _b64_decode(combined)
    result = _de_string(search_list, replace_list, url)
    return result


def _probe_domains():
    """探测可用域名"""
    available = []
    try:
        import requests as rq
    except ImportError:
        return DOMAINS[:]
    for domain in DOMAINS:
        try:
            r = rq.get(domain + '/', headers={
                'User-Agent': UA,
                'Cookie': COOKIE_STR,
                'Referer': domain + '/',
            }, timeout=8, verify=False, allow_redirects=True)
            if r.status_code == 200 and len(r.text) > 5000:
                # 确认是剧圈圈站
                if '剧圈圈' in r.text or 'jqqzx' in r.text.lower():
                    available.append(domain)
        except Exception:
            continue
    return available if available else DOMAINS[:]


class Spider(BaseSpider):

    def init(self, extend=""):
        """初始化
        extend 格式: 留空 → 自动探测  |  'https://xxx' → 指定域名
        """
        ext = extend.strip() if extend else ''
        if ext:
            self.host = ext.rstrip('/')
            self._all_domains = [self.host]
        else:
            self._all_domains = _probe_domains()
            self.host = self._all_domains[0]

        self.header = {
            'User-Agent': UA,
            'Cookie': COOKIE_STR,
            'Referer': self.host + '/',
        }

        # 分类映射 (对应网站 /type/xxx.html 和 /vodshow/id/xxx.html)
        self.cate_map = {
            '1': '电影',
            '2': '电视剧',
            '3': '动漫',
            '4': '综艺',
            '5': '短剧',
        }
        # cateId 对应网站的分类标识
        self.cate_id = {
            '1': 'dianying',
            '2': 'juji',
            '3': 'dongman',
            '4': 'zongyi',
            '5': 'duanju',
        }

    # ================================================================
    # 工具方法
    # ================================================================

    def _clean_html(self, text):
        if not text:
            return ''
        text = html_mod.unescape(text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _fetch_html(self, url):
        """请求 URL, 带多域名重试"""
        for domain in self._all_domains:
            test_url = url
            for d in DOMAINS:
                if d in test_url:
                    test_url = test_url.replace(d, domain)
                    break
            try:
                rsp = self.fetch(test_url, headers=self.header)
                text = rsp.text
                if text and len(text) > 100 and '404 Not Found' not in text[:200]:
                    return text
            except Exception as e:
                print('[jqqzx] 请求失败: %s => %s' % (test_url, e))
                continue
        return ''

    def _extract_cards(self, html_text):
        """从分类页/首页 HTML 提取视频卡片
        网站使用 module-poster-item 结构
        跳过 banner 卡片 (class="banner") 和无封面的卡片
        按 vod_id 和标题双重去重
        """
        cards = []
        seen_ids = set()
        seen_titles = set()

        # 匹配每个视频卡片: <a ... href="/vod/xxx.html" ... title="xxx" ...>
        # 排除 banner 卡片 (class="banner")
        for m in re.finditer(
            r'<a[^>]*href="(/vod/\d+\.html)"[^>]*>',
            html_text
        ):
            # 检查是否是 banner 卡片
            tag = m.group(0)
            if 'class="banner"' in tag or "class='banner'" in tag:
                continue

            href = m.group(1)
            vod_id = href.replace('/vod/', '').replace('.html', '')
            if vod_id in seen_ids:
                continue

            # 向后取 1500 字符作为卡片块
            block = html_text[m.start():m.start() + 1500]

            # 标题 — 优先从当前 <a> 标签的 title 属性获取
            title = ''
            title_m = re.search(r'title="([^"]+)"', tag)
            if title_m:
                title = html_mod.unescape(title_m.group(1))
            if not title:
                title_m = re.search(r'title="([^"]+)"', block)
                if title_m:
                    title = html_mod.unescape(title_m.group(1))
            if not title:
                alt_m = re.search(r'alt="([^"]+)"', block)
                if alt_m:
                    title = html_mod.unescape(alt_m.group(1))

            # 封面图 — 必须在当前卡片块内找到 data-original
            pic = ''
            img_m = re.search(r'data-original="([^"]+)"', block)
            if img_m:
                pic = img_m.group(1).replace('&amp;', '&')
            if not pic:
                # 尝试从 background url 获取 (banner 卡片)
                bg_m = re.search(r'background:\s*url\(([^)]+)\)', tag)
                if bg_m:
                    pic = bg_m.group(1).strip()
            if not pic:
                img_m2 = re.search(r'src="([^"]*\.(?:jpg|jpeg|webp|png)[^"]*)"', block)
                if img_m2:
                    candidate = img_m2.group(1).replace('&amp;', '&')
                    # 排除占位图
                    if 'load.gif' not in candidate and 'loading' not in candidate:
                        pic = candidate

            # 备注
            remark = ''
            note_m = re.search(r'module-item-note">(.*?)</div>', block, re.DOTALL)
            if note_m:
                remark = self._clean_html(note_m.group(1))

            # 跳过没有标题或没有封面的卡片 (banner 卡片通常没有正确结构)
            if not title:
                continue
            # 标题去重 (同一视频可能在不同板块出现, vod_id 不同但标题相同)
            if title in seen_titles:
                continue
            # 跳过没有封面的卡片 (避免显示空白封面)
            if not pic:
                continue

            seen_ids.add(vod_id)
            seen_titles.add(title)
            cards.append({
                'vod_id': vod_id,
                'title': title,
                'pic': pic,
                'remark': remark,
            })

        return cards

    # ================================================================
    # 首页 (homeContent + homeVideoContent)
    # ================================================================

    def homeContent(self, filter):
        result = {"class": []}
        for tid, tname in self.cate_map.items():
            result["class"].append({
                "type_id": tid,
                "type_name": tname,
            })
        if filter:
            result["filters"] = {}
            # 电影筛选
            result["filters"]['1'] = [
                {"key": "class", "name": "剧情", "value": self._filter_class_movie()},
                {"key": "area", "name": "地区", "value": self._filter_area()},
                {"key": "year", "name": "年份", "value": self._filter_year()},
                {"key": "by", "name": "排序", "value": self._filter_by()},
            ]
            # 电视剧筛选
            result["filters"]['2'] = [
                {"key": "cateId", "name": "类型", "value": self._filter_type_tv()},
                {"key": "class", "name": "剧情", "value": self._filter_class_tv()},
                {"key": "area", "name": "地区", "value": self._filter_area()},
                {"key": "year", "name": "年份", "value": self._filter_year()},
                {"key": "by", "name": "排序", "value": self._filter_by()},
            ]
            # 动漫筛选
            result["filters"]['3'] = [
                {"key": "class", "name": "剧情", "value": self._filter_class_anime()},
                {"key": "area", "name": "地区", "value": self._filter_area()},
                {"key": "year", "name": "年份", "value": self._filter_year()},
                {"key": "by", "name": "排序", "value": self._filter_by()},
            ]
            # 综艺筛选
            result["filters"]['4'] = [
                {"key": "area", "name": "地区", "value": self._filter_area()},
                {"key": "year", "name": "年份", "value": self._filter_year()},
                {"key": "by", "name": "排序", "value": self._filter_by()},
            ]
            # 短剧筛选
            result["filters"]['5'] = [
                {"key": "area", "name": "地区", "value": self._filter_area()},
                {"key": "year", "name": "年份", "value": self._filter_year()},
                {"key": "by", "name": "排序", "value": self._filter_by()},
            ]
        return result

    def _filter_class_movie(self):
        return [
            {"n": "全部剧情", "v": ""}, {"n": "Netflix", "v": "Netflix"},
            {"n": "动作", "v": "动作"}, {"n": "喜剧", "v": "喜剧"},
            {"n": "爱情", "v": "爱情"}, {"n": "科幻", "v": "科幻"},
            {"n": "奇幻", "v": "奇幻"}, {"n": "剧情", "v": "剧情"},
            {"n": "悬疑", "v": "悬疑"}, {"n": "惊悚", "v": "惊悚"},
            {"n": "恐怖", "v": "恐怖"}, {"n": "犯罪", "v": "犯罪"},
            {"n": "冒险", "v": "冒险"}, {"n": "战争", "v": "战争"},
            {"n": "动画", "v": "动画"}, {"n": "历史", "v": "历史"},
        ]

    def _filter_class_tv(self):
        return [
            {"n": "全部剧情", "v": ""}, {"n": "Netflix", "v": "Netflix"},
            {"n": "古装", "v": "古装"}, {"n": "爱情", "v": "爱情"},
            {"n": "战争", "v": "战争"}, {"n": "喜剧", "v": "喜剧"},
            {"n": "家庭", "v": "家庭"}, {"n": "犯罪", "v": "犯罪"},
            {"n": "动作", "v": "动作"}, {"n": "科幻", "v": "科幻"},
            {"n": "奇幻", "v": "奇幻"}, {"n": "剧情", "v": "剧情"},
            {"n": "历史", "v": "历史"}, {"n": "悬疑", "v": "悬疑"},
            {"n": "网剧", "v": "网剧"},
        ]

    def _filter_class_anime(self):
        return [
            {"n": "全部剧情", "v": ""}, {"n": "情感", "v": "情感"},
            {"n": "科幻", "v": "科幻"}, {"n": "热血", "v": "热血"},
            {"n": "推理", "v": "推理"}, {"n": "搞笑", "v": "搞笑"},
            {"n": "冒险", "v": "冒险"}, {"n": "校园", "v": "校园"},
            {"n": "动作", "v": "动作"}, {"n": "机战", "v": "机战"},
            {"n": "运动", "v": "运动"}, {"n": "战争", "v": "战争"},
        ]

    def _filter_type_tv(self):
        return [
            {"n": "全部类型", "v": "juji"},
            {"n": "国产剧", "v": "guochanju"},
            {"n": "日韩剧", "v": "rihanju"},
            {"n": "港台剧", "v": "gangtaiju"},
            {"n": "欧美剧", "v": "oumeiju"},
            {"n": "泰国剧", "v": "taiguoju"},
        ]

    def _filter_area(self):
        return [
            {"n": "全部地区", "v": ""}, {"n": "大陆", "v": "大陆"},
            {"n": "中国大陆", "v": "中国大陆"}, {"n": "香港", "v": "香港"},
            {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"},
            {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"},
            {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"},
            {"n": "泰国", "v": "泰国"}, {"n": "印度", "v": "印度"},
            {"n": "其他", "v": "其他"},
        ]

    def _filter_year(self):
        years = []
        for y in range(2026, 2009, -1):
            years.append({"n": str(y), "v": str(y)})
        years.insert(0, {"n": "全部年份", "v": ""})
        return years

    def _filter_by(self):
        return [
            {"n": "全部排序", "v": ""},
            {"n": "时间排序", "v": "time"},
            {"n": "人气排序", "v": "hits"},
            {"n": "评分排序", "v": "score"},
        ]

    def homeVideoContent(self):
        """首页推荐 — 抓取首页所有视频区域"""
        videos = []
        seen_ids = set()

        html_text = self._fetch_html(self.host + '/')
        if not html_text:
            return {"list": []}

        # 首页有多个 module-items module-poster-items-base 区域
        # 提取所有 /vod/xxx.html 链接对应的卡片
        raw_cards = self._extract_cards(html_text)
        for c in raw_cards:
            if c['vod_id'] in seen_ids:
                continue
            seen_ids.add(c['vod_id'])
            videos.append({
                "vod_id": c['vod_id'],
                "vod_name": c['title'],
                "vod_pic": c['pic'],
                "vod_remarks": c['remark'],
            })

        return {"list": videos}

    # ================================================================
    # 分类列表 (categoryContent)
    # ================================================================

    def categoryContent(self, tid, pg, filter, extend):
        cate_id = self.cate_id.get(tid, 'dianying')
        page = int(pg)

        # 构建分类URL
        # /vodshow/id/{cateId}/area/{area}/by/{by}/class/{class}/lang/{lang}/page/{catePg}/year/{year}.html
        params = []
        if extend:
            if extend.get('cateId'):
                cate_id = extend['cateId']
            if extend.get('area'):
                params.append('area/' + extend['area'])
            if extend.get('by'):
                params.append('by/' + extend['by'])
            if extend.get('class'):
                params.append('class/' + extend['class'])
            if extend.get('lang'):
                params.append('lang/' + extend['lang'])
            if extend.get('year'):
                params.append('year/' + extend['year'])

        path = '/vodshow/id/' + cate_id
        for p in params:
            path += '/' + p
        path += '/page/' + str(page) + '.html'

        url = self.host + path
        html_text = self._fetch_html(url)
        if not html_text:
            return {"list": [], "page": page, "pagecount": 1,
                    "limit": 30, "total": 0}

        raw_cards = self._extract_cards(html_text)
        videos = []
        for c in raw_cards:
            videos.append({
                "vod_id": c['vod_id'],
                "vod_name": c['title'],
                "vod_pic": c['pic'],
                "vod_remarks": c['remark'],
            })

        # 分页: 如果有数据且 >= 30, 说明有下一页
        pagecount = (page + 1) if len(videos) >= 20 else page
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "limit": 30,
            "total": pagecount * 30,
        }

    # ================================================================
    # 详情页 (detailContent)
    # ================================================================

    def detailContent(self, ids):
        """详情页 — 提取标题/封面/简介/导演/主演/线路/集数"""
        if isinstance(ids, str):
            ids = [ids]
        vod_id = ids[0]

        url = self.host + '/vod/' + vod_id + '.html'
        html_text = self._fetch_html(url)
        if not html_text:
            return {"list": []}

        # --- 标题 ---
        vod_name = vod_id
        title_m = re.search(r'<title>(.*?)</title>', html_text, re.DOTALL)
        if title_m:
            full_title = title_m.group(1).strip()
            # "低智商犯罪详情介绍-低智商犯罪在线观看-低智商犯罪迅雷下载 - 剧圈圈在线"
            # 取第一部分
            vod_name = full_title.split('详情')[0].split('-')[0].strip()

        # --- 封面图 ---
        vod_pic = ''
        pic_m = re.search(r'class="module-item-pic"[^>]*>.*?data-original="([^"]+)"',
                          html_text, re.DOTALL)
        if pic_m:
            vod_pic = pic_m.group(1).replace('&amp;', '&')
        if not vod_pic:
            pic_m2 = re.search(r'data-original="([^"]+\.(?:jpg|jpeg|webp|png)[^"]*)"', html_text)
            if pic_m2:
                vod_pic = pic_m2.group(1).replace('&amp;', '&')

        # --- 简介 ---
        vod_content = ''
        desc_m = re.search(r'module-info-introduction-content">(.*?)</div>', html_text, re.DOTALL)
        if desc_m:
            vod_content = self._clean_html(desc_m.group(1))

        # --- 导演 ---
        vod_director = ''
        dir_m = re.search(r'导演：</span>(.*?)</div>', html_text, re.DOTALL)
        if dir_m:
            vod_director = self._clean_html(dir_m.group(1))

        # --- 主演 ---
        vod_actor = ''
        act_m = re.search(r'主演：</span>(.*?)</div>', html_text, re.DOTALL)
        if act_m:
            vod_actor = self._clean_html(act_m.group(1))

        # --- 年份 ---
        vod_year = ''
        year_m = re.search(r'/year/(\d+)"', html_text)
        if year_m:
            vod_year = year_m.group(1)
        if not vod_year:
            year_m2 = re.search(r'class="tag-link[^"]*"[^>]*>(\d{4})</a>', html_text)
            if year_m2:
                vod_year = year_m2.group(1)

        # --- 地区 ---
        vod_area = ''
        area_m = re.search(r'/area/([^"]+)"', html_text)
        if area_m:
            vod_area = area_m.group(1)

        # --- 分类 ---
        type_name = ''
        class_m = re.search(r'class="tag-link[^"]*"[^>]*href="/type/([^"]+)\.html"', html_text)
        if class_m:
            type_id = class_m.group(1)
            type_map = {
                'dianying': '电影', 'juji': '电视剧', 'dongman': '动漫',
                'zongyi': '综艺', 'duanju': '短剧',
                'guochanju': '国产剧', 'rihanju': '日韩剧',
                'gangtaiju': '港台剧', 'oumeiju': '欧美剧', 'taiguoju': '泰国剧',
            }
            type_name = type_map.get(type_id, '')

        # --- 线路列表 ---
        # 线路: data-dropdown-value="xxx" ... <span>显示名</span>
        line_matches = re.finditer(
            r'data-dropdown-value="([^"]*)"[^>]*>(.*?)</div>',
            html_text, re.DOTALL
        )
        lines = []
        for m in line_matches:
            line_key = m.group(1)
            content = m.group(2)
            span_m = re.search(r'<span>(.*?)</span>', content, re.DOTALL)
            display_name = self._clean_html(span_m.group(1)) if span_m else line_key
            if display_name:
                lines.append({'key': line_key, 'name': display_name})

        # --- 播放列表 ---
        # 每条线路对应一个 module-play-list-content
        play_sections = re.finditer(
            r'<div class="module-play-list-content[^"]*">(.*?)</div>\s*</div>',
            html_text, re.DOTALL
        )
        all_play_lists = []
        for m in play_sections:
            section = m.group(1)
            eps = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', section, re.DOTALL)
            episodes = []
            for href, ep_text in eps:
                text = self._clean_html(ep_text)
                episodes.append({'href': href, 'name': text})
            all_play_lists.append(episodes)

        # --- 构建 vod_play_from / vod_play_url ---
        # 线路优先级排序: 将已知不稳定线路 (WJ/QS 等) 移到列表末尾
        # 这些线路解析后返回无效URL或源站不可播, 放到末尾避免优先展示
        LOW_PRIORITY_KEYWORDS = ['WJ', 'QS', 'wj', 'qs']

        def _is_low_priority(name):
            for kw in LOW_PRIORITY_KEYWORDS:
                if kw in name:
                    return True
            return False

        play_from_parts = []
        play_url_parts = []

        if lines and all_play_lists:
            # 先收集所有有效线路 (有集数的)
            normal_lines = []   # 优先线路
            low_lines = []      # 低优先级线路 (WJ/QS)
            for i, line in enumerate(lines):
                if i >= len(all_play_lists):
                    break
                episodes = all_play_lists[i]
                if not episodes:
                    continue
                ep_str = '#'.join([
                    ep['name'] + '$' + ep['href']
                    for ep in episodes
                ])
                item = {'name': line['name'], 'ep_str': ep_str}
                if _is_low_priority(line['name']):
                    low_lines.append(item)
                else:
                    normal_lines.append(item)
            # 正常线路在前, 低优先级线路在后
            ordered = normal_lines + low_lines
            for item in ordered:
                play_from_parts.append(item['name'])
                play_url_parts.append(item['ep_str'])
        elif all_play_lists:
            # 没有线路名但有播放列表
            for i, episodes in enumerate(all_play_lists):
                if not episodes:
                    continue
                play_from_parts.append(u'线路' + str(i + 1))
                ep_str = '#'.join([
                    ep['name'] + '$' + ep['href']
                    for ep in episodes
                ])
                play_url_parts.append(ep_str)
        else:
            # 没有集数信息
            play_from_parts.append(u'线路1')
            play_url_parts.append(u'第1集$/play/' + vod_id + '-1-1.html')

        vod = {
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_year": vod_year,
            "vod_area": vod_area,
            "vod_actor": vod_actor,
            "vod_director": vod_director,
            "vod_remarks": '',
            "vod_play_from": '$$$'.join(play_from_parts),
            "vod_play_url": '$$$'.join(play_url_parts),
            "type_name": type_name,
        }

        return {"list": [vod]}

    # ================================================================
    # 搜索 (search)
    # ================================================================

    def search(self, wd, quick):
        """搜索 — 优先用 suggest 接口 (不触发验证码), 回退到 vodsearch 页面"""
        query = urllib.parse.quote(wd)
        videos = []
        seen = set()

        # 方法1: ajax/suggest 接口 (不触发验证码, 返回 JSON)
        suggest_url = self.host + '/index.php/ajax/suggest?mid=1&wd=' + query + '&limit=20'
        try:
            rsp = self.fetch(suggest_url, headers=self.header)
            suggest_data = json.loads(rsp.text)
            if suggest_data.get('code') == 1 and suggest_data.get('list'):
                for item in suggest_data['list']:
                    vod_id = str(item.get('id', ''))
                    if not vod_id or vod_id in seen:
                        continue
                    seen.add(vod_id)
                    title = item.get('name', '') or vod_id
                    pic = item.get('pic', '').replace('\\/', '/')
                    # suggest 接口没有备注, 留空 (避免每个结果都请求详情页导致超时)
                    videos.append({
                        "vod_id": vod_id,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": '',
                    })
        except Exception as e:
            print('[jqqzx] suggest搜索失败: %s' % e)

        # 如果 suggest 有结果, 直接返回
        if videos:
            return {"list": videos}

        # 方法2: 回退到 vodsearch 页面 (可能触发验证码)
        url = self.host + '/vodsearch.html?wd=' + query
        html_text = self._fetch_html(url)
        if not html_text:
            return {"list": []}

        # 检查是否被验证码拦截
        if '系统安全验证' in html_text or 'mac_verify' in html_text:
            # 尝试备用搜索路径
            url2 = self.host + '/vodsearchmac_wd.html?wd=' + query
            html_text = self._fetch_html(url2)
            if not html_text or '系统安全验证' in html_text:
                return {"list": []}

        # 搜索结果: module-card-item
        for m in re.finditer(
            r'<div class="module-card-item module-item">(.*?)<span>详情</span>',
            html_text, re.DOTALL
        ):
            block = m.group(1)
            href_m = re.search(r'href="(/vod/\d+\.html)"', block)
            alt_m = re.search(r'alt="([^"]+)"', block)
            pic_m = re.search(r'data-original="([^"]+)"', block)
            note_m = re.search(r'module-item-note">(.*?)</div>', block, re.DOTALL)

            if href_m:
                vod_id = href_m.group(1).replace('/vod/', '').replace('.html', '')
                if vod_id in seen:
                    continue
                seen.add(vod_id)
                title = alt_m.group(1) if alt_m else vod_id
                title = html_mod.unescape(title)
                pic = pic_m.group(1).replace('&amp;', '&') if pic_m else ''
                remark = self._clean_html(note_m.group(1)) if note_m else ''

                videos.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remark,
                })

        return {"list": videos}

    # ================================================================
    # 播放 (playerContent) — 直接解析 m3u8/mp4 直链
    # 规范: header 必须是 dict 对象, 不能用 json.dumps 转字符串
    # ================================================================

    def playerContent(self, flag, id, vipFlags):
        """播放 — 直接解析视频直链 (parse=0)

        id (对应 vod_play_url 每集的 value): 播放路径 (如 /play/62719-7-1.html)
        策略:
          1. 构造完整播放页 URL, 获取 player_aaaa JSON
          2. 提取 vid 参数, POST /jx/api.php 获取加密视频URL
          3. 使用 sign 函数解密获取 m3u8/mp4 直链
          4. 返回 parse=0 直接播放
        """
        play_url = str(id) if id else ''

        # play_url 可能是完整路径 /play/xxx.html 或完整URL
        if play_url.startswith('http'):
            play_page_url = play_url
        elif play_url.startswith('/'):
            play_page_url = self.host + play_url
        else:
            play_page_url = self.host + '/play/' + play_url

        # 默认回退: 嗅探模式
        fallback = {
            "parse": 1,
            "playUrl": '',
            "url": play_page_url,
            "header": {
                'User-Agent': self.header.get('User-Agent', UA),
                'Referer': self.host + '/',
                'Cookie': COOKIE_STR,
            },
        }

        try:
            # Step 1: 获取播放页 HTML
            html_text = self._fetch_html(play_page_url)
            if not html_text:
                return fallback

            # Step 2: 提取 player_aaaa JSON
            # player_aaaa 是一行 JSON, 后面紧跟 </script>
            m = re.search(r'var player_aaaa\s*=\s*(\{.*?\})\s*</script>', html_text, re.DOTALL)
            if not m:
                return fallback

            player_data = json.loads(m.group(1))

            # 处理 encrypt 字段
            encrypt = player_data.get('encrypt', 0)
            vid = player_data.get('url', '')

            if encrypt == 1:
                vid = urllib.parse.unquote(vid)
            elif encrypt == 2:
                vid = urllib.parse.unquote(base64.b64decode(vid).decode('utf-8'))

            if not vid:
                return fallback

            # Step 3: POST /jx/api.php 获取加密视频URL
            api_url = self.host + '/jx/api.php'
            api_headers = dict(self.header)
            api_headers['Referer'] = self.host + '/jx/player.php?vid=' + urllib.parse.quote(vid)
            api_headers['X-Requested-With'] = 'XMLHttpRequest'
            api_headers['Content-Type'] = 'application/x-www-form-urlencoded'

            rsp = self.post(api_url, headers=api_headers, data={'vid': vid})
            api_text = rsp.text
            try:
                api_data = json.loads(api_text)
            except Exception:
                return fallback

            if api_data.get('code') != 200 or 'data' not in api_data:
                return fallback

            encrypted_url = api_data['data'].get('url', '')
            video_type = api_data['data'].get('type', '')

            if not encrypted_url:
                return fallback

            # Step 4: 解密获取直链
            real_url = _sign_url(encrypted_url)

            if not real_url or not real_url.startswith('http'):
                return fallback

            # 返回直链播放
            # Referer 策略:
            #   - m3u8 直链: 需要 jqqzx Referer (源站防盗链)
            #   - mp4 直链 (腾讯CDN qchannelvideo.photo.qq.com 等): 不能带 jqqzx Referer,
            #     否则返回 404 (CDN 校验 Referer, 仅允许 v.qq.com 或空 Referer)
            #   - preview=true 参数: 腾讯预览视频, 去掉该参数可获取完整播放
            is_m3u8 = ('m3u8' in real_url or video_type == 'customHls')
            # 检测是否为腾讯CDN域名 (带 preview 参数或 qchannelvideo 域名)
            is_qq_cdn = ('qchannelvideo' in real_url
                         or 'wxsnsdy.video.qq.com' in real_url
                         or 'preview=true' in real_url)

            result = {
                "parse": 0,
                "playUrl": '',
                "url": real_url,
                "header": {
                    'User-Agent': self.header.get('User-Agent', UA),
                },
            }

            if is_m3u8:
                # m3u8 源站防盗链, 需要 jqqzx Referer
                result['header']['Referer'] = self.host + '/'
            elif is_qq_cdn:
                # 腾讯CDN mp4: 不能带 jqqzx Referer (会404)
                # 不设置 Referer, 让播放器用空 Referer 访问
                pass
            else:
                # 其他 mp4 直链: 带 jqqzx Referer 兜底
                result['header']['Referer'] = self.host + '/'

            return result

        except Exception as e:
            print('[jqqzx] playerContent error: %s' % e)
            return fallback

    # 兼容旧壳子方法名别名
    def player(self, flag, id, vipFlags):
        return self.playerContent(flag, id, vipFlags)

    def detail(self, array):
        """别名兼容"""
        return self.detailContent(array)

    # 搜索方法别名 (不同TV壳子调用名不同)
    def searchContent(self, wd, quick):
        return self.search(wd, quick)

    def searchResult(self, wd, quick):
        return self.search(wd, quick)

    # homeContent 别名
    def home(self, filter):
        return self.homeContent(filter)

    def homeVod(self):
        return self.homeVideoContent()

    # categoryContent 别名
    def category(self, tid, pg, filter, extend):
        return self.categoryContent(tid, pg, filter, extend)

    # init 别名
    def init_Cb(self, extend=""):
        return self.init(extend)


# ====================================================================
# 独立运行测试
# ====================================================================
if __name__ == '__main__':
    import urllib3
    urllib3.disable_warnings()

    s = Spider()
    s.init()

    print('可用域名: ' + ', '.join(s._all_domains))
    print('当前主域名: ' + s.host)
    print()

    # 1. 首页分类
    print('=== homeContent ===')
    hc = s.homeContent(True)
    for c in hc['class']:
        print('  %s -> %s' % (c['type_id'], c['type_name']))

    # 2. 首页推荐
    print('\n=== homeVideoContent ===')
    hv = s.homeVideoContent()
    print('推荐 %d 条:' % len(hv['list']))
    for v in hv['list'][:5]:
        print('  [%s] %s  %s' % (v['vod_id'], v['vod_name'], v['vod_remarks']))

    # 3. 分类列表
    print('\n=== categoryContent (电影 p1) ===')
    cc = s.categoryContent('1', 1, True, {})
    print('共 %d 条:' % len(cc['list']))
    for v in cc['list'][:5]:
        print('  [%s] %s  %s' % (v['vod_id'], v['vod_name'], v['vod_remarks']))

    # 4. 详情页 + 播放测试
    print('\n=== detailContent + player ===')
    if cc['list']:
        test_id = cc['list'][0]['vod_id']
        dc = s.detailContent([test_id])
        if dc.get('list'):
            v = dc['list'][0]
            print('  标题: %s' % v['vod_name'])
            print('  封面: %s' % v.get('vod_pic', '')[:80])
            print('  导演: %s' % v.get('vod_director', '')[:50])
            print('  主演: %s' % v.get('vod_actor', '')[:50])
            print('  播放源: %s' % v['vod_play_from'])
            if v['vod_play_url']:
                parts = v['vod_play_url'].split('$$$')
                for i, p in enumerate(parts):
                    eps = p.split('#')
                    print('    线路%d: %d 集 (首: %s)' % (i+1, len(eps), eps[0][:60]))
                    # 测试播放第1集
                    if i == 0:
                        print('    播放第1集...')
                        r = s.playerContent('线路1', eps[0].split('$')[1], [])
                        print('      parse=%s url=%s' % (r['parse'], r['url'][:100]))
                        print('      header类型: %s' % type(r['header']).__name__)

    # 5. 搜索测试
    print('\n=== search("仙逆") ===')
    sr = s.search('仙逆', False)
    print('搜索到 %d 条:' % len(sr['list']))
    for v in sr['list'][:5]:
        print('  [%s] %s  %s' % (v['vod_id'], v['vod_name'], v['vod_remarks']))

    if sr['list']:
        td = s.detailContent([sr['list'][0]['vod_id']])
        if td.get('list'):
            v = td['list'][0]
            print('\n  标题: %s' % v['vod_name'])
            print('  播放源: %s' % v['vod_play_from'])
            if v['vod_play_url']:
                parts = v['vod_play_url'].split('$$$')
                for i, p in enumerate(parts):
                    eps = p.split('#')
                    print('    线路%d: %d 集' % (i+1, len(eps)))
                    if eps and i == 0:
                        print('      首: %s' % eps[0][:60])
                        print('      播放第1集...')
                        r = s.playerContent('线路1', eps[0].split('$')[1], [])
                        print('        parse=%s url=%s' % (r['parse'], r['url'][:100]))
                        print('        header类型: %s' % type(r['header']).__name__)
