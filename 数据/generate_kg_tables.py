import csv
import os
import re

def clean_name(name):
    # Remove extra spaces, brackets, etc.
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def extract_kg_dimensions(src_csv, out_csv):
    results = []
    headers_out = ["活动名称", "艺术总监", "策展人", "参与人员", "观众类型"]
    
    with open(src_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            activity_name = row.get("活动名称", "N/A")
            curator_field = row.get("策划人", "N/A")
            activity_func = row.get("活动职能", "N/A")
            
            art_directors = []
            curators = []
            participants = []
            
            if curator_field != "N/A":
                parts = curator_field.split(";")
                for part in parts:
                    if ":" in part:
                        role, name = part.split(":", 1)
                        role = role.strip()
                        name = clean_name(name)
                        
                        if role in ["出品人", "艺术总监", "项目总监", "监制"]:
                            art_directors.append(name)
                        elif role in ["策展人", "学术主持", "策划", "执行策展", "展览执行", "策 展 人"]:
                            curators.append(name)
                        elif role in ["主讲人", "讲者", "对谈人", "嘉宾", "艺术家", "参展艺术家", "导演", "作者"]:
                            participants.append(name)
            
            # Infer Audience Type
            audience = "大众"
            if any(k in activity_name for k in ["少儿", "儿童", "青少年", "学生", "小小", "家庭"]):
                audience = "少儿/学生"
            elif any(k in activity_name for k in ["学术", "研讨", "论坛", "讲演", "对谈", "对话"]):
                audience = "学术/专业人士"
            elif activity_func == "公教":
                audience = "大众 (互动参与型)"
            elif activity_func == "讲座":
                audience = "学术/爱好者"
                
            results.append({
                "活动名称": activity_name,
                "艺术总监": "; ".join(list(set(art_directors))) if art_directors else "N/A",
                "策展人": "; ".join(list(set(curators))) if curators else "N/A",
                "参与人员": "; ".join(list(set(participants))) if participants else "N/A",
                "观众类型": audience
            })
            
    with open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers_out)
        writer.writeheader()
        writer.writerows(results)
    
    return len(results)

if __name__ == "__main__":
    src = "/Users/zmh/Desktop/合集/维度一：总信息/维度一_全量汇总.csv"
    out = "/Users/zmh/Desktop/合集/维度三：知识图谱/知识图谱_网络关联.csv"
    
    if os.path.exists(src):
        count = extract_kg_dimensions(src, out)
        print(f"Successfully processed {count} records for Knowledge Graph.")
    else:
        print(f"Source CSV not found at {src}")
