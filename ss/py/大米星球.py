# -*- coding: utf-8 -*-
# 大米星球爬虫
import re
import sys
import html
from urllib.parse import quote
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        self.host = 'https://dmxq40.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
            'Referer': self.host + '/',
        }

    def getName(self):
        return '大米星球'

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def homeContent(self, filter):
        result = {
            'class': [
                {'type_name': 'Netflix', 'type_id': 'netflix'},
                {'type_name': '电影', 'type_id': '20'},
                {'type_name': '电视剧', 'type_id': '21'},
                {'type_name': '短剧', 'type_id': '36'},
                {'type_name': '动漫', 'type_id': '22'},
                {'type_name': '综艺', 'type_id': '23'},
            ],
            'filters': {},
            'list': []
        }
        try:
            html_text = self.fetch(self.host + '/index/home.html', headers=self.headers).text
            result['list'] = self.get_vod_list(html_text)
        except Exception as e:
            print(f'homeContent 错误: {e}')
        return result

    def homeVideoContent(self):
        try:
            html_text = self.fetch(self.host + '/index/home.html', headers=self.headers).text
            return self.get_vod_list(html_text)
        except:
            return []

    def categoryContent(self, tid, pg, filter, extend):
        result = {
            'list': [],
            'page': pg,
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }
        try:
            if tid == 'netflix':
                url = f'{self.host}/label/netflix.html'
                if int(pg) > 1:
                    url = f'{self.host}/label/netflix-{pg}.html'
            else:
                url = f'{self.host}/vodtype/{tid}.html'
                if int(pg) > 1:
                    url = f'{self.host}/vodtype/{tid}-{pg}.html'
            
            html_text = self.fetch(url, headers=self.headers).text
            result['list'] = self.get_vod_list(html_text)
        except Exception as e:
            print(f'categoryContent 错误: {e}')
        return result

    def detailContent(self, ids):
        result = {'list': []}
        try:
            url = ids[0] if ids[0].startswith('http') else self.host + ids[0]
            html_text = self.fetch(url, headers=self.headers).text
            
            vod = {}
            
            # 标题
            m = re.search(r'<h1[^>]*>([^<]+)</h1>', html_text)
            if m:
                vod['vod_name'] = m.group(1).strip()
            
            # 海报 - 解码HTML实体
            m = re.search(r'data-original="([^"]+)"[^>]*alt="([^"]+)"[^>]*class="module-item-pic"', html_text)
            if not m:
                m = re.search(r'<div class="module-item-pic"[^>]*>.*?<img[^>]+data-original="([^"]+)"', html_text, re.DOTALL)
            if m:
                pic = m.group(1)
                pic = html.unescape(pic)
                vod['vod_pic'] = pic
            
            # 简介
            m = re.search(r'<div class="module-info-introduction-content[^"]*"[^>]*>(.*?)</div>', html_text, re.DOTALL)
            if m:
                desc = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                desc = re.sub(r'\s+', ' ', desc)
                vod['vod_content'] = desc[:500] if desc else ''
            
            # 播放链接
            all_eps = re.findall(r'href="(/vodplay/\d+-(\d+)-(\d+)\.html)"[^>]*><span>([^<]+)</span>', html_text)
            
            if all_eps:
                source_dict = {}
                for href, source_id, episode, ep_name in all_eps:
                    source_id = str(source_id)
                    if source_id not in source_dict:
                        source_dict[source_id] = []
                    full_url = self.host + href
                    source_dict[source_id].append(f"{ep_name}${full_url}")
                
                source_names = re.findall(r'data-dropdown-value="([^"]+)"', html_text)
                
                play_from_list = []
                play_url_list = []
                for i, (sid, episodes) in enumerate(source_dict.items()):
                    if i < len(source_names):
                        name = source_names[i]
                    else:
                        name = f'线路{i+1}'
                    
                    def get_ep_num(x):
                        match = re.search(r'(\d+)', x.split('$')[0])
                        return int(match.group(1)) if match else 0
                    episodes_sorted = sorted(episodes, key=get_ep_num)
                    
                    play_from_list.append(name)
                    play_url_list.append('#'.join(episodes_sorted))
                
                vod['vod_play_from'] = '$$$'.join(play_from_list)
                vod['vod_play_url'] = '$$$'.join(play_url_list)
            else:
                vod['vod_play_from'] = '大米星球'
                vod['vod_play_url'] = ''
            
            result['list'].append(vod)
        except Exception as e:
            print(f'detailContent 错误: {e}')
            import traceback
            traceback.print_exc()
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {
            'list': [],
            'page': pg,
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }
        try:
            if int(pg) == 1:
                url = f'{self.host}/vodsearch/{quote(key)}-------------.html'
            else:
                url = f'{self.host}/vodsearch/{quote(key)}-------------.html?page={pg}'
            
            html_text = self.fetch(url, headers=self.headers).text
            result['list'] = self.get_search_list(html_text)
        except Exception as e:
            print(f'searchContent 错误: {e}')
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {'parse': 0, 'url': '', 'header': {}}
        try:
            play_url = id if id.startswith('http') else self.host + id
            result['url'] = play_url
            result['parse'] = 1
            result['header'] = {'Referer': self.host + '/'}
        except Exception as e:
            print(f'playerContent 错误: {e}')
        return result

    def localProxy(self, param):
        pass

    def liveContent(self, url):
        pass

    def get_vod_list(self, html_text):
        """通用列表提取 - 分类页/首页"""
        videos = []
        seen = set()
        
        # 提取所有链接
        hrefs = re.findall(r'href="(/voddetail/\d+\.html)"', html_text)
        
        # 提取所有图片
        pics = re.findall(r'data-original="([^"]+)"', html_text)
        pics = [html.unescape(p) for p in pics]
        
        # 提取所有标题
        titles = re.findall(r'module-poster-item-title[^>]*>([^<]+)<', html_text)
        
        # 提取副标题（备注）
        notes = re.findall(r'class="module-item-note"[^>]*>([^<]+)<', html_text)
        
        min_len = min(len(hrefs), len(pics), len(titles))
        for i in range(min_len):
            href = hrefs[i]
            pic = pics[i]
            title = titles[i].strip()
            remark = notes[i].strip() if i < len(notes) else ''
            
            m = re.search(r'/voddetail/(\d+)\.html', href)
            if not m:
                continue
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            
            full_url = self.host + href
            if title:
                videos.append({
                    'vod_id': full_url,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': remark
                })
        
        return videos

    def get_search_list(self, html_text):
        """搜索结果页提取"""
        videos = []
        seen = set()
        
        # 分割成单个卡片
        cards = re.split(r'(?=<div class="module-card-item module-item">)', html_text)
        
        for card in cards:
            if '<div class="module-card-item' not in card:
                continue
            
            # 提取详情链接
            detail_links = re.findall(r'href="(/voddetail/\d+\.html)"[^>]+class="[^"]*module-card-item-poster"', card)
            if not detail_links:
                detail_links = re.findall(r'<a href="(/voddetail/\d+\.html)" class="module-card-item-poster"', card)
            
            if not detail_links:
                continue
            href = detail_links[0]
            
            # 提取图片
            pics = re.findall(r'data-original="([^"]+)"', card)
            pic = html.unescape(pics[0]) if pics else ''
            
            # 提取标题 - 从strong标签，并清理<em>标签
            titles = re.findall(r'<strong>(.*?)</strong>', card, re.DOTALL)
            if titles:
                # 移除<em>标签
                title = re.sub(r'<[^>]+>', '', titles[0]).strip()
            else:
                title = ''
            
            # 提取副标题
            notes = re.findall(r'class="module-item-note"[^>]*>([^<]+)<', card)
            remark = notes[0].strip() if notes else ''
            
            # 提取分类
            classes = re.findall(r'class="module-card-item-class"[^>]*>([^<]+)<', card)
            cat = classes[0].strip() if classes else ''
            
            # 如果备注为空，用分类代替
            if not remark and cat:
                remark = cat
            
            # 提取ID
            m = re.search(r'/voddetail/(\d+)\.html', href)
            if not m:
                continue
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            
            full_url = self.host + href
            if title:
                videos.append({
                    'vod_id': full_url,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': remark
                })
        
        print(f"[DEBUG] search: 提取到 {len(videos)} 个结果")
        return videos