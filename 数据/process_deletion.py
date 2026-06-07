import csv
import os
import re

csv_path = '/Users/zmh/Desktop/合集/维度一：总信息/维度一_全量汇总.csv'
md_dir = '/Users/zmh/Desktop/合集/维度一：总信息/精修整合版'
keywords = ['预告', '即将', '开幕在即','抢先看', '明日首映', '即将开展', '即将亮相']

deleted_report = []

def should_delete(title):
    return any(kw in title for kw in keywords)

# Process CSV
if os.path.exists(csv_path):
    print(f"Processing CSV: {csv_path}")
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    new_rows = []
    for row in rows:
        title = row.get('活动名称', '')
        if should_delete(title):
            deleted_report.append(f"CSV | {row['ID']} | {title}")
        else:
            new_rows.append(row)
    
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_rows)
    print(f"CSV processed. Deleted {len(rows) - len(new_rows)} rows.")

# Process MD files
for i in range(1, 11):
    md_path = os.path.join(md_dir, f'维度一_合并_{i}.md')
    if os.path.exists(md_path):
        print(f"Processing MD: {md_path}")
        with open(md_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if len(lines) < 2:
            continue
            
        header = lines[0]
        separator = lines[1]
        data_lines = lines[2:]
        
        new_data_lines = []
        for line in data_lines:
            if not line.strip():
                continue
            # MD table row format: | ID | Time | Title | ... |
            parts = [p.strip() for p in line.split('|')]
            if len(parts) > 3:
                id_val = parts[1]
                title = parts[3]
                if should_delete(title):
                    deleted_report.append(f"MD_{i} | {id_val} | {title}")
                else:
                    new_data_lines.append(line)
            else:
                new_data_lines.append(line)
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(header)
            f.write(separator)
            f.writelines(new_data_lines)
        print(f"MD {i} processed. Deleted {len(data_lines) - len(new_data_lines)} rows.")

# Write report
report_path = '/Users/zmh/Desktop/合集/已删除预告信息汇总.txt'
with open(report_path, 'w', encoding='utf-8') as f:
    f.write("已删除的展览/活动预告信息汇总：\n")
    f.write("-" * 50 + "\n")
    f.write("来源 | ID | 活动名称\n")
    f.write("-" * 50 + "\n")
    for item in deleted_report:
        f.write(item + "\n")

print(f"Report generated at: {report_path}")
