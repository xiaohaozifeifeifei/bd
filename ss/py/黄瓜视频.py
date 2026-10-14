# -*- coding: utf-8 -*-
"""
黄瓜视频 Python Spider - 全分类版
兼容 FongMi/TV (T3) 和 WebHomeTV/PeekPro (T4) 双壳子
基于 API: https://xmhk.7wzx9.com/forward
"""
import sys
import json

sys.path.append('..')

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


class Spider(Spider):
    API_URL = "https://xmhk.7wzx9.com/forward"
    HOST = "https://www.88xff.com"

    CATEGORIES = [
        {"type_id": "1", "type_name": "传媒"},
        {"type_id": "2", "type_name": "视频"},
        {"type_id": "3", "type_name": "电影"},
        {"type_id": "6", "type_name": "91传媒"},
        {"type_id": "7", "type_name": "精东传媒"},
        {"type_id": "8", "type_name": "麻豆传媒"},
        {"type_id": "9", "type_name": "麻豆映画"},
        {"type_id": "10", "type_name": "麻豆猫爪"},
        {"type_id": "11", "type_name": "蜜桃传媒"},
        {"type_id": "12", "type_name": "天美传媒"},
        {"type_id": "13", "type_name": "星空传媒"},
        {"type_id": "14", "type_name": "偷拍自拍"},
        {"type_id": "15", "type_name": "日韩视频"},
        {"type_id": "16", "type_name": "欧美性爱"},
        {"type_id": "17", "type_name": "智能换脸"},
        {"type_id": "18", "type_name": "经典三级"},
        {"type_id": "19", "type_name": "网红主播"},
        {"type_id": "20", "type_name": "台湾辣妹"},
        {"type_id": "21", "type_name": "onlyfans"},
        {"type_id": "22", "type_name": "中文字幕"},
        {"type_id": "23", "type_name": "经典素人"},
        {"type_id": "24", "type_name": "高清无码"},
        {"type_id": "25", "type_name": "美颜巨乳"},
        {"type_id": "26", "type_name": "丝袜制服"},
        {"type_id": "27", "type_name": "SM系列"},
        {"type_id": "28", "type_name": "欧美系列"},
        {"type_id": "29", "type_name": "H動畫"},
    ]

    def getName(self):
        return "黄瓜视频"

    def init(self, extend=""):
        if isinstance(extend, list):
            self.extend = ''
        else:
            self.extend = extend or ''

        self.header = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36',
            'Referer': self.HOST + '/',
        }
        self._api_header = {
            'User-Agent': self.header['User-Agent'],
            'Content-Type': 'application/json',
            'Referer': self.HOST + '/',
        }
        self._domains = {}

    def homeContent(self, filter):
        result = {"class": self.CATEGORIES}
        if filter:
            result["filters"] = {}
        return result

    def homeVideoContent(self):
        videos = []
        seen = set()
        # 取前3个分类的数据做精选
        for cat in self.CATEGORIES[:3]:
            items = self._api_list(cat["type_id"], 1, 10)
            for it in items:
                vid = str(it.get("id", ""))
                if vid and vid not in seen:
                    seen.add(vid)
                    videos.append(self._build_vod(it))
        return {"list": videos[:72]}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        data = self._api_post({
            "command": "WEB_GET_INFO",
            "pageNumber": page, "RecordsPage": 20,
            "typeId": int(tid), "typeMid": 1,
            "languageType": "CN", "content": "",
        })
        items = []
        pagecount = 1
        if data.get("errorCode") == "0":
            d = data.get("data", {})
            items = d.get("resultList", [])
            pagecount = d.get("pageAllNumber", 1)
        videos = [self._build_vod(it) for it in items if it.get("id")]
        return {
            "list": videos, "page": page,
            "pagecount": pagecount, "limit": 20,
            "total": pagecount * 20,
        }

    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        vod_id = ids[0]
        data = self._api_post({
            "command": "WEB_GET_INFO_DETAIL",
            "type_Mid": 1, "id": int(vod_id),
            "languageType": "CN",
        })
        if data.get("errorCode") != "0":
            return {"list": []}
        result = data.get("data", {}).get("result", {})
        vid = str(result.get("id", vod_id))
        vod_name = result.get("vod_name", "")
        pic = result.get("vod_pic", "")
        sid = result.get("vod_server_id", 18)
        vod_url = result.get("vod_url", "")
        vod_time = result.get("vod_time_add", "")
        type_name = result.get("typeName", "")

        play_url_str = ""
        if vod_url:
            full = self._full_url(vod_url, sid)
            play_url_str = f"播放${full}"

        vod = {
            "vod_id": vid,
            "vod_name": vod_name,
            "vod_pic": self._full_pic(pic, sid),
            "type_name": type_name,
            "vod_year": vod_time[:4] if vod_time else "",
            "vod_area": "", "vod_remarks": "",
            "vod_actor": "", "vod_director": "", "vod_content": "",
            "vod_play_from": "默认线路",
            "vod_play_url": play_url_str,
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        videos = []
        seen = set()
        for cat in self.CATEGORIES:
            items = self._api_list(cat["type_id"], 1, 50)
            for it in items:
                name = it.get("vod_name", "")
                if key.lower() in name.lower():
                    vid = str(it.get("id", ""))
                    if vid and vid not in seen:
                        seen.add(vid)
                        videos.append(self._build_vod(it))
                    if len(seen) >= 50:
                        break
            if len(seen) >= 50:
                break
        return {"list": videos, "page": 1, "pagecount": 1, "limit": 20, "total": len(videos)}

    def playerContent(self, flag, id, vipFlags):
        url = id if str(id).startswith("http") else self._url(id)
        return {"parse": 0, "playUrl": "", "url": url, "header": self.header}

    def localProxy(self, param):
        return [200, "video/MP2T", b"", ""]

    def destroy(self):
        pass
    def close(self):
        self.destroy()

    # ========== API ==========
    def _api_post(self, data_dict):
        try:
            data = json.dumps(data_dict).encode('utf-8')
            import urllib.request
            req = urllib.request.Request(self.API_URL, data=data, headers=self._api_header, method='POST')
            resp = urllib.request.urlopen(req, timeout=20)
            return json.loads(resp.read().decode('utf-8'))
        except Exception:
            return {"errorCode": "-1"}

    def _api_list(self, tid, page, limit):
        data = self._api_post({
            "command": "WEB_GET_INFO", "pageNumber": page,
            "RecordsPage": limit, "typeId": int(tid),
            "typeMid": 1, "languageType": "CN", "content": "",
        })
        if data.get("errorCode") == "0":
            return data.get("data", {}).get("resultList", [])
        return []

    # ========== 工具 ==========
    def _build_vod(self, it):
        sid = it.get("vod_server_id", 18)
        pic = it.get("vod_pic", "")
        return {
            "vod_id": str(it.get("id", "")),
            "vod_name": it.get("vod_name", ""),
            "vod_pic": self._full_pic(pic, sid),
            "vod_remarks": "",
        }

    def _get_domain(self, sid):
        if sid in self._domains:
            return self._domains[sid]
        for cat in self.CATEGORIES:
            items = self._api_list(cat["type_id"], 1, 30)
            for it in items:
                s = it.get("vod_server_id")
                p = it.get("vod_pic", "")
                if s and p and p.startswith("http"):
                    import re
                    m = re.match(r'(https?://[^/]+)', p)
                    if m:
                        self._domains[s] = m.group(1)
        if sid in self._domains:
            return self._domains[sid]
        return "https://eu7tu.shuma5588.com"

    def _full_pic(self, path, sid=18):
        if not path:
            return ""
        if path.startswith("http"):
            return path
        return self._get_domain(sid) + path

    def _full_url(self, path, sid=18):
        if not path:
            return ""
        if path.startswith("http"):
            return path
        return self._get_domain(sid) + path

    def _url(self, path):
        if path.startswith("http"):
            return path
        return self.HOST + ("/" + path if not path.startswith("/") else path)