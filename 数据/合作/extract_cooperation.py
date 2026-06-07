#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从所有merged_*.md文件中提取合作/机构信息：
- 主办单位/主办
- 承办单位/承办
- 协办单位/协办
- 执行单位/执行
- 特别鸣谢/鸣谢
- 支持单位/支持
- 赞助/赞助商
- 合作媒体/媒体支持
- 合作机构
- 指导单位
- 学术支持
"""

import re
import os
import json
from datetime import datetime

DATA_DIR = "/Users/zmh/Desktop/重新清洗/精简文本数据_标准化"
OUTPUT_DIR = "/Users/zmh/Desktop/重新清洗/合作"

# 定义要提取的合作相关的关键词模式（按类别）
COOPERATION_PATTERNS = {
    "主办": [
        r"主办[单[位]]?\s*[:：]\s*(.+?)(?=\n(?:承办|协办|执行|赞助|支持|鸣谢|合作|媒体|展览|开幕|时间|地点|艺术家|$)|\Z)",
        r"主办方\s*[:：]\s*(.+?)(?=\n|$)",
    ],
    "承办": [
        r"承办[单[位]]?\s*[:：]\s*(.+?)(?=\n(?:协办|执行|赞助|支持|鸣谢|合作|媒体|展览|开幕|时间|地点|$)|\Z)",
    ],
    "协办": [
        r"协办[单[位]]?\s*[:：]\s*(.+?)(?=\n(?:执行|赞助|支持|鸣谢|合作|媒体|展览|开幕|时间|地点|$)|\Z)",
    ],
    "执行": [
        r"执行[单[位]]?\s*[:：]\s*(.+?)(?=\n(?:赞助|支持|鸣谢|合作|媒体|展览|开幕|时间|$)|\Z)",
    ],
    "特别鸣谢": [
        r"(?:特别\s*)?鸣谢\s*[:：]\s*(.+?)(?=\n(?:合作|媒体|展览|开幕|时间|$)|\Z)",
    ],
    "赞助": [
        r"赞助[商]?\s*[:：]\s*(.+?)(?=\n(?:支持|鸣谢|合作|媒体|展览|开幕|时间|$)|\Z)",
    ],
    "支持": [
        r"(?:学术\s*)?支持[单[位]]?\s*[:：]\s*(.+?)(?=\n(?:鸣谢|合作|媒体|展览|开幕|时间|$)|\Z)",
    ],
    "合作媒体": [
        r"合作媒体\s*[:：]\s*(.+?)(?=\n(?:展览|开幕|时间|$)|\Z)",
        r"媒体支持\s*[:：]\s*(.+?)(?=\n(?:展览|开幕|时间|$)|\Z)",
    ],
    "合作机构": [
        r"(?:战略\s*)?合作[单[位]|机构]\s*[:：]\s*(.+?)(?=\n(?:媒体|展览|开幕|时间|$)|\Z)",
        r"本次活动合作机构\s*[:：]\s*(.+?)(?=\n|$)",
    ],
    "指导单位": [
        r"指导[单[位]]?\s*[:：]\s*(.+?)(?=\n(?:主办|承办|协办|展览|开幕|时间|$)|\Z)",
    ],
}


def extract_event_title(text):
    """提取活动名称（从 # File: 行后面的文件名，或 ## 标题）"""
    # 先找 # File: 行
    m = re.search(r'# File:\s*(.+?)(?:\.md)?$', text, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        # 去掉文件名开头的数字序号
        title = re.sub(r'^\d+_\d+_\d+_', '', title)
        title = re.sub(r'^\d+_', '', title)
        return title
    return ""


def extract_date(text):
    """提取时间信息"""
    m = re.search(r'>作者：.*?时间：(\d{4}\.\d{2}\.\d{2})', text)
    if m:
        return m.group(1)
    return ""


def extract_event_blocks(content):
    """按 EVENT_START 分割，提取每个活动块"""
    blocks = re.split(r'={10,}\s*\[EVENT_START\]\s*={10,}', content)
    return blocks


# 白名单：南京艺术学院美术馆自身及校内机构（排除）
SELF_ORG_PATTERNS = [
    r"南京艺术学[园院][美术馆]?",
    r"南艺美术[馆院]",
    r"AMNUA",
    r"南京艺术学院[\w\d]*学院",
    r"南艺[\w\d]*学院",
]

def is_self_org(org):
    """判断是否为本馆/校内机构"""
    for pat in SELF_ORG_PATTERNS:
        if re.search(pat, org):
            return True
    return False

def extract_cooperation_from_block(block):
    """从单个活动块中提取合作信息"""
    results = []
    title = extract_event_title(block)
    date = extract_date(block)
    
    if not title:
        return results

    for category, patterns in COOPERATION_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, block, re.MULTILINE | re.DOTALL)
            for match in matches:
                # 清理提取的内容
                orgs = match.strip()
                # 去除末尾多余内容
                orgs = re.sub(r'\n.*', '', orgs, flags=re.DOTALL)
                orgs = orgs.strip()
                if orgs and len(orgs) > 1:
                    # 分割多个机构（以; 、、, 、/ 等分割）
                    org_list = re.split(r'[;；、,，/]', orgs)
                    for org in org_list:
                        org = org.strip()
                        if org and len(org) > 1:
                            # 过滤掉非机构文本
                            if not re.match(r'^[\d\s\-—\.。：:：()（）]+$', org):
                                # 去掉括号内的角色说明如（韩国）
                                org_clean = re.sub(r'[（(][^）)]*[）)]', '', org).strip()
                                # 排除自身机构
                                if org_clean and len(org_clean) > 1 and not is_self_org(org_clean):
                                    results.append({
                                        "活动名称": title,
                                        "日期": date,
                                        "合作类别": category,
                                        "机构名称": org_clean
                                    })
    return results


