"""
計算最終成績腳本
讀取評分 CSV 檔，計算去除前後 10% 極端值後的平均分數，
再乘以 10 並四捨五入得到最終成績
"""
import argparse
import csv
from pathlib import Path


def calculate_trimmed_mean(scores: list[float], trim_percent: float = 0.10) -> float:
    """
    計算去除前後極端值的平均分數
    
    Args:
        scores: 分數列表
        trim_percent: 要去除的比例（預設 10%）
        
    Returns:
        去除極端值後的平均分數
    """
    if not scores:
        return 0.0
    
    # 排序分數
    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    
    # 計算要去除的數量（前後各 10%）
    trim_count = int(n * trim_percent)
    
    # 去除前後極端值
    if trim_count > 0:
        trimmed_scores = sorted_scores[trim_count:-trim_count]
    else:
        trimmed_scores = sorted_scores
    
    # 計算平均
    if not trimmed_scores:
        # 如果去除後沒有分數，使用原始分數
        trimmed_scores = sorted_scores
    
    return sum(trimmed_scores) / len(trimmed_scores)


def process_csv(input_path: Path, output_path: Path, verbose: bool = False):
    """
    處理 CSV 檔案，計算每位學生的最終成績
    
    Args:
        input_path: 輸入 CSV 檔案路徑
        output_path: 輸出 CSV 檔案路徑
        verbose: 是否輸出詳細資訊
    """
    results = []
    
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # 跳過標題行
        
        for row in reader:
            if not row or not row[0]:  # 跳過空行
                continue
            
            order = int(row[0])  # 報告順序
            
            # 收集所有有效的評分（從第4欄開始，索引為3）
            scores = []
            for i in range(3, len(row)):
                if row[i] and row[i].strip():
                    try:
                        score = float(row[i])
                        scores.append(score)
                    except ValueError:
                        continue
            
            # 計算去除極端值的平均分數
            trimmed_mean = calculate_trimmed_mean(scores)
            
            # 乘以 10 並四捨五入
            final_score = round(trimmed_mean * 10)
            
            results.append({
                'order': order,
                'score_count': len(scores),
                'trimmed_mean': trimmed_mean,
                'final_score': final_score
            })
            
            if verbose:
                trim_count = int(len(scores) * 0.10)
                print(f"順序 {order:2d}: {len(scores)} 份評分, "
                      f"去除前後各 {trim_count} 份, "
                      f"平均 {trimmed_mean:.2f}, "
                      f"最終成績 {final_score}")
    
    # 依順序排序
    results.sort(key=lambda x: x['order'])
    
    # 輸出 CSV
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['順序', '成績'])
        for r in results:
            writer.writerow([r['order'], r['final_score']])
    
    print(f"\n處理完成！")
    print(f"  學生數: {len(results)}")
    print(f"  輸出檔案: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='計算最終成績 - 去除前後 10% 極端值後平均，再乘以 10 並四捨五入',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例用法:
  python calculate_final_scores.py -i scoresI.csv -o final_scoresI.csv
  python calculate_final_scores.py -i scoresII.csv -o final_scoresII.csv -v
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='輸入 CSV 檔案路徑（評分資料）'
    )
    
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='輸出 CSV 檔案路徑（最終成績）'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='顯示詳細處理過程'
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        print(f"錯誤：找不到輸入檔案: {input_path}")
        return 1
    
    print(f"計算最終成績")
    print(f"  輸入: {input_path}")
    print(f"  輸出: {output_path}")
    print(f"  演算法: 去除前後各 10% 分數，取平均後乘以 10，四捨五入")
    print()
    
    process_csv(input_path, output_path, args.verbose)
    
    return 0


if __name__ == "__main__":
    exit(main())
