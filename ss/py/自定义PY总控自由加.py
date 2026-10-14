# coding=utf-8
# ################################################################
# 自定义 PY 总控源
#   惰性加载 · 多级兼容 · 分源自定义封面 · 多目录扫描 · 卡片墙选源
#
# 封面键名两种都支持：
#   1基命名：pic1 = 二级封面，pic2 = 三级封面
#   2基命名：pic2 = 二级封面，pic3 = 三级封面
#   （配置里一旦出现 pic1，就按 1 基命名解析）
# ################################################################

import sys
sys.path.append('..')
from base.spider import Spider


# ================================================================
# ========================  可修改项 A：手动源列表  ================
# ================================================================
# 【字符串写法】"源名,py路径,二级封面,三级封面"（后两段可省）
# 【字典写法】键名二选一：
#     1基：{"name":..., "path":..., "pic1":"二级图", "pic2":"三级图"}
#     2基：{"name":..., "path":..., "pic2":"二级图", "pic3":"三级图"}
# ================================================================
EXTERNAL_PY_SOURCES = [
    # "洛雪TV,/storage/emulated/0/Download/洛雪TV.py",
    # "追影,/storage/emulated/0/Download/追影.py,/sdcard/pic/2.jpg,/sdcard/pic/3.jpg",
]


# ================================================================
# ====================  可修改项 B：基础目录  ====================
# ================================================================
BASE_DIR = ""


# ================================================================
# ====================  可修改项 C：总控名称  ====================
# ================================================================
SPIDER_NAME = "PY总控"


# ================================================================
# ==========  可修改项 E：自动扫描目录（支持多个）  ===============
# ================================================================
# 可以填任意多个目录，每个目录两种写法：
#
#   ① 只写路径：
#        "/storage/emulated/0/Download/WeiXin"
#        → 源名 = 文件名（如 洛雪TV.py 显示为「洛雪TV」）
#
#   ② 路径 + 分组名前缀，中间用竖线 | 隔开：
#        "/storage/emulated/0/Download/短剧库|短剧"
#        → 源名 = "短剧·文件名"（如 好看.py 显示为「短剧·好看」）
#
# ------------------------------------------------------------------
# ▼▼▼ 第一个路径的详细示例（照着改就行）▼▼▼
# ------------------------------------------------------------------
#
# 【示例1】只扫一个目录，源名用文件名：
#     SCAN_DIRS = [
#         "/storage/emulated/0/Download/WeiXin",
#     ]
#
# 【示例2】扫两个目录，都不加前缀：
#     SCAN_DIRS = [
#         "/storage/emulated/0/Download/WeiXin",
#         "/storage/emulated/0/Download/备用库",
#     ]
#     （若两个目录有同名 py，会出现两个同名源，建议用示例3）
#
# 【示例3】扫多个目录，每个加分组前缀，避免同名混淆（推荐）：
#     SCAN_DIRS = [
#         "/storage/emulated/0/Download/WeiXin",
#         "/storage/emulated/0/Download/短剧库|短剧",
#         "/storage/emulated/0/Download/动漫库|动漫",
#         "/storage/emulated/0/Download/备用库|备用",
#     ]
#     显示效果：
#         WeiXin 里的 洛雪TV.py        →  「洛雪TV」    （无前缀）
#         短剧库里的 好看.py            →  「短剧·好看」
#         动漫库里的 好看.py            →  「动漫·好看」
#         备用库里的 备份.py            →  「备用·备份」
#
# 【示例4】相对路径（相对本总控文件所在目录）：
#     SCAN_DIRS = [
#         "./sources",
#         "./sources/短剧|短剧",
#     ]
#
# ------------------------------------------------------------------
# ▼▼▼ 下面填你自己的 ▼▼▼
# ================================================================
SCAN_DIRS = [
   # "/storage/emulated/0/Download",
     "/storage/emulated/0/本地包/ss/py",
     "/storage/emulated/0/本地包/ys/py",
]

# ★ 是否连子文件夹一起扫：
#     True  = 递归扫所有子文件夹（含几层都行）
#     False = 只扫本层
SCAN_RECURSIVE = True

# 扫描时跳过的文件名（不含 .py）。本总控文件自身自动跳过。
# 支持多个目录共用一个排除表；同名文件在任何目录里都会被跳过。
SCAN_EXCLUDE = [
    "__init__", "base", "spider", "main", "config",
]


# ================================================================
# ====================  可修改项 F：选源入口  ====================
# ================================================================
SELECT_ENTRY_NAME = "全部源"
ALSO_LIST_SOURCES = False


