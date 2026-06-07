import csv
import os
import re

def count_participants(curator_str):
    if not curator_str or curator_str == "N/A":
        return 0
    # Participants are usually in '艺术家:xxx' or '主讲人:xxx' or '嘉宾:xxx'
    # We split by ';' and then check if the role is participant-related
    parts = curator_str.split(";")
    count = 0
    for part in parts:
        if ":" in part:
            role, names = part.split(":", 1)
            role = role.strip()
            if role in ["艺术家", "主讲人", "嘉宾", "对谈人", "参展艺术家", "导演", "作者"]:
                # Split names by common delimiters like '、', ',', '，', ' '
                name_list = re.split(r'[、,，\s]+', names.strip())
                # Filter out empty strings
                name_list = [n for n in name_list if n.strip()]
                count += len(name_list)
    return count

def extract_theme_tags(activity_name, event_text):
    # Heuristic for theme tags based on keywords or quoted text in title
    tags = []
    # 1. Quoted text in title often indicates a theme
    quotes = re.findall(r'[“"《]([^”"》]+)[”"》]', activity_name)
    if quotes:
        tags.extend(quotes)
    
    # 2. Keywords in first 500 chars of event text
    keywords = ["当代", "实验", "传统", "历史", "记忆", "社会", "空间", "媒介", "身份", "自然", "科技", "身体", "观念"]
    for k in keywords:
        if k in event_text[:500]:
            tags.append(k)
            
    return "; ".join(list(set(tags))) if tags else "N/A"

def process_dim5():
    src_csv = "/Users/zmh/Desktop/合集/维度一：总信息/维度一_全量汇总.csv"
    src_dir = "/Users/zmh/Desktop/合集/精简文本数据_标准化"
    out_csv = "/Users/zmh/Desktop/合集/维度五：品牌演进/维度五_品牌演进分析.csv"
    
    # Pre-load source texts for theme extraction
    source_data = {}
    for i in range(1, 51):
        file_path = os.path.join(src_dir, f"merged_{i}.md")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            events = content.split('========== [EVENT_START] ==========')
            for event in events:
                id_match = re.search(r'ID:\s+(ID_\d+)', event)
                if id_match:
                    source_data[id_match.group(1)] = event

    results = []
    headers_out = ["ID", "系列标签", "年份", "活动名称", "参与人数", "活动主题标签"]
    
    if not os.path.exists(src_csv):
        print(f"Error: {src_csv} not found.")
        return

    with open(src_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            series_label = row.get("系列标签", "N/A")
            # Only track if it belongs to a series
            if series_label == "N/A" or not series_label:
                continue
                
            event_id = row.get("ID")
            activity_name = row.get("活动名称")
            time_str = row.get("活动时间", "")
            curator_str = row.get("策划人", "")
            
            # Extract Year
            year_match = re.search(r'(\d{4})', time_str)
            year = year_match.group(1) if year_match else "N/A"
            
            # Count Participants
            participant_count = count_participants(curator_str)
            
            # Extract Theme Tags
            source_text = source_data.get(event_id, "")
            theme_tags = extract_theme_tags(activity_name, source_text)
            
            results.append({
                "ID": event_id,
                "系列标签": series_label,
                "年份": year,
                "活动名称": activity_name,
                "参与人数": participant_count,
                "活动主题标签": theme_tags
            })
            
    # Sort results by Series Label and then Year to show evolution
    results.sort(key=lambda x: (x["系列标签"], x["年份"]))
    
    with open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers_out)
        writer.writeheader()
        writer.writerows(results)
    
    return len(results)

if __name__ == "__main__":
    count = process_dim5()
    print(f"Successfully processed {count} series records for Dimension 5.")
