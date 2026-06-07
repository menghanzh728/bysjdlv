#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从所有merged_*.md文件中提取合作/机构信息 v2
- 支持 **加粗** 标记
- 过滤人名（数字媒体支持中的个人姓名）
- 过滤微博账号（@开头）
- 清理多余格式标记
"""

import re
import os
import json
from datetime import datetime

DATA_DIR = "/Users/zmh/Desktop/重新清洗/精简文本数据_标准化"
OUTPUT_DIR = "/Users/zmh/Desktop/重新清洗/合作"

# 需要过滤的人名（数字媒体支持等场景中出现的个人）
PERSON_NAMES = {
    "严宝平", "刘阳", "熊祎建", "孙宏刚", "章晖",
    "GuoYihan", "郭艺涵", "JiangHongmin", "姜闳敏",
    "LiMingwei", "李明蔚", "LiTing", "李停",
    "LiYuxiao", "李育晓", "LinYaohui", "林耀辉",
    "LiuShu", "刘澍", "OuZhihao", "欧志浩",
    "ShenBin", "沈斌", "TuAnqi", "涂安琪",
    "ZhangLimo", "张琍沫",
}

# 需要过滤的机构模式（非机构的内容）
FILTER_PATTERNS = [
    r"^\*{2,}$",           # 纯星号
    r"^\*{2}\s*$",         # ** 
    r"^@\w+",              # @微博账号
    r"^\s*$",              # 空白
    r"^\d+\s*$",           # 纯数字
]

def clean_org_name(name):
    """清理机构名称，去除加粗标记、@等"""
    name = name.strip()
    # 去除 ** 加粗标记
    name = re.sub(r'\*{2}', '', name).strip()
    # 去除 @ 前缀
    name = re.sub(r'^@', '', name).strip()
    # 去除多余空格
    name = re.sub(r'\s+', '', name).strip()
    # 去除书名号
    name = name.strip('《》').strip()
    # 去除版权符号
    name = re.sub(r'^©️|©', '', name).strip()
    return name

def is_filtered(org):
    """判断是否需要过滤"""
    # 检查人名
    if org in PERSON_NAMES:
        return True
    # 检查过滤模式
    for pat in FILTER_PATTERNS:
        if re.match(pat, org):
            return True
    # 检查是否是单人姓名（2-4个中文字符且不在常见机构关键词列表中）
    if re.match(r'^[\u4e00-\u9fa5]{2,4}$', org) and not any(kw in org for kw in ["公司","集团","学院","大学","中心","协会","学会","馆","社","院","局","基金","社"]):
        return True
    # 检查是否包含英文名+中文名（如 "GuoYihan 郭艺涵"）
    if re.match(r'^[A-Za-z]+[\sA-Za-z]*\u4e00', org) and '公司' not in org and '学院' not in org:
        return True
    # 包含 "艺术总监" "策展人" "执行负责" 等关键词的可能是个人信息而非机构
    if any(kw in org for kw in ["艺术总监", "策展人", "执行负责", "学术嘉宾", "图片摄影", "Specialthanksto", "MirrorPhase"]):
        return True
    # 太长的名称（>30字符）且不含机构关键词的可能不是机构
    if len(org) > 30 and not any(kw in org for kw in ["公司","集团","学院","大学","中心","协会","学会","馆","社","院","局","基金","出版社","电影节","银行"]):
        return True
    # 过滤过短的名称
    if len(org) <= 1:
        return True
    # 过滤"**"
    if org.strip('*').strip() == '':
        return True
    # 过滤"Germany"等国家名
    if org in ["Germany"]:
        return True
    return False

# 定义要提取的合作相关的关键词模式
COOPERATION_PATTERNS = {
    "主办": [
        r"(?<!学术)主办[单[位]]?\s*[:：]\s*(.+?)(?=\n)",
        r"主办方\s*[:：]\s*(.+?)(?=\n)",
    ],
    "承办": [
        r"承办[单[位]]?\s*[:：]\s*(.+?)(?=\n)",
    ],
    "协办": [
        r"协办[单[位]]?\s*[:：]\s*(.+?)(?=\n)",
    ],
    "执行": [
        r"执行[单[位]]?\s*[:：]\s*(.+?)(?=\n)",
    ],
    "特别鸣谢": [
        r"(?:特别\s*)?鸣谢\s*[:：]\s*(.+?)(?=\n)",
    ],
    "赞助": [
        r"赞助[商]?\s*[:：]\s*(.+?)(?=\n)",
    ],
    "学术支持": [
        r"学术支持\s*[:：]\s*(.+?)(?=\n)",
    ],
    "合作媒体": [
        r"合作媒体\s*[:：]\s*(.+?)(?=\n)",
        r"媒体支持\s*[:：]\s*(.+?)(?=\n)",
        r"数字媒体支持\s*[:：]\s*(.+?)(?=\n)",
    ],
    "合作机构": [
        r"(?:战略\s*)?合作[单[位]|机构]\s*[:：]\s*(.+?)(?=\n)",
        r"本次活动合作机构\s*[:：]\s*(.+?)(?=\n)",
    ],
    "指导单位": [
        r"指导[单[位]]?\s*[:：]\s*(.+?)(?=\n)",
    ],
}

# 自身机构排除
SELF_ORG_PATTERNS = [
    r"南京艺术学[园院]",
    r"南艺美术[馆院]",
    r"AMNUA",
    r"南京艺术学院",
    r"南艺$",
]

def is_self_org(org):
    for pat in SELF_ORG_PATTERNS:
        if re.search(pat, org):
            return True
    return False

def extract_event_title(text):
    m = re.search(r'# File:\s*(.+?)(?:\.md)?$', text, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        title = re.sub(r'^\d+_\d+_\d+_', '', title)
        title = re.sub(r'^\d+_', '', title)
        # 清理HTML实体
        title = title.replace('&#39;', "'").replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
        return title
    return ""

def extract_date(text):
    m = re.search(r'>作者：.*?时间：(\d{4}\.\d{2}\.\d{2})', text)
    if m:
        return m.group(1)
    return ""

def extract_event_blocks(content):
    blocks = re.split(r'={10,}\s*\[EVENT_START\]\s*={10,}', content)
    return blocks

def extract_cooperation_from_block(block):
    results = []
    title = extract_event_title(block)
    date = extract_date(block)
    if not title:
        return results

    for category, patterns in COOPERATION_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, block, re.MULTILINE | re.DOTALL)
            for match in matches:
                orgs = match.strip()
                # 去除换行及之后的内容
                orgs = re.sub(r'\n.*', '', orgs, flags=re.DOTALL)
                orgs = orgs.strip()
                if not orgs or len(orgs) < 2:
                    continue
                
                # 分割多个机构
                org_list = re.split(r'[;；、,，/]', orgs)
                for org in org_list:
                    org_clean = clean_org_name(org)
                    if not org_clean:
                        continue
                    # 检查是否包含特殊关键词（个人角色词），如果是则跳过
                    if is_filtered(org_clean):
                        continue
                    if is_self_org(org_clean):
                        continue
    
                    results.append({
                        "活动名称": title,
                        "日期": date,
                        "合作类别": category,
                        "机构名称": org_clean
                    })
    return results

def main():
    all_records = []
    
    files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith("merged_") and f.endswith(".md")],
                   key=lambda x: int(re.search(r'(\d+)', x).group(1)))
    
    print(f"找到 {len(files)} 个文件")
    
    for filename in files:
        filepath = os.path.join(DATA_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            try:
                with open(filepath, 'r', encoding='gbk') as f:
                    content = f.read()
            except:
                print(f"  跳过 {filename}：无法读取")
                continue
        
        blocks = extract_event_blocks(content)
        
        for block in blocks:
            records = extract_cooperation_from_block(block)
            all_records.extend(records)
    
    print(f"\n总计提取 {len(all_records)} 条合作记录")
    
    # 按日期排序
    def sort_key(rec):
        try:
            return datetime.strptime(rec["日期"], "%Y.%m.%d") if rec["日期"] else datetime.min
        except:
            return datetime.min
    
    all_records.sort(key=sort_key)
    
    # 统计
    org_count = {}
    for rec in all_records:
        name = rec["机构名称"]
        if name not in org_count:
            org_count[name] = {"count": 0, "categories": set(), "first_date": rec["日期"], "last_date": rec["日期"]}
        org_count[name]["count"] += 1
        org_count[name]["categories"].add(rec["合作类别"])
        if rec["日期"]:
            if rec["日期"] < org_count[name]["first_date"]:
                org_count[name]["first_date"] = rec["日期"]
            if rec["日期"] > org_count[name]["last_date"]:
                org_count[name]["last_date"] = rec["日期"]
    
    org_stats = [(name, info) for name, info in org_count.items()]
    org_stats.sort(key=lambda x: -x[1]["count"])
    
    # ===== 生成输出 =====
    output_lines = []
    output_lines.append("# AMNUA合作机构记录\n")
    output_lines.append(f"**统计时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    output_lines.append(f"**总合作记录数**: {len(all_records)}\n")
    output_lines.append(f"**涉及不同机构数**: {len(org_stats)}\n\n")
    output_lines.append("---\n\n")
    
    # 第一部分：按时间顺序
    output_lines.append("## 一、按时间顺序的合作记录\n\n")
    output_lines.append("| 序号 | 日期 | 活动名称 | 合作类别 | 机构名称 |\n")
    output_lines.append("|:---:|:----:|:-----|:----:|:-----|\n")
    
    for i, rec in enumerate(all_records, 1):
        date = rec["日期"] if rec["日期"] else "-"
        title = rec["活动名称"][:35] + "..." if len(rec["活动名称"]) > 35 else rec["活动名称"]
        output_lines.append(f"| {i} | {date} | {title} | {rec['合作类别']} | {rec['机构名称']} |\n")
    
    # 第二部分：机构统计
    output_lines.append("\n\n---\n\n")
    output_lines.append("## 二、合作机构统计（按出现次数排序）\n\n")
    output_lines.append("> ⚠️ **重复出现标记**: 出现多次的机构会标注次数\n\n")
    output_lines.append("| 排名 | 机构名称 | 出现次数 | 首次出现 | 最近出现 | 合作角色 |\n")
    output_lines.append("|:---:|:-----|:---:|:----:|:----:|:-----|\n")
    
    for rank, (name, info) in enumerate(org_stats, 1):
        repeat_tag = f" 🏷️重复{info['count']}次" if info['count'] > 1 else ""
        categories = "、".join(sorted(info["categories"]))
        output_lines.append(f"| {rank} | {name}{repeat_tag} | {info['count']} | {info['first_date']} | {info['last_date']} | {categories} |\n")
    
    # 第三部分：分析建议
    output_lines.append("\n\n---\n\n")
    output_lines.append("## 三、合作机构分析与建议\n\n")
    
    high_freq = [x for x in org_stats if x[1]['count'] >= 3]
    if high_freq:
        output_lines.append("### 🔴 高频合作机构（≥3次）——建议保持长期合作关系\n\n")
        for name, info in high_freq:
            output_lines.append(f"- **{name}**（{info['count']}次）—— 角色：{'、'.join(sorted(info['categories']))}\n")
    
    mid_freq = [x for x in org_stats if x[1]['count'] == 2]
    if mid_freq:
        output_lines.append(f"\n### 🟡 中频合作机构（2次）——共{len(mid_freq)}个，建议深化合作\n\n")
        for name, info in mid_freq:
            output_lines.append(f"- {name}（角色：{'、'.join(sorted(info['categories']))}）\n")
    
    # 媒体合作统计
    media_cats = {"合作媒体", "媒体支持"}
    media_orgs = [(n, i) for n, i in org_count.items() if media_cats & i["categories"]]
    media_orgs.sort(key=lambda x: -x[1]["count"])
    if media_orgs:
        output_lines.append(f"\n### 📺 媒体合作机构统计\n\n")
        output_lines.append("| 媒体名称 | 合作次数 |\n")
        output_lines.append("|:-----|:---:|\n")
        for name, info in media_orgs:
            output_lines.append(f"| {name} | {info['count']} |\n")
    
    # 年度分布
    output_lines.append(f"\n### 📅 年度合作机构分布\n\n")
    year_orgs = {}
    for rec in all_records:
        if rec["日期"]:
            year = rec["日期"][:4]
            if year not in year_orgs:
                year_orgs[year] = set()
            year_orgs[year].add(rec["机构名称"])
    
    for year in sorted(year_orgs.keys()):
        output_lines.append(f"- **{year}年**: {len(year_orgs[year])} 个合作机构\n")
    
    # 合作类别分布
    output_lines.append(f"\n### 📊 合作类别分布\n\n")
    cat_count = {}
    for rec in all_records:
        cat = rec["合作类别"]
        cat_count[cat] = cat_count.get(cat, 0) + 1
    output_lines.append("| 合作类别 | 次数 |\n")
    output_lines.append("|:-----|:---:|\n")
    for cat, cnt in sorted(cat_count.items(), key=lambda x: -x[1]):
        output_lines.append(f"| {cat} | {cnt} |\n")
    
    # 写入文件
    output_path = os.path.join(OUTPUT_DIR, "合作机构记录.md")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)
    
    print(f"\n结果已保存到: {output_path}")
    
    json_path = os.path.join(OUTPUT_DIR, "合作机构记录.json")
    json_output = {
        "统计时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "总记录数": len(all_records),
        "不同机构数": len(org_stats),
        "合作记录": all_records,
        "机构统计": {name: {"次数": info["count"], "角色": list(info["categories"]), "首次": info["first_date"], "最近": info["last_date"]} 
                     for name, info in org_count.items()}
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    
    print(f"JSON数据已保存到: {json_path}")
    print(f"\n统计摘要:")
    print(f"  - 总合作记录: {len(all_records)}")
    print(f"  - 不同机构: {len(org_stats)}")
    print(f"  - 高频机构(≥3次): {len(high_freq)}")

if __name__ == "__main__":
    main()