# ================================================================
# 以下为自动逻辑，一般不需要修改
# ================================================================

import os
import re
import traceback
import importlib.util

_SOURCE_LIST = None
_SRC_CACHE = {}
_LOAD_ERRORS = {}

ENTRY_TID = "srcsel"


def _resolve_path(path):
    path = (path or "").strip()
    if not path:
        return ""
    if os.path.isabs(path):
        return path
    base = (BASE_DIR or "").strip()
    if not base:
        try:
            base = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            base = os.getcwd()
    return os.path.normpath(os.path.join(base, path))


def _norm_key(path):
    try:
        return os.path.normpath(os.path.abspath(path))
    except Exception:
        return str(path or "")


def _pic_uri(p):
    """把封面路径转成客户端能识别的 URI。空返回空。"""
    p = (p or "").strip()
    if not p:
        return ""
    if p.startswith(("http://", "https://", "file://",
                     "data:", "content://", "assets://")):
        return p
    if os.path.isabs(p):
        return "file://" + p
    return p


def _extract_pics_from_dict(item):
    """从字典里取 (二级封面, 三级封面)，兼容 1 基/2 基命名。"""
    p1 = (item.get("pic1") or "").strip()
    p2 = (item.get("pic2") or "").strip()
    p3 = (item.get("pic3") or "").strip()
    if p1:
        return p1, p2       # 1 基：pic1=二级, pic2=三级
    return p2, p3           # 2 基：pic2=二级, pic3=三级


def _parse_source_item(item):
    """解析一条源配置，返回 (name, path, pic2, pic3)。"""
    if isinstance(item, dict):
        name = (item.get("name") or "").strip()
        path = (item.get("path") or "").strip()
        pic2, pic3 = _extract_pics_from_dict(item)
        return name, path, pic2, pic3

    line = (item or "").strip()
    if not line:
        return "", "", "", ""

    norm = line
    for sep in ["，", "；", ";", "|"]:
        norm = norm.replace(sep, ",")
    parts = [p.strip() for p in norm.split(",")]

    if len(parts) == 1:
        path = parts[0]
        name = os.path.splitext(os.path.basename(path))[0]
        return name, path, "", ""

    while len(parts) < 4:
        parts.append("")

    name = parts[0]
    path = parts[1]
    pic2 = parts[2]
    pic3 = parts[3]
    if not name and path:
        name = os.path.splitext(os.path.basename(path))[0]
    return name, path, pic2, pic3


def _parse_scan_item(item):
    """
    解析一条扫描目录配置，返回 (path, prefix)。
    path 是原始路径（未规范化），prefix 是可选的源名分组前缀。
    写法： "路径"  或  "路径|前缀"
    """
    if isinstance(item, dict):
        return (item.get("path") or "").strip(), (item.get("prefix") or "").strip()
    s = (item or "").strip()
    if not s:
        return "", ""
    if "|" in s:
        path, prefix = s.split("|", 1)
        return path.strip(), prefix.strip()
    return s, ""


def _scan_dir(root):
    """扫描一个目录。SCAN_RECURSIVE=True 时连所有子文件夹一起扫。"""
    files = []
    if not root or not os.path.isdir(root):
        print("[PY总控] 扫描目录不存在，跳过: {}".format(root))
        return files
    try:
        if SCAN_RECURSIVE:
            for dirpath, _dirs, names in os.walk(root):
                for n in names:
                    if n.lower().endswith(".py"):
                        files.append(os.path.join(dirpath, n))
        else:
            for n in os.listdir(root):
                full = os.path.join(root, n)
                if os.path.isfile(full) and n.lower().endswith(".py"):
                    files.append(full)
    except Exception as e:
        print("[PY总控] 扫描异常 {}: {}".format(root, e))
    return sorted(files)


def _build_source_list():
    global _SOURCE_LIST
    if _SOURCE_LIST is not None:
        return _SOURCE_LIST

    result = []
    seen = set()
    try:
        self_path = _norm_key(os.path.abspath(__file__))
    except Exception:
        self_path = ""

    # ---- 1. 手动列表（A）----
    for item in EXTERNAL_PY_SOURCES:
        name, path, pic2, pic3 = _parse_source_item(item)
        if not path:
            continue
        if not name:
            name = os.path.splitext(os.path.basename(path))[0]
        full = _resolve_path(path)
        key = _norm_key(full) if full else "manual::{}".format(name)
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "name": name, "path": full, "from": "manual",
            "pic2": pic2, "pic3": pic3,
        })

    # ---- 2. 自动扫描（E，支持多个目录 + 分组前缀）----
    exclude = set((x or "").strip().lower() for x in SCAN_EXCLUDE)
    for scan_item in SCAN_DIRS:
        raw_root, prefix = _parse_scan_item(scan_item)
        root = _resolve_path(raw_root)
        for full in _scan_dir(root):
            base = os.path.splitext(os.path.basename(full))[0]
            key = _norm_key(full)
            if key == self_path:
                continue
            if base.strip().lower() in exclude:
                continue
            if key in seen:
                continue
            seen.add(key)
            # 有前缀就拼成 "前缀·文件名"，没有就用文件名
            disp = "{}{}".format(prefix + "·", base) if prefix else base
            result.append({
                "name": disp, "path": full, "from": "scan",
                "pic2": "", "pic3": "",
            })

    _SOURCE_LIST = result
    print("[PY总控] 源清单共 {} 个".format(len(result)))
    return result