def main():
    all_records = []
    
    # 获取所有 merged_*.md 文件
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
        
        # 按 EVENT_START 分割处理
        blocks = extract_event_blocks(content)
        print(f"  {filename}: {len(blocks)} 个活动块")
        
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
    
    # 统计机构出现次数
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
    
    # 转换为列表排序
    org_stats = [(name, info) for name, info in org_count.items()]
    org_stats.sort(key=lambda x: -x[1]["count"])
    
    # ===== 输出完整记录（按时间排序）=====
    output_lines = []
    output_lines.append("# AMNUA合作机构记录\n")
    output_lines.append(f"**统计时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    output_lines.append(f"**总合作记录数**: {len(all_records)}\n")
    output_lines.append(f"**涉及不同机构数**: {len(org_stats)}\n\n")
    output_lines.append("---\n\n")
    
    # ---- 第一部分：按时间顺序的完整记录 ----
    output_lines.append("## 一、按时间顺序的合作记录\n\n")
    output_lines.append("| 序号 | 日期 | 活动名称 | 合作类别 | 机构名称 |\n")
    output_lines.append("|:---:|:----:|:-----|:----:|:-----|\n")
    
    for i, rec in enumerate(all_records, 1):
        date = rec["日期"] if rec["日期"] else "-"
        title = rec["活动名称"][:40] + "..." if len(rec["活动名称"]) > 40 else rec["活动名称"]
        output_lines.append(f"| {i} | {date} | {title} | {rec['合作类别']} | {rec['机构名称']} |\n")
    
    # ---- 第二部分：机构统计（重复出现排名）----
    output_lines.append("\n\n---\n\n")
    output_lines.append("## 二、合作机构统计（按出现次数排序）\n\n")
    output_lines.append("> ⚠️ **重复出现标记**: 出现多次的机构用 🏷️ 标注出现次数\n\n")
    output_lines.append("| 排名 | 机构名称 | 出现次数 | 首次出现 | 最近出现 | 合作角色 |\n")
    output_lines.append("|:---:|:-----|:---:|:----:|:----:|:-----|\n")
    
    for rank, (name, info) in enumerate(org_stats, 1):
        repeat_tag = f"🏷️ 重复{info['count']}次" if info['count'] > 1 else ""
        categories = "、".join(sorted(info["categories"]))
        output_lines.append(f"| {rank} | {name} | {info['count']} | {info['first_date']} | {info['last_date']} | {categories} |\n")
    
    # ---- 第三部分：分析建议 ----
    output_lines.append("\n\n---\n\n")
    output_lines.append("## 三、合作机构分析与建议\n\n")
    
    # 高频合作机构（出现3次以上）
    high_freq = [x for x in org_stats if x[1]['count'] >= 3]
    if high_freq:
        output_lines.append("### 🔴 高频合作机构（≥3次）——建议保持长期合作关系\n\n")
        for name, info in high_freq[:15]:
            output_lines.append(f"- **{name}**（{info['count']}次）—— 合作角色：{'、'.join(sorted(info['categories']))}\n")
    
    # 中频合作机构（2次）
    mid_freq = [x for x in org_stats if x[1]['count'] == 2]
    if mid_freq:
        output_lines.append(f"\n### 🟡 中频合作机构（2次）——共{len(mid_freq)}个，建议深化合作\n\n")
        for name, info in mid_freq[:20]:
            output_lines.append(f"- {name}（合作角色：{'、'.join(sorted(info['categories']))}）\n")
    
    # 媒体合作统计
    media_orgs = [(n, i) for n, i in org_count.items() if "媒体" in "".join(i["categories"]) or "合作媒体" in "".join(i["categories"])]
    media_orgs.sort(key=lambda x: -x[1]["count"])
    if media_orgs:
        output_lines.append(f"\n### 📺 媒体合作机构统计\n\n")
        output_lines.append("| 媒体名称 | 合作次数 |\n")
        output_lines.append("|:-----|:---:|\n")
        for name, info in media_orgs:
            output_lines.append(f"| {name} | {info['count']} |\n")
    
    # 年度合作分布
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
    
    # 写入文件
    output_path = os.path.join(OUTPUT_DIR, "合作机构记录.md")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)
    
    print(f"\n结果已保存到: {output_path}")
    
    # 同时保存 JSON 格式
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
    print(f"  - 中频机构(2次): {len(mid_freq)}")


if __name__ == "__main__":
    main()
