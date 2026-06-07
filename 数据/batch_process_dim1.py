import re
import os
import csv

def parse_merged_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    events = content.split('========== [EVENT_START] ==========')
    results = []
    
    for event in events:
        event = event.strip()
        if not event:
            continue
            
        id_match = re.search(r'ID:\s+(ID_\d+)', event)
        if not id_match:
            continue
        event_id = id_match.group(1)
        
        lines = event.split('\n')
        title = "N/A"
        for line in lines:
            line = line.strip()
            if line.startswith('#') and not line.startswith('# File:'):
                title = line.lstrip('#').strip()
                break
        
        if title == "N/A": continue

        # --- Inclusive Filtering Logic (Dimension 1) ---
        exclude_filters = ["招聘", "招募", "节假日", "咨询", "公告"]
        if any(f in title for f in exclude_filters):
            if not any(k in event for k in ["前言", "学术主持"]):
                continue
        
        process_filters = ["闭展", "预览", "回顾", "明日开展", "即将开展", "即将开幕", "今日开展", "今日开幕"]
        if any(f in title for f in process_filters):
            if len(event) < 600 and not any(k in title for k in ["讲座", "对谈", "公教", "工作坊"]):
                if not any(k in event for k in ["前言", "主办单位", "承办单位"]):
                    continue

        # Extract Time
        time_str = "N/A"
        date_range_pattern = r'(\d{4}\.\d{2}\.\d{2})\s*[—\-至~]\s*(\d{4}\.\d{2}\.\d{2})'
        range_match = re.search(date_range_pattern, title)
        if not range_match:
            range_match = re.search(date_range_pattern, event)
        if range_match:
            time_str = f"{range_match.group(1)}—{range_match.group(2)}"
        else:
            single_date_match = re.search(r'(\d{4}\.\d{2}\.\d{2})', title)
            if not single_date_match:
                time_line_match = re.search(r'时间：(\d{4}\.\d{2}\.\d{2})', event)
                if time_line_match:
                    time_str = time_line_match.group(1)
                else:
                    any_date_match = re.search(r'(\d{4}\.\d{2}\.\d{2})', event)
                    if any_date_match:
                        time_str = any_date_match.group(1)

        # Activity Function
        func = "其他"
        if any(k in title for k in ["展", "展览", "第.回", "单元", "回"]):
            func = "展览"
        elif any(k in title for k in ["讲座", "对谈", "研讨会", "沙龙", "对话", "论坛", "讲演"]):
            func = "讲座"
        elif any(k in title for k in ["公教", "导览", "工作坊", "少儿", "体验", "延伸活动", "项目"]):
            func = "公教"
        elif any(k in title for k in ["现场", "音乐节", "演出", "剧场", "放映", "首映", "发布", "开幕"]):
            func = "艺术现场"
        elif "驻地" in title or "驻场" in title:
            func = "驻地项目"
        elif any(k in title for k in ["馆长声音", "艺评", "评论", "学术研究", "沈从文"]):
            func = "学术评论/言论"
        elif any(k in title for k in ["报道", "新闻", "世界美术馆之旅", "动态"]):
            func = "资讯/动态"

        # Form
        form = "N/A"
        is_online = any(k in title or k in event[:300] for k in ["线上", "虚拟", "VR", "网络", "视频", "直播"])
        if func == "展览":
            form = "线上展览" if is_online else "线下展览"
        elif func == "讲座":
            form = "专题讲座"
        elif func == "公教":
            form = "工作坊/导览"
        elif func == "艺术现场":
            form = "演出/活动"
        elif func == "驻地项目":
            form = "驻场创作"
        elif func == "学术评论/言论":
            form = "文章/论文"
        elif func == "资讯/动态":
            form = "图文报道"

        # Medium
        medium = "综合"
        mediums = ["水墨", "油画", "影像", "素描", "雕塑", "设计", "摄影", "装置", "木刻", "版画", "漫画", "多媒体", "动画", "剧场", "音乐"]
        for m in mediums:
            if m in title or m in event[:1000]:
                medium = m
                break

        # Series
        series = "N/A"
        series_list = ["水墨档案", "影像档案", "零方案", "素描系列展", "复调", "时区", "思想剧场", "教学相长", "世界美术馆之旅", "馆长声音", "零度艺评"]
        for s in series_list:
            if s in title:
                series = s
                break
        
        org_type = "系列活动" if series != "N/A" else "独立活动"
        prop1 = "其他"
        if func == "展览": prop1 = "艺术展览"
        elif func == "讲座": prop1 = "学术讲座"
        elif func == "公教": prop1 = "公共教育"
        elif func == "艺术现场": prop1 = "艺术现场"
        elif func == "学术评论/言论": prop1 = "学术研究"
        elif func == "资讯/动态": prop1 = "资讯报道"

        prop2 = "N/A"
        if func == "展览":
            if "个展" in title:
                prop2 = "个展"
            elif any(k in title for k in ["联展", "群展", "邀请展", "中外", "中韩", "中德", "交流展"]):
                prop2 = "群展"
        prop3 = medium
        field = "跨学科/泛文化" if medium == "综合" else "纯艺术"
        theme = "N/A"

        # Location
        loc = "N/A"
        loc_candidates = []
        loc_patterns = {
            "4号展厅": ["4号展厅", "地下一层", "B1"],
            "0号展厅": ["0号展厅"],
            "1号展厅": ["1号展厅"],
            "2号展厅": ["2号展厅"],
            "3号展厅": ["3号展厅"],
            "5号展厅": ["5号展厅"],
            "影像空间": ["影像空间"],
            "公共空间": ["公共空间", "艺术广场"],
            "学术报告厅": ["学术报告厅", "报告厅"],
            "线上活动": ["线上", "直播", "导览", "虚拟"]
        }
        for l, p in loc_patterns.items():
            if any(k in event[:1500] for k in p):
                loc_candidates.append(l)
        if loc_candidates:
            if "线上活动" in loc_candidates and len(loc_candidates) > 1:
                loc_candidates.remove("线上活动")
            loc = ", ".join(sorted(list(set(loc_candidates))))
        if loc == "N/A" or loc == "":
            series_loc_mapping = {
                "水墨档案": "学术报告厅",
                "影像档案": "影像空间",
                "零方案": "0号展厅",
                "素描系列展": "5号展厅",
                "复调": "3号展厅",
                "时区": "3号展厅",
                "思想剧场": "学术报告厅"
            }
            if series in series_loc_mapping:
                loc = f"{series_loc_mapping[series]} (自动填充)"

        # Curator / Subject
        subjects = []
        subject_patterns = [
            (r'策\s*展\s*人[:：]\s*([^>\n\r|]+)', "策展人"),
            (r'学\s*术\s*主\s*持[:：]\s*([^>\n\r|]+)', "学术主持"),
            (r'策\s*划[:：]\s*([^>\n\r|]+)', "策划"),
            (r'出\s*品\s*人[:：]\s*([^>\n\r|]+)', "出品人"),
            (r'主\s*讲\s*人[:：]\s*([^>\n\r|]+)', "主讲人"),
            (r'讲\s*者[:：]\s*([^>\n\r|]+)', "讲者"),
            (r'对\s*谈\s*人[:：]\s*([^>\n\r|]+)', "对谈人"),
            (r'嘉\s*宾[:：]\s*([^>\n\r|]+)', "嘉宾"),
            (r'艺\s*术\s*家[:：]\s*([^>\n\r|]+)', "艺术家"),
            (r'参\s*展\s*艺\s*术\s*家[:：]\s*([^>\n\r|]+)', "艺术家"),
            (r'导\s*演[:：]\s*([^>\n\r|]+)', "导演"),
            (r'执\s*行\s*策\s*展[:：]\s*([^>\n\r|]+)', "执行策展"),
            (r'展\s*览\s*执\s*行[:：]\s*([^>\n\r|]+)', "展览执行"),
            (r'作\s*者[:：]\s*([^>\n\r|]+)', "作者"),
        ]
        
        found_curators = set()
        for pattern, label in subject_patterns:
            matches = re.findall(pattern, event[:3000])
            for m in matches:
                name = m.strip()
                if any(k in name for k in ["时间", "南京艺术学院美术馆", "AMNUA", "开放时间", "虎踞北路"]) or name == "":
                    continue
                name = re.sub(r'\s+', ' ', name)
                if name:
                    subjects.append(f"{label}:{name}")
                    found_curators.add(name)
        
        meta_author_match = re.search(r'>作者：\s*([^\s\t|]+)', event)
        if meta_author_match:
            meta_author = meta_author_match.group(1).strip()
            if not meta_author.startswith('时间') and meta_author not in ["南京艺术学院美术馆", "AMNUA", ""]:
                if meta_author not in found_curators:
                    subjects.append(f"作者:{meta_author}")

        curator = "; ".join(subjects) if subjects else "N/A"
        results.append([event_id, time_str, title, func, form, medium, org_type, series, prop1, prop2, prop3, field, theme, loc, curator])
    
    return results

