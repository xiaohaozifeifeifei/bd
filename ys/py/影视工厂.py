import requests
from bs4 import BeautifulSoup
import re
from base.spider import Spider
import sys
import json
import base64
import urllib.parse

sys.path.append('..')

xurl = "https://www.iysgc.com"
headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
}

def getList(html):
    videos = []    
    源码 = BeautifulSoup(html, "lxml")
    二次截取 = 源码.select('div.border-box, div.row-right')
    for 数组 in 二次截取:
        数组 = 数组.find_all('div', class_="public-list-box")
        for 影片 in 数组:
            vod = {}
            vod["vod_name"] = (影片.find('a').get('title','') if 影片.find('a') else '') + (影片.find('div',class_='thumb-txt').text.strip() if 影片.find('div',class_='thumb-txt') else '')
            vod["vod_id"] = 影片.find('a')['href']
            vod["vod_pic"] = 影片.find('img')['data-src']
            if 'http' not in vod["vod_pic"]:
                vod["vod_pic"] = xurl + vod["vod_pic"]
            vod["vod_remarks"] = 影片.find('span', class_="ft2").text.strip()     
            videos.append(vod)
    return videos

def 提取演员(元素):
    if not 元素:
        return []    
    链接们 = 元素.find_all('a')
    if 链接们:
        演员列表 = []
        for 链接 in 链接们:
            文本 = 链接.get_text(strip=True)
            if 文本 and len(文本) > 0:
                演员列表.append(文本)
        if 演员列表:
            return 演员列表    
    文本 = 元素.get_text(strip=True)
    文本 = 文本.replace('主演：', '').replace('导演：', '').strip()    
    for 分隔符 in ['/', '、', ',', '，']:
        文本 = 文本.replace(分隔符, '|')    
    演员列表 = []
    for 演员 in 文本.split('|'):
        演员 = 演员.strip()
        if 演员 and len(演员) > 0:
            演员列表.append(演员)    
    return 演员列表

def 拼接演员(演员列表):
    if not 演员列表 or len(演员列表) == 0:
        return ''    
    部分列表 = []
    for 演员 in 演员列表:
        if 演员 and len(演员) > 0:
            标签 = f'[a=cr:{{"id":"search://{演员}","name":"{演员}"}}/]{演员}[/a]'
            部分列表.append(标签)    
    return ' '.join(部分列表)

class Spider(Spider):
    global xurl
    global headerx

    def getName(self):
        return "首页"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def localProxy(self, params):
        pass

    def homeContent(self, filter):
        result = {}
        result = {"class": [
        {"type_id": "1","type_name": "电影"},
        {"type_id": "2","type_name": "电视剧"},
        {"type_id": "3","type_name": "综艺"},
        {"type_id": "4","type_name": "动漫"},    
        {"type_id": "5","type_name": "短剧"}]}
        return result

    def homeVideoContent(self):
        resp = requests.get(url=xurl, headers=headerx).text
        result = {'list': getList(resp)}
        return result

    def categoryContent(self, cid, pg, filter, ext):
        result = {}       
        if isinstance(cid, str) and cid.startswith('search://'):
            关键词 = cid.replace('search://', '')
            url = f'{xurl}/vodsearch/-{关键词}---------{pg}---.html'
        else:
            url = f'{xurl}/vodshow/{cid}--------{pg}---.html'        
        resp = requests.get(url=url, headers=headerx).text
        result = {'list': getList(resp)}
        result['page'] = pg
        result['pagecount'] = 99
        result['limit'] = 90
        result['total'] = 99
        return result

    def detailContent(self, ids):    
        did = ids[0]
        result = {}
        videos = []
        if 'http' not in did:
            did = xurl + did
        源码 = BeautifulSoup(requests.get(url=did, headers=headerx).text, "lxml")
        vod = {}
        vod["vod_id"] = did
        vod["vod_name"] = 源码.select_one('h3').get_text()
        vod["type_name"] = ' '.join(提取演员(源码.select_one('.gen-search-form li:-soup-contains("类型：")')))
        vod["vod_pic"] = 源码.select_one('.detail-pic img').get('data-src', '') or 源码.select_one('.detail-pic img').get('src', '')
        vod["vod_remarks"] = 源码.select_one('.gen-search-form li:-soup-contains("状态：")').get_text().replace('状态：', '').strip()
        vod["vod_year"] = 源码.select_one('.gen-search-form li:-soup-contains("年份：")').get_text().replace('年份：', '').strip()
        vod["vod_area"] = 源码.select_one('.gen-search-form li:-soup-contains("地区：")').get_text().replace('地区：', '').strip()
        vod["vod_director"] = 拼接演员(提取演员(源码.select_one('.gen-search-form li:-soup-contains("导演：")')))
        vod["vod_actor"] = 拼接演员(提取演员(源码.select_one('.gen-search-form li:-soup-contains("主演：")')))
        vod["vod_content"] = 源码.select_one('.top26').get_text().replace('简介：','')
        ktabs = []
        线路数组 = 源码.select('.anthology-tab a')
        for XL in 线路数组:
            线路标题 = XL.get_text()
            线路标题 = re.sub(r'\s+', '', 线路标题)
            线路标题 = re.sub(r'([^\d]+)(\d+)', r'\1共\2集', 线路标题)
            ktabs.append(线路标题)
        vod["vod_play_from"] = '$$$'.join(ktabs)

        klists = []
        播放数组 = 源码.select('.anthology-list-play')
        for BF in 播放数组:
            播放列表 = BF.select('a')
            klist = []
            for LB in 播放列表:
                播放标题 = LB.get_text()
                播放链接 = LB.get('href', '')
                剧集 = f'{播放标题}${播放链接}'
                klist.append(剧集)
            klists.append('#'.join(klist))
        vod["vod_play_url"] = '$$$'.join(klists)
        result = {'list': [vod]}
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}       
        try:
            源码 = BeautifulSoup(requests.get(url=xurl + id, headers=headerx).text, "lxml")
            url = re.search('},"url":"(.*?)"', str(源码)).group(1)            
            if 'm3u8' in url:
                result["parse"] = 0
                result["url"] = url
            else:
                result["parse"] = 1
                result["url"] = xurl + id  
        except (AttributeError, Exception):
            result["parse"] = 1
            result["url"] = xurl + id
        result["header"] = headerx
        return result

    def searchContent(self, key, quick, page=1):
        result = {}
        url = f'{xurl}/vodsearch/{key}----------{page}---.html'
        resp = requests.get(url=url, headers=headerx).text
        result = {'list': getList(resp)}
        result['page'] = page
        result['pagecount'] = 60
        result['limit'] = 30
        result['total'] = 999999
        return result

    def searchContentPage(self, key, quick, page):
        return self.searchContent(key, quick, page)

if __name__ == "__main__":
    spider = Spider()
    spider.init("")

    # 调用首页视频内容测试
    #res = spider.homeVideoContent()

    # 调用分类内容测试
    #res = spider.categoryContent("1", "1", {}, {})

    # 调用详情内容测试
    #res = spider.detailContent(["/voddetail/171686.html"])    

    # 调用播放内容测试
    #res = spider.playerContent("m3u8", "/vodplay/171686-7-1.html", {})

    # 调用搜索内容测试
    #res = spider.searchContent("仙逆", False)
    #print(json.dumps(res, ensure_ascii=False, indent=2))        