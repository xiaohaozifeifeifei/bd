# -*- coding: utf-8 -*-
"""
兼容 FongMi/TV (T3) 和 WebHomeTV/PeekPro (T4) 的 Python Spider
站点: 宝贝妹妹 (baobeimeimei.com)
"""
import sys
import json
import re
import base64
import time

sys.path.append('..')

try:
    from base.spider import Spider
except ImportError:
    import requests as rq
    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=30, **kw)
            r.encoding = 'utf-8'
            return r


class Spider(Spider):

    def getName(self):
        return "宝贝妹妹"

    def init(self, extend=""):
        if isinstance(extend, list):
            self.extend = ''
        else:
            self.extend = extend or ''

        self.host = "https://zpet-pwok-pxis.baobeimeimei.com"
        self.home_url = self.host + "/baobei/?link=alpha.easylinkhandle.click"
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.host + '/',
            'Connection': 'keep-alive',
        }

        self._home_cache = []
        self._home_cache_time = 0

        # 导航关键词过滤
        self.NAV_KEYWORDS = (
            '首页', '分类', '排行', '最新', '热门', '推荐',
            '国产传媒', '国产视频', '国产精品', '国产剧情', '国产自拍',
            '网曝黑料', '主播大秀', 'av解说', '日本有码', '日本无码',
            '欧美', '成人动漫', 'vr', '上一页', '下一页', '末页',
        )

        # ===== 主分类列表 =====
        self.classes = [
            {"type_name": "国产传媒",  "type_id": "2"},
            {"type_name": "国产视频",  "type_id": "163"},
            {"type_name": "国产精品",  "type_id": "17"},
            {"type_name": "国产剧情",  "type_id": "18"},
            {"type_name": "国产自拍",  "type_id": "48"},
            {"type_name": "网曝黑料",  "type_id": "232"},
            {"type_name": "主播大秀",  "type_id": "236"},
            {"type_name": "AV解说",    "type_id": "233"},
            {"type_name": "日本有码",  "type_id": "51"},
            {"type_name": "日本无码",  "type_id": "221"},
            {"type_name": "欧美",      "type_id": "30"},
            {"type_name": "成人动漫",  "type_id": "164"},
            {"type_name": "VR",        "type_id": "84"},
        ]

    def _url(self, path):
        if not path:
            return self.home_url
        if path.startswith('http'):
            return path
        if path.startswith('/'):
            return self.host + path
        return self.host + '/' + path

    def _txt(self, url, referer=None, timeout=30):
        headers = dict(self.header)
        if referer:
            headers['Referer'] = referer
        try:
            rsp = self.fetch(url, headers=headers, timeout=timeout)
            try:
                rsp.encoding = 'utf-8'
            except Exception:
                pass
            return rsp.text
        except Exception:
            return ""

    def _strip_tags(self, text):
        if not text:
            return ""
        return re.sub(r'<[^>]+>', '', text).strip()

    def _is_direct_media(self, url):
        url = (url or "").lower()
        return ".m3u8" in url or ".mp4" in url or ".flv" in url or ".mkv" in url

    def _is_nav_text(self, text):
        t = text.lower().strip()
        if len(t) < 3 or len(t) > 80:
            return True
        for kw in self.NAV_KEYWORDS:
            if kw in t:
                return True
        return False

    # ========== 首页 ==========
    def homeContent(self, filter):
        return {
            "class": self.classes,
            "filters": {},
        }

    def homeVideoContent(self):
        now = int(time.time())
        if self._home_cache and now - self._home_cache_time < 300:
            return {"list": self._home_cache[:72]}

        html = self._txt(self.home_url, timeout=25)
        videos = self._parse_video_list(html)
        if len(videos) < 20:
            videos = []
            for cid in ["2", "163", "51", "5"]:
                page_html = self._txt(self._url(f"/t/{cid}/"), timeout=20)
                videos.extend(self._parse_video_list(page_html))
                if len(videos) >= 72:
                    break

        self._home_cache = videos[:72]
        self._home_cache_time = now
        return {"list": self._home_cache}

    # ========== 分类列表 ==========
    def categoryContent(self, tid, pg, filter, extend):
        if str(pg) == "1":
            url = self._url(f"/t/{tid}/")
        else:
            url = self._url(f"/t/{tid}-{pg}/")

        html = self._txt(url, referer=self.host + '/', timeout=30)
        videos = self._parse_video_list(html)

        pagecount = 99
        last_match = re.search(r'/t/' + re.escape(str(tid)) + r'/page_(\d+)/', html)
        if not last_match:
            last_match = re.search(r'/t/' + re.escape(str(tid)) + r'/\d+-(\d+)/', html)
        if last_match:
            pagecount = int(last_match.group(1))

        return {
            "list": videos,
            "page": pg,
            "pagecount": pagecount,
            "limit": 20,
            "total": pagecount * 20,
        }

    # ========== 搜索 ==========
    def searchContent(self, key, quick, pg="1"):
        url = self._url(f"/sa.html?wd={key}")
        html = self._txt(url, referer=self.host + '/', timeout=30)
        videos = self._parse_video_list(html)

        return {
            "list": videos,
            "page": pg,
            "pagecount": 10,
            "limit": 20,
            "total": len(videos),
        }

    # ========== 详情页 ==========
    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        vod_id = ids[0]

        url = self.host + vod_id if vod_id.startswith('/voddetail/') else self._url(vod_id)
        html = self._txt(url, referer=self.host + '/', timeout=30)

        vod = self._parse_detail(html, vod_id)
        return {"list": [vod]}

    # ========== 播放解析 ==========
    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {"parse": 1, "playUrl": "", "url": ""}

        url = id if str(id).startswith("http") else self._url(id)

        if self._is_direct_media(url):
            return {
                "parse": 0, "playUrl": "", "url": url,
                "header": dict(self.header),
                "format": "application/x-mpegURL" if ".m3u8" in url else "",
                "contentType": "application/x-mpegURL" if ".m3u8" in url else "",
            }

        html = self._txt(url, referer=self.host + '/', timeout=30)

        real_url = ""
        # 1. player_aaaa 变量
        m = re.search(r"var\s+player_[a-zA-Z0-9_]+\s*=\s*(\{.*?\})\s*</script>", html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                real_url = data.get("url", "")
                encrypt = data.get("encrypt", 0)
                if encrypt in [1, 2, 3] and real_url:
                    try:
                        if encrypt == 3:
                            pad = 4 - len(real_url) % 4
                            if pad != 4:
                                real_url += '=' * pad
                            decoded = base64.b64decode(real_url).decode("utf-8", errors="ignore")
                            m_url = re.search(r'(https?://[^\s\x00-\x1f<>"\x27]+)', decoded)
                            real_url = m_url.group(1) if m_url else decoded
                        else:
                            real_url = base64.b64decode(real_url).decode("utf-8", errors="ignore")
                    except Exception:
                        pass
                real_url = real_url.replace("\\/", "/")
            except Exception:
                pass

        # 2. iframe 嵌套
        if not real_url:
            m2 = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
            if m2:
                iframe_url = self._url(m2.group(1))
                iframe_html = self._txt(iframe_url, referer=url, timeout=30)
                real_url = re.search(r'"url"\s*:\s*"([^"]+)"', iframe_html)
                real_url = real_url.group(1) if real_url else ""

        # 3. 全局 m3u8/mp4 匹配
        if not real_url:
            m3 = re.search(r'["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', html, re.I)
            if m3:
                real_url = m3.group(1)

        if real_url:
            return {
                "parse": 0, "playUrl": "", "url": real_url,
                "header": {
                    "User-Agent": self.header["User-Agent"],
                    "Referer": url,
                },
                "format": "application/x-mpegURL" if ".m3u8" in real_url else "",
                "contentType": "application/x-mpegURL" if ".m3u8" in real_url else "",
            }

        return {"parse": 1, "playUrl": "", "url": url, "header": dict(self.header)}

    def localProxy(self, param):
        return [200, "video/MP2T", b"", ""]

    def destroy(self):
        pass

    def close(self):
        self.destroy()

    # ========== 列表解析 ==========
    def _parse_video_list(self, html):
        videos = []
        seen = set()
        if not html:
            return videos

        items = re.findall(
            r'<a[^>]*href=["\'](/voddetail/\d+/)["\'][^>]*>(.*?)</a>',
            html, re.S
        )
        for href, inner in items:
            if href in seen:
                continue

            # 必须包含图片才是影片卡片
            if not re.search(r'<img[^>]+>', inner, re.I):
                continue

            # 提取标题（多级 fallback）
            title = ""

            # 1) 从 <a> 标签本身的 title 属性获取
            a_tag_match = re.search(
                r'<a[^>]*href=["\']' + re.escape(href) + r'["\'][^>]*title=["\']([^"\']+)["\']',
                html, re.I
            )
            if a_tag_match:
                title = a_tag_match.group(1).strip()

            # 2) 从 <img> 的 alt 属性获取
            if not title:
                alt_match = re.search(r'<img[^>]+alt=["\']([^"\']+)["\']', inner, re.I)
                if alt_match:
                    title = alt_match.group(1).strip()

            # 3) 从 <img> 的 title 属性获取
            if not title:
                title_match = re.search(r'<img[^>]+title=["\']([^"\']+)["\']', inner, re.I)
                if title_match:
                    title = title_match.group(1).strip()

            # 4) 从纯文本获取，清理空白
            if not title:
                text = self._strip_tags(inner)
                text = re.sub(r'\s+', ' ', text).strip()
                text = re.sub(r'^\d{4}-\d{2}-\d{2}\s*', '', text)
                text = re.sub(r'^[A-Z]{2,}\s*', '', text)
                title = text.strip()

            # 过滤不合理的标题
            if not title or len(title) < 4 or len(title) > 100:
                continue
            if self._is_nav_text(title):
                continue

            # 提取封面
            img = ""
            img_match = re.search(r'data-original=["\']([^"\']+)["\']', inner)
            if img_match:
                img = img_match.group(1)
            if not img:
                img_match = re.search(r'src=["\']([^"\']+)["\']', inner)
                if img_match:
                    img = img_match.group(1)
            if not img:
                bg_match = re.search(r'background-image:\s*url\(["\']?([^"\'()]+)', inner)
                if bg_match:
                    img = bg_match.group(1)

            if img and not img.startswith('http'):
                img = self._url(img)

            seen.add(href)
            videos.append({
                "vod_id": href,
                "vod_name": title,
                "vod_pic": img,
            })
            if len(videos) >= 80:
                break

        # 兜底
        if len(videos) < 5:
            blocks = re.findall(
                r'href=["\'](/voddetail/\d+/)["\']',
                html
            )
            for href in blocks:
                if href in seen:
                    continue
                seen.add(href)
                title_match = re.search(
                    r'href=["\']' + re.escape(href) + r'["\'][^>]*>([^<]+)',
                    html
                )
                videos.append({
                    "vod_id": href,
                    "vod_name": self._strip_tags(title_match.group(1)) if title_match else href,
                    "vod_pic": "",
                })
                if len(videos) >= 80:
                    break

        return videos

    # ========== 详情页解析 ==========
    def _parse_detail(self, html, vod_id):
        vod = {
            "vod_id": vod_id,
            "vod_name": "",
            "vod_pic": "",
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            "vod_play_from": "",
            "vod_play_url": "",
        }

        # 标题：h1 标签
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if h1_match:
            vod["vod_name"] = self._strip_tags(h1_match.group(1))

        # 封面：多级 fallback
        img_match = re.search(
            r'<img[^>]+(?:src|data-original)=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp))["\']',
            html, re.I
        )
        if img_match:
            vod["vod_pic"] = img_match.group(1)
        if not vod["vod_pic"]:
            img_match = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', html, re.I)
            if img_match:
                vod["vod_pic"] = img_match.group(1)
        if not vod["vod_pic"]:
            bg_match = re.search(r'background-image:\s*url\(["\']?([^"\'()]+)', html, re.I)
            if bg_match:
                vod["vod_pic"] = bg_match.group(1)

        # 简介
        content_match = re.search(
            r'class=["\'][^"\']*(?:content|desc|intro|summary|detail)["\'][^>]*>(.*?)</div>',
            html, re.S
        )
        if content_match:
            vod["vod_content"] = self._strip_tags(content_match.group(1))[:500]

        # ===== 播放链接 =====
        play_from = []
        play_url_parts = []

        # 策略1：从 player_aaaa 提取
        players = re.findall(
            r"var\s+player_[a-zA-Z0-9_]+\s*=\s*(\{.*?\})\s*</script>",
            html, re.S
        )
        if players:
            play_from.append("默认线路")
            ep_list = []
            for idx, p in enumerate(players):
                try:
                    data = json.loads(p)
                    url_val = data.get("url", "")
                    if url_val:
                        encrypt = data.get("encrypt", 0)
                        if encrypt in [1, 2, 3]:
                            try:
                                if encrypt == 3:
                                    pad = 4 - len(url_val) % 4
                                    if pad != 4:
                                        url_val += '=' * pad
                                    decoded = base64.b64decode(url_val).decode("utf-8", errors="ignore")
                                    m_url = re.search(r'(https?://[^\s\x00-\x1f<>"\x27]+)', decoded)
                                    url_val = m_url.group(1) if m_url else decoded
                                else:
                                    url_val = base64.b64decode(url_val).decode("utf-8", errors="ignore")
                            except Exception:
                                pass
                        url_val = url_val.replace("\\/", "/")
                        ep_list.append(f"播放${url_val}")
                except Exception:
                    pass
            if not ep_list:
                ep_list = [f"播放{vod_id}$"]
            play_url_parts.append("#".join(ep_list))

        # 策略2：从 iframe 中提取播放页
        iframes = re.findall(
            r'<iframe[^>]+src=["\']([^"\']+)["\']', html
        )
        if iframes and not play_from:
            play_from.append("默认线路")
            ep_list = []
            for iframe_url in iframes[:10]:
                abs_url = self._url(iframe_url) if not iframe_url.startswith('http') else iframe_url
                ep_list.append(f"播放${abs_url}")
            play_url_parts.append("#".join(ep_list))

        # 策略2.5：提取 /v/{id}/ 播放页链接
        if not play_from:
            play_btn = re.search(r'href=["\'](/v/\d+/)["\']', html)
            if play_btn:
                play_from.append("默认线路")
                play_url_parts.append(f"播放${self._url(play_btn.group(1))}")

        # 策略3：从 a 标签中找播放链接
        play_links = re.findall(
            r'href=["\']([^"\']+)["\'][^>]*>([^<]*播[^<]*<|[^<]*集[^<]*<|[^<]*观看[^<]*)',
            html, re.I
        )
        if play_links and not play_from:
            play_from.append("默认线路")
            ep_list = []
            for href, text in play_links:
                if self._is_direct_media(href):
                    ep_list.append(f"播放${href}")
                else:
                    abs_url = self._url(href) if not href.startswith('http') else href
                    ep_list.append(f"{self._strip_tags(text)}${abs_url}")
            if ep_list:
                play_url_parts.append("#".join(ep_list))

        # 兜底
        if not play_from:
            play_from.append("默认线路")
            play_url_parts.append(f"播放${vod_id}")

        vod["vod_play_from"] = "$$$".join(play_from)
        vod["vod_play_url"] = "$$$".join(play_url_parts)

        return vod