def write_outputs(results, md_path, csv_path):
    headers = ["ID", "活动时间", "活动名称", "活动职能", "表现形式", "学科媒介", "活动组织类型", "系列标签", "活动性质1", "活动性质2", "活动性质3", "活动领域", "活动主题标签", "活动地点", "策划人"]
    
    # MD
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("| " + " | ".join([":---:"] * len(headers)) + " |\n")
        for row in results:
            clean_row = [str(x).replace('|', '\\|').replace('\n', ' ').replace('\r', '') for x in row]
            f.write("| " + " | ".join(clean_row) + " |\n")
            
    # CSV
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(results)

if __name__ == "__main__":
    src_dir = "/Users/zmh/Desktop/合集/精简文本数据_标准化"
    out_dir = "/Users/zmh/Desktop/合集/维度一：总信息"
    os.makedirs(out_dir, exist_ok=True)
    
    all_results = []
    
    # Process all 50 files
    for i in range(1, 51):
        src_file = os.path.join(src_dir, f"merged_{i}.md")
        if os.path.exists(src_file):
            print(f"Processing {src_file}...")
            file_results = parse_merged_file(src_file)
            all_results.extend(file_results)
            
            # Also save individual file analysis
            md_out = os.path.join(out_dir, f"merged_{i}_分类.md")
            csv_out = os.path.join(out_dir, f"merged_{i}_分类.csv")
            write_outputs(file_results, md_out, csv_out)
    
    # Finally, group into 10 master files (approx 5 files each)
    chunk_size = 5
    for j in range(0, 10):
        start_idx = j * chunk_size + 1
        end_idx = (j + 1) * chunk_size
        chunk_results = []
        for k in range(start_idx, end_idx + 1):
            src_file = os.path.join(src_dir, f"merged_{k}.md")
            if os.path.exists(src_file):
                chunk_results.extend(parse_merged_file(src_file))
        
        if chunk_results:
            master_md = os.path.join(out_dir, f"维度一_合并_{j+1}.md")
            master_csv = os.path.join(out_dir, f"维度一_合并_{j+1}.csv")
            write_outputs(chunk_results, master_md, master_csv)
            print(f"Saved merged group {j+1}")

    print("Batch processing complete.")
