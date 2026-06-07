#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从单篇文件夹中提取所有合作机构信息 v2.0（优化版）
包括：主办单位、承办单位、协办单位、特别协办、学术支持、支持单位、执行单位、指导单位、赞助

优化内容：
1. 修复 clean_org_name 去除 ** 前缀
2. 过滤英文噪音词汇（Organizer, Supported by, Academic Support, Organizer: 等）
3. 统一歌德学院变体名称（合并不同括号写法）
4. 排除自身机构英文名（Art Museum of Nanjing University of the Arts）
5. 更干净的分隔符处理和噪音过滤

从文件名提取日期，按时间顺序排列
"""

import re
import os
import json
from datetime import datetime

# 配置
SINGLE_DIR = "/Users/zmh/Desktop/重新清洗/单篇"
OUTPUT_MD = "/Users/zmh/Desktop/重新清洗/合作/合作机构记录_完整版.md"
OUTPUT_JSON = "/Users/zmh/Desktop/重新清洗/合作/合作机构记录_完整版.json"

# 合作类别关键词及对应的显示名称
COOPERATION_CATEGORIES = {
    '主办单位': '主办',
    '主办': '主办',
    '承办单位': '承办',
    '承办': '承办',
    '协办单位': '协办',
    '协办': '协办',
    '特别协办': '特别协办',
    '学术支持': '学术支持',
    '支持单位': '支持',
    '赞助': '赞助',
    '赞助商': '赞助',
    '执行单位': '执行',
    '指导单位': '指导',
    '特别鸣谢': '特别鸣谢',
}

# 需要过滤掉的自身机构关键词（包括英文名）
SELF_ORG_PATTERNS = [
    '南京艺术学院美术馆',
    '南艺美术馆',
    'AMNUA',
    '南京艺术学院',
    '南艺',
    '美术馆公共教育部',
    '美术馆典藏部',
    '美术馆',
    'Art Museum of Nanjing University of the Arts',
]

# 英文噪音词汇（不是真正的中文机构名称）
ENGLISH_NOISE_PATTERNS = [
    r'^Organizer\s*:?\s*',       # Organizer, Organizer: 
    r'^Supported\s+by',           # Supported by
    r'^Academic\s+Support',       # Academic Support
    r'^Co-?orgenizer',            # Co-orgenizer
    r'^Organized\s+by',           # Organized by
    r'^Special\s+thanks\s+to',    # Special thanks to
]

# 非机构名称模式（过滤明显不是机构的文本）
NON_ORG_PATTERNS = [
    r'^时间[：:]',                # 时间：
    r'^\d{4}年\d{1,2}月',        # 2015年3月...
    r'^地点[：:]',                # 地点：
    r'^Party$', r'^Talk$', r'^NYC$', r'^Germany$',
    r'^Orang$',                   # Orang（可能是人名或品牌简称，出现3次）
    # 长段描述性文字（超过30字且不含机构关键词的）
]

# 需要清理的剩余**前缀
REMAINING_STAR_PATTERN = re.compile(r'^\*\*\s*')

# 过长且可疑的描述性文本（可能是提取错误的段落）
LONG_TEXT_THRESHOLD = 40  # 超过40个字符且不包含常见机构关键词的视为噪音

# 名称标准化映射：将不同写法的同一机构统一
NAME_NORMALIZATION = {
    '歌德学院（中国）': '歌德学院（中国）',
    '歌德学院(中国)': '歌德学院（中国）',
    '歌德学院': '歌德学院（中国）',
    '北京德国文化中心·歌德学院（中国）': '歌德学院（中国）',
    '北京德国文化中心·歌德学院(中国)': '歌德学院（中国）',
    'Goethe-Institut China': '歌德学院（中国）',
    '金鹰·全生活中心': '南京金鹰全生活中心',
    '金鹰全生活中心': '南京金鹰全生活中心',
    '南京金鹰全生活中心': '南京金鹰全生活中心',
    '歌德学院（中国）      德国对外文化关系学院友情支持时间：2015年3月21日': '歌德学院（中国）',
    '北京德国文化中心·歌德学院(中国)Organized by: Nanjing University of the Arts Museum': '歌德学院（中国）',
    '德国斑马国际诗歌电影节Special thanks to: Zebra Poetry Film Festival': '德国斑马国际诗歌电影节',
    '** 香港Ora-Ora方由美术': '香港Ora-Ora方由美术',
    '** 中国国家画院': '中国国家画院',
    '**大川文化': '大川文化',
    '** 大川文化': '大川文化',
    '中国国家画院）': '中国国家画院',
    '中国当代水墨年鉴组委会**承办：**大川文化': '中国当代水墨年鉴组委会',
}

# 角色关键词（过滤个人姓名）
ROLE_KEYWORDS = [
    '艺术总监', '策展人', '学术主持', '出品人', '展览策划',
    '策展团队', '展览统筹', '展务主管', '媒体主管', '公教主管',
    '纪录片导演', '纪录片团队', '联合策展人', '策划团队',
    '参展艺术家', '艺术家', '参展画家',
]

def extract_date_from_filename(filename):
    """从文件名中提取日期，格式如：1_20130905_0_xxx.md -> 2013.09.05"""
    match = re.match(r'(\d+)_(\d{4})(\d{2})(\d{2})_', filename)
    if match:
        return f"{match.group(2)}.{match.group(3)}.{match.group(4)}"
    return None

def extract_title_from_filename(filename):
    """从文件名中提取活动标题"""
    # 去掉序号和时间部分，如：1_20130905_0_Welcome_to_AMNUA.md -> Welcome_to_AMNUA
    match = re.match(r'\d+_\d{8}_\d+_(.+)\.md$', filename)
    if match:
        title = match.group(1)
        # 清理标题中的下划线（但保留可能是有意义的空格替代）
        # 将下划线替换为空格，但注意有些标题中的下划线是原本的空格
        title = title.replace('_', ' ')
        # 清理多余空格
        title = re.sub(r'\s+', ' ', title).strip()
        return title
    return None

def is_self_org(org_name):
    """判断是否为自身机构，需要过滤"""
    for pattern in SELF_ORG_PATTERNS:
        if pattern in org_name:
            return True
    return False

def is_role_line(line):
    """判断是否为角色/人员行"""
    for keyword in ROLE_KEYWORDS:
        if keyword in line:
            return True
    return False

def is_person_name(org_name):
    """判断是否为个人姓名（2-4个中文字符，不包含机构关键词）"""
    # 纯中文字符 2-4 个字，没有"公司、学院、大学、集团、社、馆、中心"等
    pure_chinese = re.match(r'^[\u4e00-\u9fa5]{2,4}$', org_name)
    if pure_chinese:
        # 检查是否包含机构特征词
        inst_keywords = ['公司', '学院', '大学', '集团', '社', '馆', '中心', 
                        '出版社', '协会', '基金会', '研究会', '委员会',
                        '报', '刊', '网', '台', '局', '处', '部', '系',
                        '银行', '基金', '美术', '艺术', '文化', '传媒',
                        '设计', '画院', '剧院', '团', '院', '所']
        for kw in inst_keywords:
            if kw in org_name:
                return False
        return True
    return False

def is_noise_text(org_name):
    """判断是否为噪音文本（英文标注、非机构文本等）"""
    for pattern in ENGLISH_NOISE_PATTERNS:
        if re.match(pattern, org_name, re.IGNORECASE):
            return True
    for pattern in NON_ORG_PATTERNS:
        if re.match(pattern, org_name):
            return True
    
    # 检查是否还有 ** 前缀（应该已经被清理，但以防万一）
    if REMAINING_STAR_PATTERN.match(org_name):
        return True
    
    # 过滤过长的描述性文本（不是机构名）
    if len(org_name) > LONG_TEXT_THRESHOLD:
        # 检查是否包含常见机构关键词
        inst_keywords = ['公司', '学院', '大学', '集团', '社', '馆', '中心', 
                        '出版社', '协会', '基金会', '研究会', '委员会',
                        '报', '刊', '美术馆', '画廊', '研究院', '学会']
        has_inst_kw = any(kw in org_name for kw in inst_keywords)
        # 也检查是否包含中文（纯英文长文本通常是噪音）
        has_chinese = bool(re.search(r'[\u4e00-\u9fa5]', org_name))
        if not has_inst_kw and not has_chinese:
            return True
        # 超过60字且包含"。 "的基本是段落提取错误
        if len(org_name) > 60 and '。' in org_name:
            return True
    
    return False

def is_truncated_name(org_name):
    """判断是否为被截断的名称"""
    # 以"艺"、"的中"、"的"等结尾的不完整词汇
    truncations = [r'艺$', r'院$', r'的中$', r'的$']
    for p in truncations:
        if re.search(p, org_name):
            # 如果很短（小于4字）且以这些结尾，可能是截断
            if len(org_name) <= 6:
                return True
    return False

def normalize_org_name(org_name):
    """标准化机构名称：统一括号格式、合并变体"""
    # 先检查是否有直接映射
    if org_name in NAME_NORMALIZATION:
        return NAME_NORMALIZATION[org_name]
    
    # 统一全角/半角括号
    name = org_name.replace('（', '(').replace('）', ')')
    
    # 如果标准化后有映射，则使用
    if name in NAME_NORMALIZATION:
        return NAME_NORMALIZATION[name]
    
    return org_name

def clean_org_name(name):
    """清理机构名称"""
    # 去掉首尾空白
    name = name.strip()
    # 去掉加粗标记 **（可能在开头或结尾）
    name = re.sub(r'^\*{1,2}\s*', '', name)
    name = re.sub(r'\s*\*{1,2}$', '', name)
    # 去掉首尾特殊符号
    name = name.strip('：')
    name = name.strip(':')
    name = name.strip('，')
    name = name.strip(',')
    name = name.strip('、')
    name = name.strip(';')
    name = name.strip('；')
    name = name.strip('《')
    name = name.strip('》')
    name = name.strip("'")
    name = name.strip('"')
    name = name.strip('|')  # 表格符号
    name = name.strip()
    return name

def parse_cooperation_line(line):
    """解析一行中的合作信息，返回 (类别, 机构名) 列表"""
    results = []
    
    # 尝试匹配各种格式：
    # 1. **主办单位：** XXX
    # 2. 主办单位：XXX
    # 3. 主办单位 XXX
    # 4. **学术支持：** XXX
    
    for keyword, category in COOPERATION_CATEGORIES.items():
        # 匹配带**加粗的格式
        pattern1 = r'\*{0,2}' + re.escape(keyword) + r'\*{0,2}\s*[:：]\s*\*{0,2}(.+?)(?:\*{0,2}$)'
        # 匹配不带冒号的格式
        pattern2 = r'\*{0,2}' + re.escape(keyword) + r'\*{0,2}\s+(.+?)$'
        # 匹配带/分隔的格式（如 "主办单位/XXX"）
        pattern3 = r'\*{0,2}' + re.escape(keyword) + r'\*{0,2}\s*/\s*(.+?)$'
        
        for pattern in [pattern1, pattern2, pattern3]:
            match = re.search(pattern, line)
            if match:
                content = match.group(1).strip()
                if not content:
                    continue
                    
                # 跳过角色/人员行
                if is_role_line(line):
                    continue
                
                # 按常见分隔符分割多个机构
                # 中文分号；英文分号; 中文逗号，英文逗号, 中文顿号、空格
                parts = re.split(r'[;；、，,/]\s*', content)
                
                for part in parts:
                    part = clean_org_name(part)
                    if not part or len(part) <= 1:
                        continue
                    if part.isspace():
                        continue
                    if is_self_org(part):
                        continue
                    if is_person_name(part):
                        continue
                    if is_noise_text(part):
                        continue
                    if is_truncated_name(part):
                        continue
                    
                    # 标准化机构名称
                    part = normalize_org_name(part)
                    
                    results.append((category, part))
    
    return results

def extract_from_text(text, filename, all_records):
    """从文本中提取所有合作信息"""
    date = extract_date_from_filename(filename)
    title = extract_title_from_filename(filename)
    
    if not date or not title:
        return
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        # 跳过角色/人员行
        if is_role_line(line):
            continue
        
        results = parse_cooperation_line(line)
        for category, org_name in results:
            all_records.append({
                '日期': date,
                '活动名称': title,
                '合作类别': category,
                '机构名称': org_name,
                '来源文件': filename,
                '行号': i + 1
            })


def main():
    all_records = []
    
    # 获取所有md文件
    md_files = [f for f in os.listdir(SINGLE_DIR) if f.endswith('.md')]
    md_files.sort()  # 按文件名排序（包含日期信息）
    
    print(f"找到 {len(md_files)} 个单篇文件")
    
    for filename in md_files:
        filepath = os.path.join(SINGLE_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            extract_from_text(text, filename, all_records)
        except Exception as e:
            print(f"  读取文件 {filename} 出错: {e}")
    
    # 按日期排序
    all_records.sort(key=lambda x: x['日期'])
    
    print(f"\n总计提取 {len(all_records)} 条合作记录")
    
    # 统计机构频次
    org_stats = {}
    for rec in all_records:
        org_name = rec['机构名称']
        if org_name not in org_stats:
            org_stats[org_name] = {
                'count': 0,
                'first_date': rec['日期'],
                'last_date': rec['日期'],
                'categories': set(),
                'activities': []
            }
        org_stats[org_name]['count'] += 1
        if rec['日期'] < org_stats[org_name]['first_date']:
            org_stats[org_name]['first_date'] = rec['日期']
        if rec['日期'] > org_stats[org_name]['last_date']:
            org_stats[org_name]['last_date'] = rec['日期']
        org_stats[org_name]['categories'].add(rec['合作类别'])
        org_stats[org_name]['activities'].append(rec['活动名称'])
    
    # 按出现次数排序
    sorted_orgs = sorted(org_stats.items(), key=lambda x: (-x[1]['count'], x[1]['first_date']))
    
    # 统计类别分布
    category_stats = {}
    for rec in all_records:
        cat = rec['合作类别']
        if cat not in category_stats:
            category_stats[cat] = 0
        category_stats[cat] += 1
    
    # 统计年度分布
    year_stats = {}
    for rec in all_records:
        year = rec['日期'][:4]
        if year not in year_stats:
            year_stats[year] = set()
        year_stats[year].add(rec['机构名称'])
    
    # ======== 生成 Markdown ========
    md_lines = []
    md_lines.append("# AMNUA合作机构记录（完整版）\n")
    md_lines.append(f"> **统计时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    md_lines.append(f"> **数据来源**: 单篇文件夹（{len(md_files)}个文件）\n")
    md_lines.append(f"> **提取内容**: 主办单位、承办单位、协办单位、特别协办、学术支持、赞助、支持单位、执行单位、指导单位、特别鸣谢\n")
    md_lines.append(f"> **总记录数**: {len(all_records)} 条\n")
    md_lines.append(f"> **不同机构数**: {len(org_stats)} 个\n")
    md_lines.append("\n---\n")
    
    # ====== 一、按时间顺序排列 ======
    md_lines.append("\n## 一、合作机构记录（按时间排序）\n")
    md_lines.append("| 序号 | 日期 | 活动名称 | 合作类别 | 机构名称 |\n")
    md_lines.append("|:---:|:----:|:-----|:-----:|:-----|\n")
    
    for idx, rec in enumerate(all_records, 1):
        activity_name = rec['活动名称']
        # 限制活动名称长度
        if len(activity_name) > 35:
            activity_name = activity_name[:32] + '...'
        md_lines.append(f"| {idx} | {rec['日期']} | {activity_name} | {rec['合作类别']} | {rec['机构名称']} |\n")
    
    # ====== 二、机构统计 ======
    md_lines.append("\n---\n")
    md_lines.append("\n## 二、合作机构统计（按出现次数排序）\n")
    md_lines.append("> ⚠️ **重复出现标记**: 出现多次的机构会标注次数\n")
    md_lines.append("\n| 排名 | 机构名称 | 出现次数 | 首次出现 | 最近出现 | 合作角色 |\n")
    md_lines.append("|:---:|:-----|:---:|:----:|:----:|:-----|\n")
    
    for rank, (org_name, stats) in enumerate(sorted_orgs, 1):
        count = stats['count']
        count_tag = f" 🏷️重复{count}次" if count > 1 else ""
        categories = '、'.join(sorted(stats['categories']))
        md_lines.append(f"| {rank} | {org_name}{count_tag} | {count} | {stats['first_date']} | {stats['last_date']} | {categories} |\n")
    
    # ====== 三、分析与建议 ======
    md_lines.append("\n---\n")
    md_lines.append("\n## 三、合作机构分析与建议\n")
    
    # 高频机构
    high_freq = [(n, s) for n, s in sorted_orgs if s['count'] >= 3]
    if high_freq:
        md_lines.append("\n### 🔴 高频合作机构（≥3次）——建议保持长期合作关系\n")
        for org_name, stats in high_freq:
            categories = '、'.join(sorted(stats['categories']))
            md_lines.append(f"- **{org_name}**（{stats['count']}次）—— 角色：{categories}\n")
    
    # 中频机构
    mid_freq = [(n, s) for n, s in sorted_orgs if s['count'] == 2]
    if mid_freq:
        md_lines.append("\n### 🟡 中频合作机构（2次）——共{}个，建议深化合作\n".format(len(mid_freq)))
        for org_name, stats in mid_freq[:20]:  # 只显示前20个
            categories = '、'.join(sorted(stats['categories']))
            md_lines.append(f"- {org_name}（角色：{categories}）\n")
    
    # 媒体合作机构
    media_orgs = [(n, s) for n, s in sorted_orgs if '合作媒体' in s['categories'] or 
                  any(kw in n for kw in ['报', '刊', '网', '台', 'TV', '日报', '晚报', '传媒', '广播', '艺术界'])]
    if media_orgs:
        md_lines.append("\n### 📺 媒体合作机构统计\n")
        md_lines.append("| 媒体名称 | 合作次数 |\n")
        md_lines.append("|:-----|:---:|\n")
        for org_name, stats in sorted(media_orgs, key=lambda x: -x[1]['count']):
            md_lines.append(f"| {org_name} | {stats['count']} |\n")
    
    # 年度分布
    md_lines.append("\n### 📅 年度合作机构分布\n")
    for year in sorted(year_stats.keys()):
        count = len(year_stats[year])
        md_lines.append(f"- **{year}年**: {count} 个合作机构\n")
    
    # 类别分布
    md_lines.append("\n### 📊 合作类别分布\n")
    md_lines.append("| 合作类别 | 次数 |\n")
    md_lines.append("|:-----|:---:|\n")
    for cat, count in sorted(category_stats.items(), key=lambda x: -x[1]):
        md_lines.append(f"| {cat} | {count} |\n")
    
    # 写入文件
    os.makedirs(os.path.dirname(OUTPUT_MD), exist_ok=True)
    with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
        f.writelines(md_lines)
    
    # ======== 生成 JSON ========
    json_output = {
        '统计时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        '总记录数': len(all_records),
        '不同机构数': len(org_stats),
        '合作记录': all_records,
        '机构统计': [
            {
                '机构名称': name,
                '出现次数': stats['count'],
                '首次出现': stats['first_date'],
                '最近出现': stats['last_date'],
                '合作角色': list(stats['categories'])
            }
            for name, stats in sorted_orgs
        ]
    }
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {OUTPUT_MD}")
    print(f"JSON数据已保存到: {OUTPUT_JSON}")
    print(f"\n统计摘要:")
    print(f"  - 总合作记录: {len(all_records)}")
    print(f"  - 不同机构: {len(org_stats)}")
    print(f"  - 高频机构(≥3次): {len(high_freq)}")
    print(f"  - 中频机构(2次): {len(mid_freq)}")
    
    # 打印前20个高频机构
    print(f"\n前20个高频机构:")
    for i, (name, stats) in enumerate(sorted_orgs[:20], 1):
        categories = '、'.join(sorted(stats['categories']))
        print(f"  {i}. {name} - {stats['count']}次 ({categories})")


if __name__ == '__main__':
    main()
