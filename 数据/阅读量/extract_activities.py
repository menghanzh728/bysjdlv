#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取南京艺术学院美术馆（AMNUA）的活动信息
分类统计：讲座、工作坊、访谈、沙龙、展览等
并记录：时间、地点、活动名称
"""

import os
import re
import json
from collections import defaultdict
from datetime import datetime

# 文件夹路径
DATA_DIR = "/Users/zmh/Desktop/重新清洗/精简文本数据_标准化"
OUTPUT_DIR = "/Users/zmh/Desktop/重新清洗/活动占比"

# 活动分类规则
ACTIVITY_CATEGORIES = {
    "讲座": {
        "keywords": ["讲座", "lecture", "学术讲座", "专题讲座"],
        "activities": []
    },
    "工作坊": {
        "keywords": ["工作坊", "workshop", "工坊"],
        "activities": []
    },
    "访谈": {
        "keywords": ["访谈", "对话", "对谈", "interview"],
        "activities": []
    },
    "沙龙": {
        "keywords": ["沙龙", "salon"],
        "activities": []
    },
    "展览": {
        "keywords": ["展览", "展讯", "exhibition", "零方案", "影像档案", "素描"],
        "activities": []
    },
    "公教活动": {
        "keywords": ["公教", "公共教育", "少儿", "children", "education"],
        "activities": []
    },
    "开幕式/研讨会": {
        "keywords": ["开幕", "研讨会", "opening", "seminar"],
        "activities": []
    },
    "导览": {
        "keywords": ["导览", "tour", "guide"],
        "activities": []
    },
    "现场/活动报道": {
        "keywords": ["现场", "scene", "现场报道"],
        "activities": []
    },
    "其他": {
        "keywords": [],
        "activities": []
    }
}

# 用于匹配关键信息的正则
title_pattern = re.compile(r'^#([^#]+)$', re.MULTILINE)
file_date_pattern = re.compile(r'# File: \d+_(\d{4})(\d{2})(\d{2})_')
time_pattern = re.compile(r'时间[:：]\s*(\d{4})[.\s-](\d{2})[.\s-](\d{2})[.\s-]?(\d{1,2})?[:\s]*(\d{2})?')
location_pattern = re.compile(r'地点[:：]\s*([^(\n\r]+)')
activity_name_pattern = re.compile(r'((?:AMNUA)?[^：\n\r]*(?:讲座|工作坊|访谈|对话|展览|沙龙|公教|导览|展讯)[^：\n\r]*)')

def classify_activity(title, content):
    """根据标题和内容分类活动"""
    combined_text = (title + " " + content).lower()
    
    for category, data in ACTIVITY_CATEGORIES.items():
        if category == "其他":
            continue
        for keyword in data["keywords"]:
            if keyword.lower() in combined_text:
                return category
    
    return "其他"

def extract_activity_info(section, title):
    """从活动内容中提取关键信息"""
    info = {
        "标题": title,
        "分类": "未分类",
        "日期": "",
        "时间": "",
        "地点": "",
        "活动名称": "",
        "ID": ""
    }
    
    # 提取ID
    id_match = re.search(r'ID: (\S+)', section)
    if id_match:
        info["ID"] = id_match.group(1)
    
    # 提取日期（从文件名）
    date_match = file_date_pattern.search(section)
    if date_match:
        info["日期"] = f"{date_match.group(1)}.{date_match.group(2)}.{date_match.group(3)}"
    
    # 提取时间信息
    time_matches = time_pattern.finditer(section)
    times = []
    for match in time_matches:
        year = match.group(1)
        month = match.group(2)
        day = match.group(3)
        hour = match.group(4) or ""
        minute = match.group(5) or ""
        
        # 只记录活动时间（包含具体时间或日期范围）
        if hour or minute:
            time_str = f"{year}.{month}.{day} {hour}:{minute}" if hour and minute else f"{year}.{month}.{day}"
        else:
            time_str = f"{year}.{month}.{day}"
        
        times.append(time_str)
    
    if times:
        info["时间"] = " | ".join(times[:3])  # 取前3个时间信息
    
    # 提取地点
    location_match = location_pattern.search(section)
    if location_match:
        location = location_match.group(1).strip()
        # 只保留南京艺术学院美术馆内的地点
        if "南京艺术学院" in location or "AMNUA" in location or "美术馆" in location:
            info["地点"] = location[:80]
    
    # 提取活动名称
    activity_match = activity_name_pattern.search(section)
    if activity_match:
        info["活动名称"] = activity_match.group(1)[:80]
    else:
        info["活动名称"] = title[:80]
    
    # 分类
    info["分类"] = classify_activity(title, section)
    
    return info

def main():
    print("=" * 80)
    print("开始提取南京艺术学院美术馆（AMNUA）的活动信息")
    print("=" * 80)
    print()
    
    activity_count = 0
    amnua_count = 0
    
    # 遍历所有merged_*.md文件
    for filename in sorted(os.listdir(DATA_DIR)):
        if not filename.startswith("merged_") or not filename.endswith(".md"):
            continue
        
        filepath = os.path.join(DATA_DIR, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 按文件头分割每个帖子
        sections = content.split('# File: ')
        
        for section in sections:
            if not section.strip():
                continue
            
            section = '# File: ' + section
            
            # 检查是否为AMNUA美术馆的内容
            if "南京艺术学院美术馆" not in section and "AMNUA" not in section:
                continue
            
            amnua_count += 1
            
            # 提取标题
            title_match = re.search(r'^#([^#].+)', section, re.MULTILINE)
            if not title_match:
                continue
            
            title = title_match.group(1).strip()[:100]
            
            # 提取活动信息
            activity_info = extract_activity_info(section, title)
            
            # 只收集有时间或地点信息的活动
            if activity_info["时间"] or activity_info["地点"]:
                category = activity_info["分类"]
                ACTIVITY_CATEGORIES[category]["activities"].append(activity_info)
                activity_count += 1
                
                # 进度提示
                if activity_count % 50 == 0:
                    print(f"已处理 {activity_count} 条有时间/地点的活动信息...")
    
    print()
    print(f"✅ 提取完成！")
    print(f"📊 总计: {amnua_count} 条AMNUA相关帖子, {activity_count} 条有明确时间/地点的活动")
    print()
    
    # 统计各分类
    print("=" * 80)
    print("活动分类统计")
    print("=" * 80)
    print()
    
    total_activities = 0
    total_reads = 0
    
    category_summary = {}
    
    for category in sorted(ACTIVITY_CATEGORIES.keys()):
        activities = ACTIVITY_CATEGORIES[category]["activities"]
        if activities:
            category_summary[category] = len(activities)
            total_activities += len(activities)
            print(f"【{category}】: {len(activities)} 条")
    
    print()
    print(f"总计: {total_activities} 条活动")
    print()
    
    # 生成分类结果文件
    output_path = os.path.join(OUTPUT_DIR, "AMNUA活动分类统计.md")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# 南京艺术学院美术馆（AMNUA）活动分类统计\n\n")
        f.write(f"统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"总计: {total_activities} 条有明确时间/地点的活动\n\n")
        f.write("=" * 80 + "\n\n")
        
        # 按分类输出
        for category in sorted(ACTIVITY_CATEGORIES.keys()):
            activities = ACTIVITY_CATEGORIES[category]["activities"]
            if not activities:
                continue
            
            f.write(f"## {category} (共{len(activities)}条)\n\n")
            
            # 按日期排序
            sorted_activities = sorted(activities, key=lambda x: x["日期"] if x["日期"] else "0000-00-00")
            
            # 表格头
            f.write("| 序号 | ID | 活动名称 | 日期 | 时间 | 地点 |\n")
            f.write("|:---:|:---:|:-----|:----:|:----:|:-----|\n")
            
            for i, activity in enumerate(sorted_activities, 1):
                activity_name = activity["活动名称"].replace("|", "｜")[:50]
                location = activity["地点"].replace("|", "｜")[:40] if activity["地点"] else "-"
                time_info = activity["时间"][:30] if activity["时间"] else "-"
                date_info = activity["日期"][:15] if activity["日期"] else "-"
                
                f.write(f"| {i} | {activity['ID']} | {activity_name} | {date_info} | {time_info} | {location} |\n")
            
            f.write("\n\n")
    
    print(f"📁 分类统计已保存至: {output_path}")
    
    # 生成JSON格式数据
    json_output = {}
    for category in sorted(ACTIVITY_CATEGORIES.keys()):
        activities = ACTIVITY_CATEGORIES[category]["activities"]
        if activities:
            json_output[category] = [
                {
                    "ID": a["ID"],
                    "标题": a["标题"],
                    "活动名称": a["活动名称"],
                    "日期": a["日期"],
                    "时间": a["时间"],
                    "地点": a["地点"]
                }
                for a in activities
            ]
    
    json_path = os.path.join(OUTPUT_DIR, "AMNUA活动分类统计.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    
    print(f"📁 JSON数据已保存至: {json_path}")

if __name__ == "__main__":
    main()
