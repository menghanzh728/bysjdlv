import os
import re

output_dir = "/Users/zmh/Desktop/合集/维度二：系列与空间"

# 需要删除的关键词
delete_keywords = [
    '荐文', '特刊', '影评', '杂谈', '随笔', '书评', '纪念丨', '在线放送', '沈从文', '狂人日记', '母亲节', '谈人生', '百科'
]

# 排除例外：如果标题包含这些词，即使包含垃圾词也要保留
keep_markers = ['展览', '项目', '讲座', '演出', '首映', '音乐会']

processed_count = 0
deleted_count = 0

for i in range(1, 11):
    file_path = os.path.join(output_dir, f"维度二_合并_{i}.md")
    if not os.path.exists(file_path):
        continue
        
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    header = lines[:2]
    new_lines.extend(header)
    
    for line in lines[2:]:
        if not line.strip():
            continue
            
        should_delete = False
        # 检查是否命中删除关键词
        if any(k in line for k in delete_keywords):
            should_delete = True
            # 检查是否有保护词
            if any(m in line for k in keep_markers):
                should_delete = False
        
        # 特殊处理：剧本朗读《艺术》及其系列
        if '实验戏剧展演单元' in line:
            # 确保地点被更新为 4号展厅
            line = re.sub(r'\| [^|]+ \|$', '| 4号展厅（自动填充） |', line.strip()) + '\n'
            should_delete = False

        if should_delete:
            deleted_count += 1
        else:
            new_lines.append(line)
            
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

print(f"Deleted {deleted_count} non-activity lines from merged files.")
