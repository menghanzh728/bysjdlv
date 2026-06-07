#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析精简文本数据文件夹中的每年每月发帖量和阅读量
不修改源文件，结果存入新文件
"""

import os
import re
import json
from collections import defaultdict
from datetime import datetime

# 文件夹路径
DATA_DIR = "/Users/zmh/Desktop/重新清洗/精简文本数据_标准化"
OUTPUT_DIR = DATA_DIR  # 结果也存到同一目录

# 用于存储每年每月的统计数据
# 结构: { year: { month: {"posts": 0, "total_reads": 0, "reads_list": [], "post_details": []} } }
stats = defaultdict(lambda: defaultdict(lambda: {"posts": 0, "total_reads": 0, "reads_list": [], "post_details": []}))

# 匹配文件头中的日期: # File: 数字_YYYYMMDD_...
file_date_pattern = re.compile(r'^# File: \d+_(\d{4})(\d{2})\d{2}_')

# 匹配阅读量: >阅读：数字
read_count_pattern = re.compile(r'>阅读：(\d+)')

# 匹配时间行: >作者：\t时间：YYYY.MM.DD ...
time_pattern = re.compile(r'>作者：\s*时间：(\d{4})\.(\d{2})\.\d{2}')

# 遍历所有 merged_*.md 文件
total_posts = 0
total_reads = 0

for filename in sorted(os.listdir(DATA_DIR)):
    if not filename.startswith("merged_") or not filename.endswith(".md"):
        continue
    
    filepath = os.path.join(DATA_DIR, filename)
    print(f"正在处理: {filename}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按 [EVENT_START] 或文件边界分割每个帖子
    # 实际上每个帖子以 "# File:" 开头
    sections = content.split('# File: ')
    
    for section in sections:
        if not section.strip():
            continue
        
        section = '# File: ' + section
        
        # 从文件名中提取日期 (最可靠)
        file_match = file_date_pattern.search(section)
        
        # 或者从时间行提取日期
        time_match = time_pattern.search(section)
        
        year = None
        month = None
        
        if file_match:
            year = file_match.group(1)
            month = file_match.group(2)
        elif time_match:
            year = time_match.group(1)
            month = time_match.group(2)
        
        # 提取帖子标题 - 找第二个 # 开头的行（真正的标题）
        post_title = ""
        # 先按行分割，找第二个以 # 开头且不包含 "File:" 的行
        lines = section.split('\n')
        title_found = False
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith('#') and 'File:' not in line_stripped and 'ID:' not in line_stripped:
                post_title = line_stripped.lstrip('#').strip()
                title_found = True
                break
        if not title_found:
            # 回退：从文件名提取可读标题
            fn_match = re.search(r'# File: \d+_\d+_\d+_(.+)\.md', section)
            if fn_match:
                post_title = fn_match.group(1).replace('_', ' ')[:60]
        
        # 提取ID
        id_match = re.search(r'ID: (\S+)', section)
        post_id = id_match.group(1) if id_match else ""
        
        # 从文件名中提取完整日期 - 使用更灵活的匹配方式
        file_date_full = ""
        # 从 # File: 行提取日期
        file_line_match = re.search(r'# File: \d+_(\d{4})(\d{2})(\d{2})_', section)
        if file_line_match:
            file_date_full = f"{file_line_match.group(1)}.{file_line_match.group(2)}.{file_line_match.group(3)}"
        elif time_match:
            # 从时间行提取日期
            td = re.search(r'>作者：\s*时间：(\d{4})\.(\d{2})\.(\d{2})', section)
            if td:
                file_date_full = f"{td.group(1)}.{td.group(2)}.{td.group(3)}"
        
        if year and month:
            # 提取阅读量
            read_match = read_count_pattern.search(section)
            read_count = 0
            if read_match:
                read_count = int(read_match.group(1))
            
            stats[year][month]["posts"] += 1
            stats[year][month]["total_reads"] += read_count
            stats[year][month]["reads_list"].append(read_count)
            stats[year][month]["post_details"].append({
                "id": post_id,
                "title": post_title[:60] if post_title else "(无标题)",
                "date": file_date_full,
                "reads": read_count
            })
            
            total_posts += 1
            total_reads += read_count

# 生成结果文件
output_lines = []
output_lines.append("# 精简文本数据 - 每年每月发帖量与阅读量统计")
output_lines.append(f"# 统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
output_lines.append(f"# 数据范围: 共 {len(stats)} 年, 总计 {total_posts} 条帖子, 总阅读量 {total_reads}")
output_lines.append("")

# ============================================================
# 一、每年总览
# ============================================================
output_lines.append("")
output_lines.append("=" * 80)
output_lines.append("一、每年总览")
output_lines.append("=" * 80)
output_lines.append("")

output_lines.append(f"| 年份 | 发帖量(条) | 总阅读量 | 平均阅读量/帖 | 最高阅读量帖子 | 阅读量 |")
output_lines.append(f"|:---:|:--------:|:--------:|:------------:|:--------------|:----:|")

for year in sorted(stats.keys()):
    yearly_posts = sum(stats[year][m]["posts"] for m in stats[year])
    yearly_reads = sum(stats[year][m]["total_reads"] for m in stats[year])
    yearly_avg = yearly_reads / yearly_posts if yearly_posts > 0 else 0
    
    # 找全年最高阅读量的帖子
    all_details = []
    for m in stats[year]:
        all_details.extend(stats[year][m]["post_details"])
    top_post = max(all_details, key=lambda x: x["reads"]) if all_details else None
    
    if top_post:
        top_title = top_post["title"].replace("|", "｜")[:30]
        top_display = f"{top_post['date']} {top_title}"
    else:
        top_display = "-"
    top_reads = top_post["reads"] if top_post else "-"
    
    output_lines.append(f"| {year} | {yearly_posts} | {yearly_reads} | {yearly_avg:.1f} | {top_display} | {top_reads} |")

output_lines.append("")

# ============================================================
# 二、每年每月最高阅读量帖子 + 平均阅读量
# ============================================================
output_lines.append("")
output_lines.append("=" * 80)
output_lines.append("二、每年每月最高阅读量帖子与平均阅读量")
output_lines.append("=" * 80)
output_lines.append("")

for year in sorted(stats.keys()):
    yearly_posts = sum(stats[year][m]["posts"] for m in stats[year])
    yearly_reads = sum(stats[year][m]["total_reads"] for m in stats[year])
    yearly_avg = yearly_reads / yearly_posts if yearly_posts > 0 else 0
    
    output_lines.append(f"\n## {year}年 (总发帖: {yearly_posts}, 总阅读: {yearly_reads}, 年平均: {yearly_avg:.1f})\n")
    output_lines.append(f"| 月份 | 发帖量 | 总阅读量 | 月平均阅读量 | 最高阅读量 | 最高阅读帖子ID | 最高阅读帖子标题 |")
    output_lines.append(f"|:---:|:-----:|:-------:|:----------:|:---------:|:-------------:|:----------------|")
    
    for month in sorted(stats[year].keys()):
        m_data = stats[year][month]
        avg_reads = m_data["total_reads"] / m_data["posts"] if m_data["posts"] > 0 else 0
        
        # 找本月最高阅读量帖子
        top_post = max(m_data["post_details"], key=lambda x: x["reads"])
        
        top_title_display = top_post["title"].replace("|", "｜")[:35]
        
        output_lines.append(f"| {month}月 | {m_data['posts']} | {m_data['total_reads']} | {avg_reads:.1f} | {top_post['reads']} | {top_post['id']} | {top_title_display} |")
    
    # 年度汇总行
    output_lines.append(f"| **全年** | **{yearly_posts}** | **{yearly_reads}** | **{yearly_avg:.1f}** | | | |")
    output_lines.append("")

# ============================================================
# 三、每月汇总数据表
# ============================================================
output_lines.append("")
output_lines.append("=" * 80)
output_lines.append("三、每月汇总数据")
output_lines.append("=" * 80)
output_lines.append("")

for year in sorted(stats.keys()):
    output_lines.append(f"\n## {year}年\n")
    output_lines.append(f"| 月份 | 发帖量(条) | 阅读量 | 平均阅读量/帖 |")
    output_lines.append(f"|------|-----------|--------|--------------|")
    for month in sorted(stats[year].keys()):
        m_data = stats[year][month]
        avg_reads = m_data["total_reads"] / m_data["posts"] if m_data["posts"] > 0 else 0
        output_lines.append(f"| {month}月 | {m_data['posts']} | {m_data['total_reads']} | {avg_reads:.1f} |")
    
    y_posts = sum(stats[year][m]["posts"] for m in stats[year])
    y_reads = sum(stats[year][m]["total_reads"] for m in stats[year])
    y_avg = y_reads / y_posts if y_posts > 0 else 0
    output_lines.append(f"| **合计** | **{y_posts}** | **{y_reads}** | **{y_avg:.1f}** |")
    output_lines.append("")

# ============================================================
# 四、每条帖子的阅读量明细
# ============================================================
output_lines.append("")
output_lines.append("=" * 80)
output_lines.append("四、每条帖子的阅读量明细")
output_lines.append("=" * 80)
output_lines.append("")

for year in sorted(stats.keys()):
    output_lines.append(f"\n## {year}年\n")
    for month in sorted(stats[year].keys()):
        m_data = stats[year][month]
        output_lines.append(f"\n### {year}年{month}月 (共{m_data['posts']}条帖子, 总阅读量: {m_data['total_reads']})\n")
        output_lines.append(f"| 序号 | 帖子ID | 日期 | 标题 | 阅读量 |")
        output_lines.append(f"|:---:|:------:|:----:|:----|:----:|")
        
        # 按日期排序
        sorted_details = sorted(m_data["post_details"], key=lambda x: x["date"])
        for i, detail in enumerate(sorted_details, 1):
            title_display = detail["title"].replace("|", "｜")[:40]
            output_lines.append(f"| {i} | {detail['id']} | {detail['date']} | {title_display} | {detail['reads']} |")
        
        output_lines.append("")

# 写入结果文件
output_path = os.path.join(OUTPUT_DIR, "每年每月发帖量与阅读量统计.md")
with open(output_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print(f"\n✅ 统计完成！")
print(f"📊 总计: {total_posts} 条帖子, {total_reads} 阅读量")
print(f"📁 结果已保存至: {output_path}")

# 同时输出JSON格式方便后续处理
json_output = {}
for year in sorted(stats.keys()):
    json_output[year] = {}
    for month in sorted(stats[year].keys()):
        m_data = stats[year][month]
        json_output[year][month] = {
            "posts": m_data["posts"],
            "total_reads": m_data["total_reads"],
            "avg_reads_per_post": round(m_data["total_reads"] / m_data["posts"], 1) if m_data["posts"] > 0 else 0,
            "post_details": sorted(m_data["post_details"], key=lambda x: x["date"])
        }

json_path = os.path.join(OUTPUT_DIR, "每年每月发帖量与阅读量统计.json")
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(json_output, f, ensure_ascii=False, indent=2)
print(f"📁 JSON结果已保存至: {json_path}")
