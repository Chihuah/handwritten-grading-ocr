"""
演示資料轉置邏輯
將 OCR 結果從「評分表視角」轉為「學生視角」
"""
import json
from pathlib import Path
from collections import defaultdict

# 讀取測試結果
with open('test_ocr_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

# 資料彙整：以學號為主鍵
student_scores = defaultdict(lambda: {'order': None, 'name': None, 'scores': []})

# 處理每份評分表
for result in results:
    if not result.get('success'):
        print(f"跳過失敗的檔案: {result['file_name']}")
        continue
    
    file_name = result['file_name']
    data = result['data']
    
    print(f"\n處理: {file_name}")
    print(f"學生數: {data['total_students']}")
    
    # 處理每位學生的評分
    for score_data in data['scores']:
        student_id = score_data['student_id']
        
        # 第一次遇到該學生，記錄基本資訊
        if student_scores[student_id]['order'] is None:
            student_scores[student_id]['order'] = score_data['order']
            student_scores[student_id]['name'] = score_data['name']
        
        # append 評分
        student_scores[student_id]['scores'].append(score_data['score'])

# 輸出結果
print(f"\n{'='*60}")
print("資料轉置結果")
print(f"{'='*60}")
print(f"總學生數: {len(student_scores)}")

# 按報告順序排序
sorted_students = sorted(student_scores.items(), key=lambda x: x[1]['order'])

# 顯示前5位學生的資料
print("\n前5位學生的評分記錄：")
for i, (student_id, info) in enumerate(sorted_students[:5], 1):
    scores_str = ','.join(str(s) for s in info['scores'])
    print(f"{i}. {info['order']},{student_id},{info['name']},{scores_str}")

# 生成 CSV
output_file = Path('demo_output.csv')
with open(output_file, 'w', encoding='utf-8-sig') as f:
    # 寫入標頭
    max_scores = max(len(info['scores']) for info in student_scores.values())
    header_cols = ['報告順序', '學號', '姓名'] + [f'評分{i+1}' for i in range(max_scores)]
    f.write(','.join(header_cols) + '\n')
    
    # 寫入每位學生的資料
    for student_id, info in sorted_students:
        scores_str = ','.join(str(s) if s is not None else '' for s in info['scores'])
        row = f"{info['order']},{student_id},{info['name']},{scores_str}\n"
        f.write(row)

print(f"\n完整 CSV 已輸出至: {output_file}")
print(f"檔案大小: {output_file.stat().st_size} bytes")
