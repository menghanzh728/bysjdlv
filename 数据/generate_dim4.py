import csv
import os
import re

def get_cultural_origin(activity_prop):
    if any(k in activity_prop for k in ["中国画", "水墨"]):
        return "东方本土"
    elif any(k in activity_prop for k in ["油画", "丙烯", "素描", "版画"]):
        return "西方架上"
    elif any(k in activity_prop for k in ["当代艺术", "影像", "数字"]):
        return "全球化语境"
    else:
        return "混合/其他"

def get_radiation_level(participants, co_organizers):
    # Level 3 (International)
    intl_keywords = ["国", "领事馆", "使馆", "歌德学院", "国际", "中外", "中韩", "中德", "中法", "中日", "中英", "美国", "德国", "法国", "韩国", "日本", "英国", "意大利", "大使馆", "文化中心"]
    
    has_intl_participant = False
    if participants != "N/A":
        # Remove common abbreviations and IDs
        clean_p = re.sub(r'ID_\d+', '', participants)
        clean_p = clean_p.replace("N/A", "").replace("AMNUA", "").replace(" Curator", "").replace("Artist", "").replace("Team", "")
        # Check for 3+ consecutive English letters (foreign names)
        if re.search(r'[a-zA-Z]{3,}', clean_p):
            has_intl_participant = True
        # Check for country names in brackets
        if any(f"（{k}）" in participants or f"({k})" in participants for k in ["韩国", "德国", "美国", "法国", "日本", "英国", "意大利", "国外", "外籍"]):
            has_intl_participant = True

    has_intl_organizer = any(k in co_organizers for k in intl_keywords)
    
    if has_intl_participant or has_intl_organizer:
        return "国际级"

    # Level 2 (National)
    national_keywords = [
        "北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "西安", "武汉",
        "中国美术馆", "国家博物馆", "中华艺术宫", "中央美术学院", "中国美术学院", 
        "UCCA", "OCAT", "龙美术馆", "余德耀", "西岸", "和美术馆", "今日美术馆", "时代美术馆"
    ]
    if any(k in co_organizers for k in national_keywords):
        return "全国级"
    
    # Check for other domestic museums/universities not specific to Nanjing/Jiangsu
    if any(k in co_organizers for k in ["美术馆", "博物馆", "大学", "艺术中心"]):
        if not any(k in co_organizers for k in ["南艺", "南京", "江苏", "南京艺术学院"]):
            return "全国级"

    # Level 1 (Local/School)
    return "本土级"

def extract_co_organizers(event_text):
    patterns = [
        r'协办单位[:：]\s*([^>\n\r|]+)',
        r'承办单位[:：]\s*([^>\n\r|]+)',
        r'主办单位[:：]\s*([^>\n\r|]+)',
        r'主办[:：]\s*([^>\n\r|]+)',
        r'协办[:：]\s*([^>\n\r|]+)',
        r'支持单位[:：]\s*([^>\n\r|]+)'
    ]
    found = []
    for p in patterns:
        matches = re.findall(p, event_text[:2500])
        for m in matches:
            # Clean up trailing punctuation
            val = m.strip().rstrip('。').rstrip('；')
            found.append(val)
    return " / ".join(list(set(found))) if found else ""

def process_dim4():
    src_csv = "/Users/zmh/Desktop/合集/维度一：总信息/维度一_全量汇总.csv"
    src_dir = "/Users/zmh/Desktop/合集/精简文本数据_标准化"
    out_csv = "/Users/zmh/Desktop/合集/维度四：文化辐射度/维度四_文化辐射度分析.csv"
    
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
    headers_out = ["ID", "活动名称", "活动性质3", "策划人", "协办方/承办方", "文化溯源分类", "地理辐射能级"]
    
    with open(src_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            event_id = row.get("ID")
            activity_name = row.get("活动名称")
            activity_prop = row.get("活动性质3", "")
            participants = row.get("策划人", "")
            
            source_text = source_data.get(event_id, "")
            co_organizers = extract_co_organizers(source_text)
            
            cultural_origin = get_cultural_origin(activity_prop)
            radiation_level = get_radiation_level(participants, co_organizers)
            
            results.append({
                "ID": event_id,
                "活动名称": activity_name,
                "活动性质3": activity_prop,
                "策划人": participants,
                "协办方/承办方": co_organizers,
                "文化溯源分类": cultural_origin,
                "地理辐射能级": radiation_level
            })
            
    with open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers_out)
        writer.writeheader()
        writer.writerows(results)
    
    return len(results)

if __name__ == "__main__":
    count = process_dim4()
    print(f"Successfully processed {count} records for Dimension 4.")
