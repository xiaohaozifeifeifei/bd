import requests
from bs4 import BeautifulSoup
import re
from base.spider import Spider
import sys
import json
import base64
import urllib.parse

sys.path.append('..')

xurl = "https://leaves-fall-gracefully.777hub129.xyz"
headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
}

class Spider(Spider):
    global xurl
    global headerx

    def getName(self):
        return "首页"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def homeContent(self, filter):
        # 分类
        class_items = [
        {"type_id": "20", "type_name": "国产自拍"},
        {"type_id": "21", "type_name": "网红主播"},
        {"type_id": "22", "type_name": "国产传媒"},
        {"type_id": "23", "type_name": "人妻熟女"},
        {"type_id": "24", "type_name": "探花系列"},
        {"type_id": "25", "type_name": "日本无码"},
        {"type_id": "26", "type_name": "美乳巨乳"},
        {"type_id": "28", "type_name": "强制侵犯"},
        {"type_id": "25", "type_name": "制服诱惑"},
        {"type_id": "29", "type_name": "绝色佳人"},
        {"type_id": "30", "type_name": "风俗泡浴"},
        {"type_id": "31", "type_name": "家庭乱伦"},
        {"type_id": "32", "type_name": "电影解说"},
        {"type_id": "35", "type_name": "少女萝莉"},
        {"type_id": "36", "type_name": "捆绑调教"},
        {"type_id": "38", "type_name": "魔镜系列"},
        {"type_id": "39", "type_name": "时间停止"},
        {"type_id": "40", "type_name": "催眠洗脑"},
        {"type_id": "41", "type_name": "漫改系列"},
        {"type_id": "42", "type_name": "电车痴汉"},
        {"type_id": "43", "type_name": "淫欲痴女"},
        {"type_id": "44", "type_name": "明星换脸"},
        {"type_id": "45", "type_name": "网曝事件"},
        {"type_id": "46", "type_name": "人妖专区"},
        {"type_id": "47", "type_name": "女性系列"},
        {"type_id": "49", "type_name": "男同性恋"},
        {"type_id": "48", "type_name": "女同性恋"},
        {"type_id": "50", "type_name": "欧美精品"},
        {"type_id": "51", "type_name": "日本动漫"},
        {"type_id": "52", "type_name": "立体动漫"},
        {"type_id": "53", "type_name": "韩国主播"},
        {"type_id": "54", "type_name": "泰国风情"},
        {"type_id": "55", "type_name": "OnlyFans"}
    ]
        
        # 筛选
        static_filters = {}
        
        return {
            "class": class_items,
            "filters": static_filters
        }
        # 数组
    def homeVideoContent(self):
        #请求数据
        源码 = BeautifulSoup(requests.get(url=xurl, headers=headerx).text, "lxml")
        #print(源码)
        
        # 查找所有视频列表
        二次截取 = 源码.find_all('div')
        
        # 遍历数据
        videos = []
        for 数组 in 二次截取:
            数组 = 数组.find_all('div', class_="list")
            #print(数组)
        
        # 遍历数据
            for 数组 in 数组:
                # 获取标题
                标题 = 数组.find('img')['alt']
                #print(标题)
                
                # 获取链接
                链接 = 数组.find('a')['href']
                #print(链接)
                
                # 获取封面
                图片 = 数组.find('img')['data-src']
                if 'http' not in 图片:
                    图片 = xurl + 图片  # 补全封面URL
                #print(图片)
                
                # 获取副标题
                副标题标签 = 数组.find('div', class_="info")
                if 副标题标签 is not None:
                 副标题 = 副标题标签.text.strip()
                else:
                 副标题 = ""
                #print(副标题)
                
                video = {
                          "vod_id": 链接,
                          "vod_name": 标题,
                          "vod_pic": 图片,
                          "vod_remarks": 副标题
                                     }
                videos.append(video)
                #print(video)
                
        result = {'list': videos}
        return result
        # 链接
    def categoryContent(self, cid, pg, filter, ext):
        page = int(pg) if pg else 1
        cateId = ext.get('cateId', cid) if ext else cid
        
        url = f"{xurl}/label/sort999/index.php/vod/type/id/{cateId}/page/{page}.html"
        
        #请求数据
        resp = requests.get(url, headers=headerx, timeout=10)
        soup = BeautifulSoup(resp.text, 'lxml')
        
        # 查找所有视频列表
        二次截取 = soup.find_all('div')
        
        # 遍历数据
        videos = []
        for 数组 in 二次截取:
            数组 = 数组.find_all('div', class_="list")
        
        # 遍历数据
            for 数组 in 数组:
                # 获取标题
                标题 = 数组.find('img')['alt']
                
                # 获取链接
                链接 = 数组.find('a')['href']
                
                # 获取封面
                图片 = 数组.find('img')['data-src']
                if 'http' not in 图片:
                    图片 = xurl + 图片  # 补全封面URL
                
                # 获取副标题
                副标题标签 = 数组.find('div', class_="info")
                if 副标题标签 is not None:
                 副标题 = 副标题标签.text.strip()
                else:
                 副标题 = ""
                
                video = {
                          "vod_id": 链接,
                          "vod_name": 标题,
                          "vod_pic": 图片,
                          "vod_remarks": 副标题
                                     }
                videos.append(video)
                
        result = {'list': videos}
        result['page'] = pg
        result['pagecount'] = 99
        result['limit'] = 90
        result['total'] = 99
        return result
        # 详情
    def detailContent(self, ids): 
        did = ids[0]
        result = {}
        videos = []
        playurl = ''
        if 'http' not in did:
            did = xurl + did
        # 请求详情页
        源码 = BeautifulSoup(requests.get(url=did, headers=headerx).text, "lxml")
        
        # 初始化VOD字典
        vod = {}
        
        # ========== 提取视频基本信息 ==========
        #视频ID
        vod["vod_id"] = xurl
        
        # 标题
        vod["vod_name"] = 源码.select_one('.des h1').get_text().strip()    
        
        # 封面图
        vod["vod_pic"] = 源码.select_one('img').get('src', '').replace('', '').strip()               
            
        # ========== 提取播放列表 ==========
        
        # 线路
        ktabs = []
        线路数组 = 源码.select('.button')
        for XL in 线路数组:
            线路标题 = XL.get_text()
            线路标题 = re.sub(r'\s*\d+$', '', 线路标题).strip()
            ktabs.append(线路标题)
        vod["vod_play_from"] = '$$$'.join(ktabs)
  
        # 列表
        klists = []
        播放数组 = 源码.select('.button')
        for BF in 播放数组:
            播放列表 = BF.select('a')
            klist = []
            for LB in 播放列表:
                播放标题 = LB.get_text()
                播放链接 = LB.get('href', '')
                剧集 = f'{播放标题}${播放链接}'
                klist.append(剧集)
            # 用#连接同一播放源的剧集
            klists.append('#'.join(klist))
        
        # 用$$$连接不同播放源
        vod["vod_play_url"] = '$$$'.join(klists)
        
        result = {'list': [vod]}
        #print(result)
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}       
        try:
            # 第一步：尝试提取直链播放
            源码 = BeautifulSoup(requests.get(url=xurl + id, headers=headerx).text, "lxml")
            url = re.search(r'var\s+now\s*=\s*"([^"]+)"', str(源码)).group(1)            
            # 正则提取成功，使用直链播放
            result["parse"] = 0
            result["playUrl"] = ''
            result["url"] = url
            result["header"] = headerx
            
        except (AttributeError, Exception):
            # 提取失败（正则未匹配到或请求异常），使用嗅探播放
            result["parse"] = 1
            result["playUrl"] = ''
            result["url"] = xurl + id
            result["header"] = headerx        
        return result
        # 搜索
    def searchContentPage(self, key, quick, page):
        result = {}
        videos = []
        if not page:
            page = '1'
        if page == '1':
            url = f'{xurl}/label/sort999/index.php/vod/search.html?wd={key}'
        else:
            url = f''        
        源码 = BeautifulSoup(requests.get(url=url, headers=headerx).text, "lxml")
        #print(源码)
        
        # 查找所有视频列表
        二次截取 = 源码.find_all('div')
        
        # 遍历数据
        videos = []
        for 数组 in 二次截取:
            数组 = 数组.find_all('div', class_="list")
            #print(数组)
        
        # 遍历数据
            for 数组 in 数组:
                # 获取标题
                标题 = 数组.find('img')['alt']
                #print(标题)
                
                # 获取链接
                链接 = 数组.find('a')['href']
                #print(链接)
                
                # 获取封面
                图片 = 数组.find('img')['data-src']
                if 'http' not in 图片:
                    图片 = xurl + 图片  # 补全封面URL
                #print(图片)
                
                # 获取副标题
                副标题标签 = 数组.find('div', class_="info")
                if 副标题标签 is not None:
                 副标题 = 副标题标签.text.strip()
                else:
                 副标题 = ""
                #print(副标题)
                
                video = {
                          "vod_id": 链接,
                          "vod_name": 标题,
                          "vod_pic": 图片,
                          "vod_remarks": 副标题
                                     }
                videos.append(video)
                #print(video)
                
        result = {'list': videos}
        result['page'] = page
        result['pagecount'] = 60
        result['limit'] = 30
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
    #result = spider.homeVideoContent()
    #print("首页视频内容测试结果：")
    #print(result)

    # 调用分类内容测试
    #category_result = spider.categoryContent("1", "1", {}, {})
    #print("\n分类内容测试结果：")
    #print(category_result)

    # 调用详情内容测试
    #detail_result = spider.detailContent(["/hanjuzaixian/4375.html"])
    #print("\n详情内容测试结果：")
    #print(detail_result)

    # 调用播放内容测试
    player_result = spider.playerContent("m3u8", "/play/4375-1-0.html", {})
    #print("\n播放内容测试结果：")
    print(player_result)

    # 调用搜索内容测试
    #search_result = spider.searchContent("橘子果酱", False)
    # print("\n搜索内容测试结果：")
    #print(search_result)