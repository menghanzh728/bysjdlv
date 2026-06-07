import re
import os

input_file = "/Users/zmh/Desktop/合集/精简文本数据_标准化/merged_1.md"
output_file = "/Users/zmh/Desktop/合集/维度一：总信息/merged_1_分类.md"

series_main_spaces = {
    '复调': '3号展厅', '零方案': '0号展厅', '影像档案': '影像空间',
    '素描系列展': '5号展厅', '水墨档案': '学术报告厅', '思想剧场': '学术报告厅',
    '再不远行就老了': '公共空间', '实验戏剧': '4号展厅', '英语角': '咖啡厅',
    '工作坊': '公共空间'
}

def standardize_space(space_str, block_content="", series_name="N/A"):
    if any(k in space_str or k in block_content[:500] for k in ['网络展', '微展览', '云端展', '扫码观看', '直播', '线上']):
        if '地点' not in block_content or '展厅' not in block_content: return "线上活动"
    
    mapping = {
        '4号展厅': ['地下一层', '负一楼', '4号展厅', '4展厅'],
        '0号展厅': ['0号展厅', '0展厅', '零号', '零展厅', '零空间'],
        '1号展厅': ['1号展厅', '1展厅', '一层', '一楼'],
        '2号展厅': ['2号展厅', '2展厅', '二层', '二楼'],
        '3号展厅': ['3号展厅', '3展厅', '三层', '三楼'],
        '5号展厅': ['5号展厅', '5展厅'],
        '影像空间': ['影像空间', '影像厅'],
        '学术报告厅': ['报告厅', '研讨厅'],
        '多功能厅': ['多功能厅'],
        '公共空间': ['公共空间']
    }
    found = []
    for std, keywords in mapping.items():
        if any(k in space_str for k in keywords):
            if std == '1号展厅' and '负一楼' in space_str: continue
            found.append(std)
    if not found:
        if '毕业作品联展' in block_content or '闳约深美' in block_content: return "美术馆全域"
        if series_name in series_main_spaces: return series_main_spaces[series_name]
    return ", ".join(sorted(list(set(found)))) if found else "N/A"

def extract_curators(block):
    curators = []
    # 更加精准的提取
    p_curator = re.search(r'策展人[：/]\s*([^>\n\r\s|;]+)', block)
    if p_curator: curators.append(f"策展人:{p_curator.group(1).strip()}")
    p_academic = re.search(r'学术主持[：/]\s*([^>\n\r\s|;]+)', block)
    if p_academic: curators.append(f"学术主持:{p_academic.group(1).strip()}")
    p_plan = re.search(r'策划[：/]\s*([^>\n\r\s|;]+)', block)
    if p_plan: curators.append(f"策划:{p_plan.group(1).strip()}")
    return "; ".join(curators) if curators else "N/A"

def extract_time(block):
    # 提取第一个出现的日期区间或日期
    dates = re.findall(r'\d{4}[.\-/]\d{2}[.\-/]\d{2}', block)
    if len(dates) >= 2: return f"{dates[0]}—{dates[1]}"
    if dates: return dates[0]
    return "N/A"

def classify(title, block):
    func, form, medium = "其他", "N/A", "综合"
    if any(k in title for k in ['展览', '开展', '开幕', '个展', '联展', '档案', '作品展']):
        func, form = "展览", "线下展览"
    elif any(k in title for k in ['讲座', '论坛', '分享会', '研讨', '对话']):
        if any(k in title for k in ['讲座', '论坛']): func, form = "讲座", "专题讲座"
        else: func, form = "学术研讨", "对谈/讲座"
    elif any(k in title for k in ['工作坊', '活动', '导览', '征集']):
        func, form = "公教", "工作坊/导览"
    elif any(k in title for k in ['演出', '剧', '音乐', '现场']):
        func, form = "艺术现场", "演出/活动"
    elif '零方案' in title:
        func, form = "驻地项目", "驻场创作"

    # 媒介 (仅在标题或开头段落匹配，避免误伤)
    head = block[:500]
    if '水墨' in title or '水墨' in head: medium = "水墨"
    elif '油画' in title or '油画' in head: medium = "油画"
    elif '影像' in title or '影像' in head: medium = "影像"
    elif '素描' in title or '素描' in head: medium = "素描"
    elif '设计' in title or '设计' in head: medium = "设计"
    
    return func, form, medium

# 极致过滤：同步用户之前的去噪要求
garbage_keywords = [r'艺评', r'报道', r'推荐', r'荐文', r'评论', r'随笔', r'杂谈', r'特刊', r'招聘', r'公告']
garbage_regex = re.compile('|'.join(garbage_keywords))

with open(input_file, 'r', encoding='utf-8') as f:
    content = f.read()

blocks = content.split('========== [EVENT_START] ==========')
final_rows = []

for block in blocks:
    if not block.strip(): continue
    
    id_match = re.search(r'ID:\s*(ID_\d+)', block)
    assigned_id = id_match.group(1) if id_match else "N/A"
    
    title_match = re.search(r'^#(?!\s*File:)\s*(.*)$', block, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Unknown"
    title_clean = re.split(r'[|丨]', title)[0].strip()
    
    # 过滤非活动
    if garbage_regex.search(title): continue
    if len(block) < 800 and not any(k in title for k in ['开展', '讲座', '开幕', '演出']): continue

    f, fr, m = classify(title_clean, block)
    t = extract_time(block)
    
    s_label = "N/A"
    for s in ['零方案', '影像档案', '素描系列展', '水墨档案', '复调']:
        if s in title or s in block[:500]:
            s_label = s
            break
            
    loc_match = re.search(r'地点[：/]\s*([^>\n\r]+)', block) or re.search(r'展厅[：/]\s*([^>\n\r]+)', block)
    loc = standardize_space(loc_match.group(1).strip() if loc_match else "", block, s_label)
    cur = extract_curators(block)
    
    final_rows.append([
        assigned_id, t, title_clean, f, fr, m, 
        "系列活动" if s_label != "N/A" else "独立活动",
        s_label, 
        "艺术展览" if f == "展览" else "公共教育" if f == "公教" else "学术讲座" if f == "讲座" else "其他",
        "个展" if "个展" in title else "群展" if any(k in title for k in ["联展", "群展", "中韩", "中德"]) else "N/A",
        m,
        "纯艺术" if m != "综合" else "跨学科/泛文化",
        "N/A", loc, cur
    ])

# 写入
headers = ["ID", "活动时间", "活动名称", "活动职能", "表现形式", "学科媒介", "活动组织类型", "系列标签", "活动性质1", "活动性质2", "活动性质3", "活动领域", "活动主题标签", "活动地点", "策划人"]
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("| " + " | ".join(headers) + " |\n")
    f.write("| " + " | ".join([":---:"] * len(headers)) + " |\n")
    for row in final_rows:
        f.write("| " + " | ".join(row) + " |\n")

print(f"Successfully re-edited {output_file} with {len(final_rows)} activities.")
