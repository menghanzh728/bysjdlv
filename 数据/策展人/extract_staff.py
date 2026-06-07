#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从单篇文件夹中提取南京艺术学院美术馆所有校内工作人员名单 v2.0（精确版）

提取策略：
1. 只从文章的结构化信息区域（展览信息块）提取角色-人名配对
2. 角色包括：策展人、馆长、院长、艺术总监、展览执行、学术主持、组委会等
3. 使用严格的姓名验证，过滤非人名噪音
4. 去重合并，按角色分类输出

输出：策展人/南艺美术馆工作人员名单.md
"""

import re
import os
from collections import defaultdict, OrderedDict
from datetime import datetime

# 配置
SINGLE_DIR = "/Users/zmh/Desktop/重新清洗/单篇"
OUTPUT_FILE = "/Users/zmh/Desktop/重新清洗/策展人/南艺美术馆工作人员名单.md"

# ============================================================
# 已知的南艺美术馆/南艺校内人员（白名单）
# ============================================================
# 通过这些已知人员可以扩展识别更多校内人员

CORE_STAFF = {
    # 美术馆核心成员
    '李小山': '馆长/艺术总监',
    '郑闻': '学术部主任/策展人',
    '林书传': '策展人/展览执行',
    '陈瑞': '学术部/策展人',
    '王亚敏': '策展人',
    '曲俊': '展览团队',
    '申鸽': '展览团队',
    '高雅': '展览团队',
    '张安平': '展览团队',
    '徐轩露': '设计/视觉',
    '刘婷': '公教/策展',
    '李莉': '公教/策展',
    '金玉衡': '策展人',
    '陈正': '策展人',
    # 美术学院/南艺校内教授及领导
    '周京新': '美术学院院长/教授',
    '刘伟冬': '院长/校长/教授',
    '姚红': '教授/学术主持',
    '魏永恒': '副教授/策展人',
    '秦修平': '副教授',
    '唐彦': '副教授',
    '李小光': '副教授',
    '周尤': '副教授/策展人',
    '张驰': '副教授',
    '徐利明': '教授/院长',
    '李彤': '教授',
    '费泳': '教授',
    '商勇': '教授',
    '戴丹': '副教授',
    '顾丞峰': '教授',
    '李安源': '教授',
    '薛翔': '教授',
    '黄惇': '教授',
    '张友宪': '教授',
    '陆庆龙': '教授/副院长',
    '束新水': '教授',
    '张新权': '教授',
    '陈世宁': '教授',
    '沈行工': '教授',
    '陈建华': '教授',
    '吕晓雯': '教授',
    '孙胜银': '教授',
    '朱智伟': '副教授',
    '张素琴': '副教授',
    '王浩辉': '教授',
    '杨春华': '教授',
    '徐乐乐': '教授',
    '曹方': '教授',
    '周一清': '教授',
    '莫雄': '教授',
    '吴静': '教授',
    '邬烈炎': '教授',
    '袁熙旸': '教授',
    '夏燕靖': '教授',
    '吕凤显': '教授',
    '陈琦': '教授',
    '张放': '教授',
    '孙晶': '副教授',
    '童芳': '副教授',
}

# ============================================================
# 严格的中文人名验证
# ============================================================
CN_NAME_RE = re.compile(r'^[\u4e00-\u9fff·]{2,4}$')

# 明显不是人名的词（过滤）
NOT_NAME_WORDS = {
    '主办', '承办', '协办', '学术支持', '支持单位', '赞助', '承办单位',
    '主办单位', '协办单位', '时间', '地点', '展期', '开幕', '特别鸣谢',
    '媒体支持', '媒体', '特别支持', '特别协办', '鸣谢', '支持', '合作',
    '组委会', '组委会', '副主席', '主席', '秘书长', '副秘书长', '常务',
    '周一', '周二', '周三', '周四', '周五', '周六', '周日', '一月',
    '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月',
    '十月', '十一月', '十二月', '上午', '下午', '中午', '晚上',
    '致辞', '助理', '声音', '最后', '执行', '代表', '感谢', '表示',
    '策展人', '艺术总监', '学术主持', '展览执行', '项目负责', '总统筹',
    '统筹', '翻译', '设计', '文献整理', '媒体推广', '项目统筹',
    '发起人', '中国美术', '博士生导', '的崔雄', '助理与学', '策展助理',
    '团长', '期间', '一职', '查查', '海上雅臣', '文刀米',
    '雷娜特·', '杜塞尔多',
}

# 机构后缀（以这些结尾的词不是人名）
ORG_SUFFIX = (
    '学院', '大学', '美术馆', '博物馆', '公司', '集团', '协会', '学会',
    '研究会', '委员会', '中心', '局', '处', '部', '馆', '社', '报', '刊',
    '出版社', '基金会', '理事会', '组委会', '代表团', '事务所', '工厂',
    '画廊', '建设', '企业', '银行', '酒店', '广场', '艺术中心',
    '旧址', '驻地', '小学', '中学',
)

# 以"长"结尾的职务型词汇（非人名）
NOT_NAME_ENDINGS = [
    '局长', '处长', '部长', '校长', '院长', '馆长', '系主任', '主任',
    '秘书长', '主席', '董事长', '总经理', '总监',
]

# 常见动词后缀 — 出现在人名后表示动作（如"郑闻策划"中的"策划"）
# 包含这些词尾的不是纯人名
VERB_SUFFIXES = [
    '策划', '担任', '主持', '发起', '代表', '表示', '认为', '指出',
    '强调', '介绍', '致辞', '宣布', '发布', '参加', '出席', '围绕',
    '提出', '展开', '开始', '制作', '创作', '设计', '负责', '致辞',
    '及沃', '老师', '先生', '教授', '致辞',
]


def is_valid_person_name(name):
    """验证是否为有效的中文人名"""
    name = name.strip()
    if not name:
        return False
    # 必须是2-4个中文字符
    if not CN_NAME_RE.match(name):
        return False
    # 排除非人名词汇
    if name in NOT_NAME_WORDS:
        return False
    # 排除以机构后缀结尾
    for suffix in ORG_SUFFIX:
        if name.endswith(suffix) and len(name) >= 3:
            return False
    # 排除职务型词汇
    for ending in NOT_NAME_ENDINGS:
        if name == ending or name.endswith(ending):
            return False
    # 排除常见动词/组合后缀（防止"郑闻策划"、"李小山先"等噪音）
    for vs in VERB_SUFFIXES:
        if name.endswith(vs) and len(name) > 2:
            return False
    # 额外：2字名如果不在白名单中，需要更谨慎
    if len(name) == 2 and name not in CORE_STAFF:
        return False
    # 以"的"开头几乎不可能是人名（"的崔雄"等截断噪音）
    if name.startswith('的'):
        return False
    # 以"与"或"和"开头（"助理与学"等截断噪音）
    if name.startswith('与') or name.startswith('和'):
        return False
    return True


def is_likely_internal(name):
    """判断是否为可能的校内人员"""
    if name in CORE_STAFF:
        return True
    # 不在此名单中的2字名需要谨慎对待
    return False


def extract_date_from_filename(filename):
    """从文件名提取日期：序号_YYYYMMDD_序号_Title.md"""
    match = re.search(r'_(\d{8})_', filename)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, '%Y%m%d')
        except:
            return None
    return None


def clean_role_text(text):
    """清理角色文本，去除括号注释等"""
    # 去掉括号内的英文注释
    text = re.sub(r'[（(][^）)]*[）)]', '', text)
    # 去掉多余空格
    text = text.strip().strip(':').strip('：').strip('/').strip()
    return text


def extract_names_from_text(text):
    """从文本中提取人名列表（以、等分隔）
    
    关键原则：
    1. 优先使用已知白名单匹配
    2. 对于非白名单，只提取明确分隔的独立人名
    3. 绝不从长句中截取片段
    """
    if not text:
        return []
    
    text = text.strip()
    names = []
    
    # === 策略1：按分隔符拆分为独立项 ===
    if re.search(r'[、，,]', text):
        parts = re.split(r'[、，,]+', text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # 去除纯英文/数字后缀（如英文名注释）
            cn_only = re.sub(r'[^\u4e00-\u9fff·]', '', part)
            if is_valid_person_name(cn_only):
                names.append(cn_only)
            else:
                # 也可能是"人名（注释）"格式
                cn_match = re.match(r'^([\u4e00-\u9fff·]{2,4})', part)
                if cn_match:
                    candidate = cn_match.group(1)
                    if is_valid_person_name(candidate):
                        names.append(candidate)
        if names:
            return names
    
    # === 策略2：无分隔符，检查是否含已知白名单人员 ===
    found_core = []
    for name in CORE_STAFF:
        if name in text:
            found_core.append(name)
    if found_core:
        return found_core
    
    # === 策略3：检查是否有先生/教授/老师等后缀 ===
    clean_text = text
    for suffix in ['先生', '教授', '老师', '馆长', '院长', '主任', '博士', '院长', '副馆长']:
        if clean_text.endswith(suffix) and len(clean_text) > len(suffix):
            base = clean_text[:-len(suffix)]
            if is_valid_person_name(base):
                return [base]
    
    # === 策略4：整个文本恰好是一个纯人名 ===
    # 这是最安全的方式，只匹配纯粹的人名
    if is_valid_person_name(clean_text):
        return [clean_text]
    
    return []


# ============================================================
# 结构化信息提取模式
# ============================================================

# 角色头衔模式（优先匹配）
# 策略：冒号后提取直到行尾或句号，然后在Python中仔细解析人名
ROLE_HEADER_RE = re.compile(
    r'(策展人|Curator|艺术总监|Art\s*Director|学术主持|Academic\s*(?:Chair|Support|Advisor)|'
    r'学术顾问|艺术顾问|展览执行|展览团队|Exhibition\s*Team|组委会|Organizing\s*Committee|'
    r'项目负责|Project\s*(?:Manager|Leader|Coordinator)|总统筹|项目统筹|特约主持|活动主持|'
    r'特邀主持|发起人|特邀策展人|策展团队|视觉设计|平面设计|展览设计|设计|翻译|文献整理|'
    r'媒体推广|参展艺术家|艺术支持|学术支持|学术主持单位)'
    r'[：/:]\s*([^\n。]{1,60}?)(?=[\n。]|$)',
    re.IGNORECASE
)

# 馆长声音系列 — 从文章标题中识别（馆长声音 + 可能的人名）
TITLE_ROLE_RE = re.compile(r'【([^】]*馆长声音[^】]*)】')

# 职务头衔 + 人名（连续无空格）- 仅在文档结构化区域匹配
TITLE_NAME_CONTINUOUS_RE = re.compile(
    r'(?:南艺美术馆|南京艺术学院美术馆)'
    r'(馆长|副馆长|艺术总监|学术部主任|学术部|展览部|公教部主任|办公室主任)'
    r'([\u4e00-\u9fff·]{2,4})'
)

# 人名 + 空格 + 职务 - 仅在明确标识的语境中匹配
NAME_SPACE_TITLE_RE = re.compile(
    r'([\u4e00-\u9fff·]{2,4})\s*'
    r'(?:现任|时任)\s*'
    r'南京艺术学院\s*(?:美术馆)?\s*'
    r'(馆长|副馆长|艺术总监|学术部主任)'
)

# 职务 + 空格 + 人名（带冒号或不带）
TITLE_SPACE_NAME_RE = re.compile(
    r'(?:时任|现任)?\s*'
    r'南京艺术学院\s*(?:美术馆)?\s*'
    r'(馆长|副馆长|艺术总监|院长|副院长|系主任|教授)\s*'
    r'[：/:]?\s*'
    r'([\u4e00-\u9fff·]{2,4})'
)

# 英文职务头衔
ENGLISH_ROLE_RE = re.compile(
    r'(Curator|Art\s*Director|Academic\s*(?:Chair|Director|Support)|'
    r'Exhibition\s*(?:Director|Coordinator|Team)|Project\s*(?:Manager|Leader)|'
    r'Director|Co-?ordinator)[：/:]\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2})'
)


def extract_role_headers(content, filename, date_str):
    """
    方法1：提取角色头衔行（"角色名：人名"模式）
    这是最主要的提取方式
    """
    results = []
    for match in ROLE_HEADER_RE.finditer(content):
        role = match.group(1).strip()
        name_text = match.group(2).strip()
        
        # 标准化角色名
        role = clean_role_text(role)
        role_lower = role.lower()
        
        # 角色名标准化
        role_map = {
            'curator': '策展人',
            'art director': '艺术总监',
            'artistic director': '艺术总监',
            'academic chair': '学术主持',
            'academic support': '学术支持',
            'academic advisor': '学术顾问',
            'academic director': '学术主持',
            'exhibition team': '展览团队',
            'exhibition director': '展览执行',
            'exhibition coordinator': '展览执行',
            'project manager': '项目负责',
            'project leader': '项目负责',
            'project coordinator': '项目统筹',
            'organizing committee': '组委会',
            'director': '馆长',
            'coordinator': '统筹',
        }
        role_clean = role_map.get(role_lower, role)
        
        names = extract_names_from_text(name_text)
        for name in names:
            if not is_valid_person_name(name):
                continue
            # 只保留白名单人员或合理的名字
            if name in CORE_STAFF or len(name) >= 2:
                results.append({
                    'name': name,
                    'role': role_clean,
                    'date': date_str,
                    'source': filename,
                })
    
    return results


def extract_title_continuous(content, filename, date_str):
    """
    方法2：提取"南艺美术馆馆长XXX"连续无空格模式
    """
    results = []
    for match in TITLE_NAME_CONTINUOUS_RE.finditer(content):
        title = match.group(1).strip()
        name = match.group(2).strip()
        if is_valid_person_name(name) or name in CORE_STAFF:
            results.append({
                'name': name,
                'role': title,
                'date': date_str,
                'source': filename,
            })
    return results


def extract_name_space_title(content, filename, date_str):
    """
    方法3：提取"XXX 南艺美术馆馆长"倒置模式
    """
    results = []
    for match in NAME_SPACE_TITLE_RE.finditer(content):
        name = match.group(1).strip()
        title = match.group(2).strip()
        if is_valid_person_name(name) or name in CORE_STAFF:
            results.append({
                'name': name,
                'role': title,
                'date': date_str,
                'source': filename,
            })
    return results


def extract_title_space_name(content, filename, date_str):
    """
    方法4：提取"南艺美术馆馆长：李小山"模式
    """
    results = []
    for match in TITLE_SPACE_NAME_RE.finditer(content):
        title = match.group(1).strip()
        name = match.group(2).strip()
        if is_valid_person_name(name) or name in CORE_STAFF:
            results.append({
                'name': name,
                'role': title,
                'date': date_str,
                'source': filename,
            })
    return results


def extract_english_roles(content, filename, date_str):
    """
    方法5：提取英文职务模式
    """
    results = []
    for match in ENGLISH_ROLE_RE.finditer(content):
        role = match.group(1).strip()
        name = match.group(2).strip()
        
        # 角色映射
        role_map = {
            'curator': '策展人',
            'art director': '艺术总监',
            'artistic director': '艺术总监',
            'academic chair': '学术主持',
            'academic director': '学术主持',
            'exhibition director': '展览执行',
            'exhibition coordinator': '展览执行',
            'project manager': '项目负责',
            'director': '馆长',
        }
        std_role = role_map.get(role.lower(), role)
        
        # 验证英文人名
        if name and len(name) >= 3:
            results.append({
                'name': name,
                'role': std_role,
                'date': date_str,
                'source': filename,
            })
    return results


def extract_staff_from_file(filepath):
    """
    从单个文件中综合提取工作人员信息。
    使用多种策略提取并去重。
    """
    results = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        try:
            with open(filepath, 'r', encoding='gbk') as f:
                content = f.read()
        except:
            return results
    
    filename = os.path.basename(filepath)
    date = extract_date_from_filename(filename)
    date_str = date.strftime('%Y-%m-%d') if date else '未知'
    
    # 使用各种策略提取
    results.extend(extract_role_headers(content, filename, date_str))
    results.extend(extract_title_continuous(content, filename, date_str))
    results.extend(extract_name_space_title(content, filename, date_str))
    results.extend(extract_title_space_name(content, filename, date_str))
    results.extend(extract_english_roles(content, filename, date_str))
    
    return results


def normalize_name(name):
    """标准化人名：将噪音变体映射到标准名"""
    # 已知的白名单人员及其噪音变体
    name_variants = {
        '李小山': ['李小山先', '李小山教', '李小山担', '李小山任', '李小山认', 
                   '李小山在', '李小山一', '李小山曾', '李小山则', '李小山致',
                   '李小山策', '李小山表', '李小山获', '李小山为',
                   '李小山这', '李小山那', '李小山介', '李小山强', '李小山担',
                   '李小山以', '李小山从', '李小山与', '李小山对'],
        '郑闻': ['郑闻担', '郑闻策', '郑闻先', '郑闻主', '郑闻及', '郑闻老', 
                 '郑闻发', '郑闻策展', '郑闻策划', '郑闻担任', '郑闻先生',
                 '郑闻主持', '郑闻及沃'],
        '林书传': ['林书传主', '林书传致', '林书传担', '林书传先', '林书传代', 
                   '林书传在', '林书传策', '林书传出', '林书传开', '林书传表'],
        '刘伟冬': ['刘伟冬先', '刘伟冬教', '刘伟冬首', '刘伟冬表'],
        '张承志': ['张承志教', '张承志在', '张承志先'],
        '张凌浩': ['张凌浩教'],
        '何晓佑': ['何晓佑先', '何晓佑教'],
        '陈瑞': ['陈瑞策', '陈瑞承', '陈瑞先', '陈瑞表'],
        '王亚敏': ['王亚敏策', '王亚敏担'],
    }
    
    for std_name, variants in name_variants.items():
        for v in variants:
            if name == v:
                return std_name
    return name


def merge_records(all_records):
    """合并记录：将噪音变体合并到标准人名下"""
    merged = []
    for r in all_records:
        r['name'] = normalize_name(r['name'])
        merged.append(r)
    return merged


def build_staff_database(all_records):
    """
    构建完整的员工数据库。
    合并同名，统计角色和出现时间。
    对非白名单的人员进行更严格的过滤。
    """
    # 先合并变体名
    all_records = merge_records(all_records)
    
    # 按(姓名, 角色, 来源)去重
    seen = set()
    unique_records = []
    for r in all_records:
        key = (r['name'], r['role'], r['source'])
        if key not in seen:
            seen.add(key)
            unique_records.append(r)
    
    staff_db = OrderedDict()
    
    for record in unique_records:
        name = record['name']
        role = record['role']
        date = record['date']
        
        if name not in staff_db:
            staff_db[name] = {
                'name': name,
                'roles': OrderedDict(),
                'first_date': date,
                'last_date': date,
                'source_count': 0,
                'role_count': 0,
            }
        
        person = staff_db[name]
        
        if role not in person['roles']:
            person['roles'][role] = 0
        person['roles'][role] += 1
        person['role_count'] += 1
        person['source_count'] += 1
        
        if date != '未知':
            if person['first_date'] == '未知' or date < person['first_date']:
                person['first_date'] = date
            if person['last_date'] == '未知' or date > person['last_date']:
                person['last_date'] = date
    
    # 过滤：仅保留白名单人员 + 出现2次以上且名字合理的人
    filtered_db = OrderedDict()
    for name, info in staff_db.items():
        if name in CORE_STAFF:
            filtered_db[name] = info
        elif is_valid_person_name(name) and info['role_count'] >= 2:
            filtered_db[name] = info
    
    return filtered_db


def generate_markdown(staff_db):
    """生成Markdown格式的名单"""
    lines = []
    
    lines.append("# 南京艺术学院美术馆校内工作人员名单\n")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"> 数据来源：从单篇文件夹中提取\n")
    lines.append("")
    lines.append("---\n")
    
    # === 角色排序 ===
    role_order = [
        '馆长', '副馆长', '院长', '副院长', '校长', '副校长',
        '艺术总监', '学术主持', '学术支持', '学术顾问', '艺术顾问',
        '策展人', '特邀策展人', '展览执行', '展览团队', '策展团队',
        '组委会', '项目负责', '总统筹', '项目统筹',
        '主任', '系主任', '教授', '副教授', '教务长',
        '学术部主任', '展览部', '公教部主任', '办公室主任',
        '特约主持', '活动主持', '特邀主持', '发起人',
        '设计', '视觉设计', '平面设计', '展览设计',
        '翻译', '文献整理', '媒体推广', '统筹',
    ]
    
    # 按角色分类
    role_entries = defaultdict(list)
    primary_roles = {}
    
    for name, info in staff_db.items():
        # 确定主要角色（优先级最高的那个）
        assigned = False
        for r in role_order:
            if r in info['roles']:
                role_entries[r].append((name, info))
                primary_roles[name] = r
                assigned = True
                break
        if not assigned:
            # 使用出现次数最多的角色
            main_role = max(info['roles'].items(), key=lambda x: x[1])[0]
            role_entries[main_role].append((name, info))
            primary_roles[name] = main_role
    
    # ==========================================
    # 第一部分：按角色分类的汇总表
    # ==========================================
    lines.append("## 一、按角色分类汇总\n")
    lines.append("| 序号 | 姓名 | 校内身份 | 主要角色 | 出现次数 | 活动时间 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    
    seq = 1
    for role in role_order:
        if role in role_entries:
            entries = sorted(role_entries[role], key=lambda x: x[1]['role_count'], reverse=True)
            for name, info in entries:
                known_role = CORE_STAFF.get(name, '')
                role_str = '、'.join(info['roles'].keys())
                time_range = f"{info['first_date']} ~ {info['last_date']}"
                lines.append(f"| {seq} | **{name}** | {known_role} | {role_str} | {info['role_count']} | {time_range} |")
                seq += 1
    
    # 处理未在排序中的角色
    all_assigned_roles = set(primary_roles.values())
    all_roles_in_db = set()
    for info in staff_db.values():
        all_roles_in_db.update(info['roles'].keys())
    unassigned_roles = all_roles_in_db - set(role_order)
    
    for role in sorted(unassigned_roles):
        if role in role_entries:
            entries = sorted(role_entries[role], key=lambda x: x[1]['role_count'], reverse=True)
            for name, info in entries:
                known_role = CORE_STAFF.get(name, '')
                role_str = '、'.join(info['roles'].keys())
                time_range = f"{info['first_date']} ~ {info['last_date']}"
                lines.append(f"| {seq} | **{name}** | {known_role} | {role_str} | {info['role_count']} | {time_range} |")
                seq += 1
    
    lines.append("")
    lines.append(f"总计：**{len(staff_db)}** 名工作人员\n")
    lines.append("---\n")
    
    # ==========================================
    # 第二部分：按角色分组的详细列表
    # ==========================================
    lines.append("## 二、按角色分组详情\n")
    
    for role in role_order:
        if role in role_entries:
            entries = sorted(role_entries[role], key=lambda x: x[1]['role_count'], reverse=True)
            lines.append(f"### {role}\n")
            for name, info in entries:
                known_role = CORE_STAFF.get(name, '')
                role_detail = '、'.join([f"{r}({c}次)" for r, c in info['roles'].items()])
                extra = f" — {known_role}" if known_role else ""
                lines.append(f"- **{name}**{extra}: {role_detail} | {info['first_date']} ~ {info['last_date']}")
            lines.append("")
    
    for role in sorted(unassigned_roles):
        if role in role_entries:
            entries = sorted(role_entries[role], key=lambda x: x[1]['role_count'], reverse=True)
            lines.append(f"### {role}\n")
            for name, info in entries:
                known_role = CORE_STAFF.get(name, '')
                role_detail = '、'.join([f"{r}({c}次)" for r, c in info['roles'].items()])
                extra = f" — {known_role}" if known_role else ""
                lines.append(f"- **{name}**{extra}: {role_detail} | {info['first_date']} ~ {info['last_date']}")
            lines.append("")
    
    # ==========================================
    # 第三部分：完整名单（按姓名排序）
    # ==========================================
    lines.append("---\n")
    lines.append("## 三、完整名单（按姓名排序）\n")
    lines.append("| 序号 | 姓名 | 校内身份 | 担任角色 | 出现频次 | 活动时间范围 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    
    sorted_names = sorted(staff_db.keys(), key=lambda x: x[0] if x else '')
    for seq, name in enumerate(sorted_names, 1):
        info = staff_db[name]
        known_role = CORE_STAFF.get(name, '')
        role_summary = '、'.join([f"{r}({c}次)" for r, c in info['roles'].items()])
        time_range = f"{info['first_date']} ~ {info['last_date']}"
        lines.append(f"| {seq} | {name} | {known_role} | {role_summary} | {info['role_count']}次 | {time_range} |")
    
    return '\n'.join(lines)


def main():
    print("=" * 60)
    print("南艺美术馆校内工作人员名单提取工具 v2.0（精确版）")
    print("=" * 60)
    
    all_files = sorted([f for f in os.listdir(SINGLE_DIR) if f.endswith('.md')])
    print(f"\n共发现 {len(all_files)} 个文件")
    
    all_records = []
    processed = 0
    
    for filename in all_files:
        filepath = os.path.join(SINGLE_DIR, filename)
        records = extract_staff_from_file(filepath)
        all_records.extend(records)
        processed += 1
        if processed % 500 == 0:
            def count_white(rr):
                return len(set(r['name'] for r in rr if r['name'] in CORE_STAFF))
            print(f"  已处理 {processed}/{len(all_files)}，提取 {len(all_records)} 条，已知校内人员 {count_white(all_records)} 名")
    
    # 统计已知校内人员的记录数
    core_records = [r for r in all_records if r['name'] in CORE_STAFF]
    unknown_records = [r for r in all_records if r['name'] not in CORE_STAFF]
    
    print(f"\n处理完成！共处理 {processed} 个文件")
    print(f"提取到 {len(all_records)} 条人员记录")
    print(f"  其中白名单人员记录: {len(core_records)} 条")
    print(f"  其他人员记录: {len(unknown_records)} 条")
    
    # 构建数据库（自动过滤）
    staff_db = build_staff_database(all_records)
    print(f"去重过滤后共 {len(staff_db)} 名工作人员")
    print(f"  其中白名单人员: {sum(1 for n in staff_db if n in CORE_STAFF)} 名")
    print(f"  其他识别人员: {sum(1 for n in staff_db if n not in CORE_STAFF)} 名")
    
    # 生成Markdown
    markdown = generate_markdown(staff_db)
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"\n输出文件: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == '__main__':
    main()
