# -*- coding: utf-8 -*-
"""
5x5x影院 Python Spider
兼容 FongMi/TV (T3) 和 WebHomeTV/PeekPro (T4)

站点架构：SPA 前端壳子 + SSR 分类页 + JSON 推荐/搜索 API
- 首页分类：/ 的 HTML 中提取 /category/{id}/
- 首页推荐：/json/recommend/rmd_{1-200}.json（每页11条）
- 分类列表：/category/{tid}/page/{pg}/ 的 HTML SSR（每页23条）
- 标签筛选：/tag/{tag_id}/ 的 HTML SSR
- 搜索：/api/search/video?keyword=&page=  JSON API
- 详情页：/vd/{id}/ 的 HTML 含 data-m3u8 / data-mp4 / data-poster
- 播放：直链返回

多域名（自动探测）：
  https://www.17qp16.com
  https://www.pmz3aa.com
  https://www.zqwkox.com
"""
import sys
import json
import re
import random

sys.path.append('..')

# ===== 兼容导入：FM 有基类，PeekPro 没有就自己定义 =====
try:
    from base.spider import Spider
except ImportError:
    import requests as rq
    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r


try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote


class Spider(Spider):

    # 多域名配置（自动探测可用域名）
    DOMAINS = [
        "https://www.17qp16.com",
        "https://www.pmz3aa.com",
        "https://www.zqwkox.com",
    ]

    # 资源服务器（图片封面）
    RES_BASE = "https://jhfduadgiyhas.com:1443"

    # 推荐 JSON 总数 rmd_1.json ~ rmd_200.json
    RMD_TOTAL = 200

    def getName(self):
        return "5x5x影院"

    def init(self, extend=""):
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self._probe_domain()

    # ========== 工具方法 ==========
    def _probe_domain(self):
        """探测可用域名，失败则默认第一个"""
        for domain in self.DOMAINS:
            try:
                r = self.fetch(domain + '/', headers=self.header, timeout=10)
                if r.status_code == 200 and len(r.text) > 500:
                    self.host = domain
                    self.header['Referer'] = domain + '/'
                    return
            except Exception:
                continue
        self.host = self.DOMAINS[0]
        self.header['Referer'] = self.host + '/'

    def _url(self, path):
        if not path:
            return self.host + '/'
        if path.startswith('http'):
            return path
        return self.host + path if path.startswith('/') else self.host + '/' + path

    def _res_url(self, path):
        """拼接资源 URL（图片封面）"""
        if not path:
            return ''
        if path.startswith('http'):
            return path
        return self.RES_BASE + '/' + path.lstrip('/')

    def _txt(self, url, referer=None, timeout=30):
        headers = dict(self.header)
        if referer:
            headers['Referer'] = referer
        try:
            rsp = self.fetch(url, headers=headers, timeout=timeout)
            rsp.encoding = 'utf-8'
            return rsp.text
        except Exception:
            return ""

    def _json(self, url, referer=None, timeout=10):
        """请求并解析 JSON"""
        headers = dict(self.header)
        headers['Accept'] = 'application/json,*/*;q=0.8'
        if referer:
            headers['Referer'] = referer
        try:
            rsp = self.fetch(url, headers=headers, timeout=timeout)
            if rsp.status_code == 200:
                text = rsp.text.strip()
                if text.startswith('{'):
                    return json.loads(text)
        except Exception:
            pass
        return None

    def _parse_cards_from_html(self, html):
        """从 HTML 中解析视频卡片列表（支持无引号属性值）"""
        videos = []
        card_blocks = re.findall(
            r'<a\s+href=["\']?(/vd/(\d+)/)["\']?\s+class=["\']?card[^>]*>(.*?)</a>',
            html, re.S
        )
        for href, vid, block in card_blocks:
            pic = re.search(r'data-src=([^\s>]+)', block)
            pic_url = pic.group(1).strip('"\'') if pic else ''
            alt = re.search(r'alt=([^\s>]+)', block)
            title = alt.group(1).strip('"\'') if alt else ''
            videos.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic_url,
                'vod_remarks': '',
            })
        return videos

    def _extract_max_page(self, html):
        """从分页控件提取最大页码"""
        m = re.search(r'data-max=(\d+)', html)
        if m:
            return int(m.group(1))
        return 99

    # ========== 首页 ==========
    def homeContent(self, filter):
        html = self._txt(self.host + '/')

        # 提取主分类：/category/1/ 大陆, /category/2/ 日韩 ...
        classes = []
        cat_matches = re.findall(
            r'href=["\']?/category/(\d+)/["\']?[^>]*data-cat-id=\d+[^>]*>([^<]+)</a>',
            html, re.S
        )
        for cat_id, cat_name in cat_matches:
            classes.append({'type_id': cat_id, 'type_name': cat_name.strip()})

        if not classes:
            classes = [
                {'type_id': '1', 'type_name': '大陆'},
                {'type_id': '2', 'type_name': '日韩'},
                {'type_id': '3', 'type_name': '欧美'},
                {'type_id': '4', 'type_name': '动画'},
                {'type_id': '5', 'type_name': '三级'},
            ]

        result = {'class': classes}

        # 提取子标签作为筛选器
        filters = {}
        tags = re.findall(
            r'href=["\']?/tag/(\d+)/["\']?[^>]*data-tag-id=\d+[^>]*>([^<]+)</a>',
            html, re.S
        )
        if tags:
            tag_values = [{'n': '全部', 'v': ''}]
            for tag_id, tag_name in tags:
                tag_values.append({'n': tag_name.strip(), 'v': tag_id})
            for c in classes:
                filters[c['type_id']] = [{
                    'key': 'tag',
                    'name': '标签',
                    'value': tag_values
                }]

        if filters:
            result['filters'] = filters

        return result

    def homeVideoContent(self):
        """首页推荐：并发加载多个推荐 JSON，凑够数量"""
        videos = []
        seen = set()

        # 随机选 6 个不同的推荐 JSON，凑约 60 条
        rmd_ids = random.sample(range(1, self.RMD_TOTAL + 1), min(6, self.RMD_TOTAL))
        for rmd_id in rmd_ids:
            try:
                data = self._json(self._url(f'/json/recommend/rmd_{rmd_id}.json'))
                if data and isinstance(data, dict):
                    for item in data.get('list', []):
                        vid = str(item.get('id', ''))
                        if vid and vid not in seen:
                            seen.add(vid)
                            videos.append({
                                'vod_id': vid,
                                'vod_name': item.get('title', ''),
                                'vod_pic': self._res_url(item.get('litpic', '')),
                                'vod_remarks': '',
                            })
            except Exception:
                continue

        return {'list': videos}

    # ========== 分类列表 ==========
    def categoryContent(self, tid, pg, filter, extend):
        """
        分类内容：解析分类页 HTML SSR
        支持标签筛选（通过标签页 HTML 解析）
        """
        pg = int(pg or 1)

        ext = {}
        if extend:
            if isinstance(extend, dict):
                ext = extend
            elif isinstance(extend, str):
                try:
                    ext = json.loads(extend)
                except Exception:
                    ext = {}

        tag_id = ext.get('tag', '')

        # 如果有标签筛选，走标签页
        if tag_id:
            url = self._url(f'/tag/{tag_id}/')
            if pg > 1:
                url = self._url(f'/tag/{tag_id}/page/{pg}/')
        else:
            url = self._url(f'/category/{tid}/')
            if pg > 1:
                url = self._url(f'/category/{tid}/page/{pg}/')

        html = self._txt(url)
        videos = self._parse_cards_from_html(html)
        max_page = self._extract_max_page(html)

        return {
            'list': videos,
            'page': pg,
            'pagecount': max_page,
            'limit': 23,
            'total': max_page * 23,
        }

    # ========== 详情页 ==========
    def detailContent(self, ids):
        # 兼容 list 和 str
        if isinstance(ids, str):
            ids = [ids]
        vod_id = ids[0]

        url = self._url(f'/vd/{vod_id}/')
        html = self._txt(url)

        # 提取标题（去掉站点后缀）
        vod_name = ''
        m_title = re.search(r'<title>([^<]+)</title>', html)
        if m_title:
            vod_name = m_title.group(1).split(' - ')[0].strip()

        # 提取 player-wrap 中的播放数据
        m = re.search(
            r'<div[^>]*id=["\']?player-wrap["\']?[^>]*>',
            html, re.S
        )

        vod_pic = ''
        m3u8_url = ''
        mp4_url = ''

        if m:
            tag = m.group(0)

            m3 = re.search(r'data-m3u8=([^\s>]+)', tag)
            if m3:
                m3u8_url = m3.group(1).strip('"\'')

            mp4 = re.search(r'data-mp4=([^\s>]+)', tag)
            dl = re.search(r'data-dl-base=([^\s>]+)', tag)
            if mp4:
                mp4_file = mp4.group(1).strip('"\'')
                if dl:
                    mp4_url = dl.group(1).strip('"\'').rstrip('/') + '/' + mp4_file

            poster = re.search(r'data-poster=([^\s>]+)', tag)
            if poster:
                vod_pic = poster.group(1).strip('"\'')

        # 全局 fallback 匹配 m3u8
        if not m3u8_url and not mp4_url:
            fm = re.search(r'https?://[^\s"\'<>]+\.m3u8', html)
            if fm:
                m3u8_url = fm.group(0)

        # 构建播放列表
        play_from = []
        play_url = []

        if m3u8_url:
            play_from.append('m3u8')
            play_url.append(f'正片${m3u8_url}')
        if mp4_url:
            play_from.append('mp4')
            play_url.append(f'正片${mp4_url}')

        vod = {
            'vod_id': vod_id,
            'vod_name': vod_name,
            'vod_pic': vod_pic,
            'type_name': '',
            'vod_year': '',
            'vod_area': '',
            'vod_remarks': '',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': '',
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_url),
        }
        return {'list': [vod]}

    # ========== 搜索 ==========
    def searchContent(self, key, quick, pg="1"):
        pg = int(pg or 1)
        url = self._url(f'/api/search/video?keyword={quote(key)}&page={pg}')
        data = self._json(url, referer=self._url('/search/'))

        videos = []
        total_pages = 1

        if data and data.get('code') == 0:
            d = data.get('data')
            if d:
                total_pages = d.get('total_pages', 1)
                for item in d.get('list', []):
                    videos.append({
                        'vod_id': str(item.get('id', '')),
                        'vod_name': item.get('title', ''),
                        'vod_pic': item.get('litpic', ''),
                        'vod_remarks': '',
                    })

        return {
            'list': videos,
            'page': pg,
            'pagecount': total_pages,
            'limit': 28,
            'total': total_pages * 28,
        }

    # ========== 播放解析 ==========
    def playerContent(self, flag, id, vipFlags):
        return {
            'parse': 0,
            'playUrl': '',
            'url': id,
            'header': {
                'User-Agent': self.header['User-Agent'],
                'Referer': self.host + '/',
            },
            'format': 'application/x-mpegURL' if '.m3u8' in id else '',
            'contentType': 'application/x-mpegURL' if '.m3u8' in id else '',
        }

    # ========== 本地代理 ==========
    def localProxy(self, param):
        return [200, "video/MP2T", b"", ""]

    # ========== 清理 ==========
    def destroy(self):
        pass

    def close(self):
        self.destroy()