def _load_one_spider(name, path):
    full = _resolve_path(path)
    if not full:
        _LOAD_ERRORS[name] = "路径为空"
        return None
    if not os.path.isfile(full):
        _LOAD_ERRORS[name] = "文件不存在: {}".format(full)
        return None
    try:
        mod_name = "ext_sp_{}".format(abs(hash(full)) % (10 ** 9))
        spec = importlib.util.spec_from_file_location(mod_name, full)
        if spec is None or spec.loader is None:
            _LOAD_ERRORS[name] = "无法创建模块"
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        parent = os.path.dirname(full)
        if parent and parent not in sys.path:
            sys.path.insert(0, parent)
        root = os.path.dirname(parent) if parent else ""
        if root and root not in sys.path:
            sys.path.insert(0, root)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "Spider"):
            _LOAD_ERRORS[name] = "无 Spider 类"
            return None
        inst = mod.Spider()
        try:
            inst.init("")
        except TypeError:
            try:
                inst.init()
            except Exception:
                pass
        except Exception:
            pass
        classes = []
        try:
            classes = (inst.homeContent(False) or {}).get("class") or []
        except Exception as e:
            print("[PY总控] 取分类失败 {}: {}".format(name, e))
        return {"name": name, "path": full, "spider": inst, "classes": classes}
    except Exception as e:
        _LOAD_ERRORS[name] = "加载异常: {}".format(e)
        traceback.print_exc()
        return None


def _get_source(idx):
    if idx in _SRC_CACHE:
        return _SRC_CACHE[idx]
    src_list = _build_source_list()
    if not (0 <= idx < len(src_list)):
        return None
    item = src_list[idx]
    one = _load_one_spider(item["name"], item["path"])
    _SRC_CACHE[idx] = one
    return one


# ---------------------- id 编解码 ----------------------

def _enc(idx, real_id):
    return "s{}|{}".format(idx, real_id)


def _dec(vid):
    m = re.match(r"^s(\d+)\|(.*)$", str(vid), re.S)
    if m:
        return int(m.group(1)), m.group(2)
    return None, ""


def _enc_play(idx, pid):
    return "p{}|{}".format(idx, pid)


def _dec_play(pid):
    m = re.match(r"^p(\d+)\|(.*)$", str(pid), re.S)
    if m:
        return int(m.group(1)), m.group(2)
    return None, str(pid)


def _prefix_play(idx, play_url):
    if not play_url:
        return play_url
    out_blocks = []
    for block in str(play_url).split("$$$"):
        out_eps = []
        for ep in block.split("#"):
            ep = ep.strip()
            if not ep:
                continue
            if "$" in ep:
                nm, pid = ep.split("$", 1)
                out_eps.append("{}${}".format(nm, _enc_play(idx, pid)))
            else:
                out_eps.append(_enc_play(idx, ep))
        if out_eps:
            out_blocks.append("#".join(out_eps))
    return "$$$".join(out_blocks)


def _source_first_level(idx, filter):
    """列出某源的分类（分类页），卡片用该源的 pic2。"""
    src_list = _build_source_list()
    src = _get_source(idx)
    if not src:
        err = _LOAD_ERRORS.get(src_list[idx]["name"], "加载失败")
        return {"list": [{
            "vod_id": _enc(idx, ""),
            "vod_name": "加载失败：{}".format(err),
            "vod_remarks": "请检查文件",
        }], "page": 1, "pagecount": 1, "limit": 1, "total": 1}

    sp = src["spider"]
    classes = src.get("classes") or []
    if not classes:
        try:
            classes = (sp.homeContent(False) or {}).get("class") or []
        except Exception:
            classes = []

    pic2 = _pic_uri(src_list[idx].get("pic2"))
    lst = []
    for c in classes:
        cid = str(c.get("type_id", ""))
        if not cid:
            continue
        item = {
            "vod_id": _enc(idx, cid),
            "vod_name": c.get("type_name") or cid,
            "vod_tag": "folder",
        }
        if pic2:
            item["vod_pic"] = pic2
        lst.append(item)
    return {"list": lst, "page": 1, "pagecount": 1,
            "limit": len(lst), "total": len(lst)}


