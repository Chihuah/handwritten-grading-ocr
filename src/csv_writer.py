"""
CSV 輸出模組
將彙整後的資料輸出為 CSV 檔案
"""
from pathlib import Path
from typing import List, Dict, Optional
import csv
import logging

logger = logging.getLogger(__name__)


class CSVWriter:
    """CSV 檔案寫入器"""
    
    def __init__(self, output_path: str, encoding: str = 'utf-8-sig'):
        """
        初始化 CSV 寫入器
        
        Args:
            output_path: 輸出 CSV 檔案路徑
            encoding: 檔案編碼（預設 utf-8-sig 以支援 Excel）
        """
        self.output_path = Path(output_path)
        self.encoding = encoding
        logger.info(f"初始化 CSV 寫入器: {output_path}")
    
    def write(self, data: List[Dict], 
             score_column_prefix: str = '評分') -> bool:
        """
        寫入 CSV 檔案
        
        Args:
            data: 彙整後的學生資料列表
            score_column_prefix: 評分欄位名稱前綴
            
        Returns:
            是否成功寫入
        """
        if not data:
            logger.warning("資料為空，無法寫入 CSV")
            return False
        
        try:
            # 計算最大評分數（用於決定欄位數）
            max_scores = max(len(student['scores']) for student in data)
            
            # 建立標頭
            headers = ['報告順序', '學號', '姓名']
            headers.extend([f'{score_column_prefix}{i+1}' for i in range(max_scores)])
            
            # 寫入 CSV
            with open(self.output_path, 'w', newline='', encoding=self.encoding) as f:
                writer = csv.writer(f)
                
                # 寫入標頭
                writer.writerow(headers)
                
                # 寫入每位學生的資料
                for student in data:
                    row = [
                        student['order'],
                        student['student_id'],
                        student['name']
                    ]
                    
                    # 加入評分，不足的補空字串
                    scores = student['scores']
                    row.extend([s if s is not None else '' for s in scores])
                    
                    # 如果評分數不足 max_scores，補空字串
                    if len(scores) < max_scores:
                        row.extend([''] * (max_scores - len(scores)))
                    
                    writer.writerow(row)
            
            file_size = self.output_path.stat().st_size
            logger.info(f"✓ 成功寫入 CSV: {self.output_path.name} ({file_size} bytes)")
            logger.info(f"  學生數: {len(data)}, 評分欄位數: {max_scores}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 寫入 CSV 失敗: {e}")
            return False
    
    def get_file_info(self) -> Optional[Dict]:
        """
        取得輸出檔案資訊
        
        Returns:
            檔案資訊字典，若檔案不存在則返回 None
        """
        if not self.output_path.exists():
            return None
        
        stat = self.output_path.stat()
        return {
            'path': str(self.output_path.absolute()),
            'size': stat.st_size,
            'exists': True
        }


def write_csv(data: List[Dict], 
             output_path: str,
             encoding: str = 'utf-8-sig',
             score_column_prefix: str = '評分') -> bool:
    """
    便利函式：寫入 CSV 檔案
    
    Args:
        data: 彙整後的學生資料列表
        output_path: 輸出 CSV 檔案路徑
        encoding: 檔案編碼
        score_column_prefix: 評分欄位名稱前綴
        
    Returns:
        是否成功寫入
    """
    writer = CSVWriter(output_path, encoding=encoding)
    return writer.write(data, score_column_prefix=score_column_prefix)


if __name__ == "__main__":
    # 測試用
    import json
    from pathlib import Path
    logging.basicConfig(level=logging.INFO)
    
    # 讀取測試資料
    test_file = Path("test_ocr_results.json")
    if test_file.exists():
        # 使用 data_aggregator 彙整資料
        from data_aggregator import aggregate_ocr_results
        
        with open(test_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        aggregator = aggregate_ocr_results(results)
        data = aggregator.get_aggregated_data()
        
        # 寫入 CSV
        output_file = "test_output.csv"
        success = write_csv(data, output_file)
        
        if success:
            print(f"\n✓ 測試成功! 請檢查: {output_file}")
            
            # 顯示檔案資訊
            writer = CSVWriter(output_file)
            info = writer.get_file_info()
            if info:
                print(f"  路徑: {info['path']}")
                print(f"  大小: {info['size']} bytes")