class Spider(Spider):
    def getName(self):
        return SPIDER_NAME or "PY总控"

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        src_list = _build_source_list()
        classes = []
        filters = {}

        classes.append({"type_id": ENTRY_TID,
                        "type_name": SELECT_ENTRY_NAME or "全部源"})

        vals = [{"n": "全部源", "v": ""}]
        for i, item in enumerate(src_list):
            vals.append({"n": item["name"], "v": str(i)})
        filters[ENTRY_TID] = [{
            "key": "src",
            "name": "选择源",
            "value": vals,
        }]

        if ALSO_LIST_SOURCES:
            for i, item in enumerate(src_list):
                classes.append({
                    "type_id": _enc(i, ""),
                    "type_name": item["name"],
                })

        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        src_list = _build_source_list()
        tid = str(tid or "")
        extend = extend if isinstance(extend, dict) else {}

        # ---- 选源入口 ----
        if tid == ENTRY_TID:
            src_val = str(extend.get("src") or "")
            if src_val != "":
                try:
                    idx = int(src_val)
                except Exception:
                    idx = -1
                if 0 <= idx < len(src_list):
                    return _source_first_level(idx, filter)
            lst = []
            for i, item in enumerate(src_list):
                lst.append({
                    "vod_id": _enc(i, ""),
                    "vod_name": item["name"],
                    "vod_tag": "folder",
                })
            return {"list": lst, "page": 1, "pagecount": 1,
                    "limit": len(lst), "total": len(lst)}

        # ---- 普通多级 ----
        idx, real_tid = _dec(tid)
        if idx is None or not (0 <= idx < len(src_list)):
            return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

        if str(real_tid) == "":
            return _source_first_level(idx, filter)

        src = _get_source(idx)
        if not src:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}
        sp = src["spider"]

        try:
            data = sp.categoryContent(str(real_tid), pg, filter, extend) or {}
        except Exception as e:
            print("[PY总控] categoryContent 失败 {}: {}".format(src["name"], e))
            return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

        pic3 = _pic_uri(src_list[idx].get("pic3"))
        for v in data.get("list") or []:
            if not isinstance(v, dict) or "vod_id" not in v:
                continue
            v["vod_id"] = _enc(idx, v["vod_id"])
            if pic3 and v.get("vod_tag") == "folder" \
                    and not (v.get("vod_pic") or "").strip():
                v["vod_pic"] = pic3
        return data

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        idx, real_id = _dec(str(ids[0]))
        src = _get_source(idx)
        if not src:
            return {"list": []}
        sp = src["spider"]
        try:
            data = sp.detailContent([real_id]) or {}
        except Exception as e:
            print("[PY总控] detailContent 失败: {}".format(e))
            return {"list": []}
        for v in data.get("list") or []:
            if not isinstance(v, dict):
                continue
            if "vod_id" in v:
                v["vod_id"] = _enc(idx, v["vod_id"])
            if v.get("vod_play_url"):
                v["vod_play_url"] = _prefix_play(idx, v["vod_play_url"])
        return data

    def searchContent(self, key, quick, pg="1"):
        src_list = _build_source_list()
        videos = []
        for i in range(len(src_list)):
            src = _get_source(i)
            if not src:
                continue
            sp = src["spider"]
            if not hasattr(sp, "searchContent"):
                continue
            try:
                try:
                    data = sp.searchContent(key, quick, pg) or {}
                except TypeError:
                    data = sp.searchContent(key, quick) or {}
            except Exception:
                continue
            for v in data.get("list") or []:
                if isinstance(v, dict):
                    v = dict(v)
                    v["vod_id"] = _enc(i, v.get("vod_id", ""))
                    remarks = v.get("vod_remarks") or ""
                    v["vod_remarks"] = (remarks + " · " + src["name"]).strip(" ·")
                    videos.append(v)
        return {"list": videos}

    def playerContent(self, flag, id, vipFlags):
        idx, real_id = _dec_play(id)
        src = _get_source(idx)
        if src:
            try:
                return src["spider"].playerContent(flag, real_id, vipFlags)
            except Exception as e:
                print("[PY总控] playerContent 失败: {}".format(e))
        return {"parse": 0, "playUrl": "", "url": real_id}