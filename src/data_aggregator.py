"""
資料彙整模組
將多份評分表的資料進行轉置與彙整
從「評分表視角」轉為「學生視角」
"""
from typing import Dict, List
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class DataAggregator:
    """資料彙整器"""
    
    def __init__(self, master_list: Dict = None):
        """
        初始化資料彙整器
        
        Args:
            master_list: 原始學生名單（來自原始評分表）
                        格式: {"students": [{"order": int, "student_id": str, "name": str}]}
        """
        self.student_scores = defaultdict(lambda: {
            'order': None,
            'name': None,
            'scores': []
        })
        self.processed_files = []
        self.has_master_list = False
        
        # 如果提供原始學生名單，先初始化
        if master_list:
            self._load_master_list(master_list)
        
        logger.info(f"初始化資料彙整器 (master_list: {self.has_master_list})")
    
    def _load_master_list(self, master_list: Dict):
        """
        載入原始學生名單
        
        Args:
            master_list: 原始學生名單
        """
        students = master_list.get('students', [])
        logger.info(f"載入原始學生名單: {len(students)} 位學生")
        
        for student in students:
            student_id = student['student_id']
            self.student_scores[student_id]['order'] = student['order']
            self.student_scores[student_id]['name'] = student['name']
            # scores 保持為空列表，等待加入評分
        
        self.has_master_list = True
        logger.info(f"✓ 已載入 {len(students)} 位學生的主檔資料")
    
    def add_ocr_result(self, ocr_result: Dict, scores_only: bool = None) -> bool:
        """
        加入一份評分表的 OCR 結果
        
        Args:
            ocr_result: OCR 辨識結果字典
            scores_only: 是否只提取評分（忽略學號姓名資訊）。
                        若為 None，則根據是否有主檔自動決定
            
        Returns:
            是否成功加入
        """
        if not ocr_result.get('success', False):
            logger.warning(f"跳過失敗的辨識結果: {ocr_result.get('file_name', 'unknown')}")
            return False
        
        file_name = ocr_result['file_name']
        data = ocr_result['data']
        
        # 自動決定是否只提取評分
        if scores_only is None:
            scores_only = self.has_master_list
        
        logger.info(f"加入評分表: {file_name} (學生數: {data.get('total_students', 'N/A')}, scores_only: {scores_only})")
        
        # 處理每位學生的評分
        matched_count = 0
        unmatched_count = 0
        
        for score_data in data.get('scores', []):
            # 檢查是否為隱私模式輸出（只有 order 和 score，沒有 student_id）
            student_id = score_data.get('student_id')
            order = score_data.get('order')
            
            if student_id is None and order is not None:
                # 隱私模式：使用 order 作為 key
                key = f"order_{order}"
                
                if self.student_scores[key]['order'] is None:
                    self.student_scores[key]['order'] = order
                    self.student_scores[key]['name'] = None  # 隱私模式無姓名
                
                self.student_scores[key]['scores'].append(score_data.get('score'))
                matched_count += 1
                
            elif scores_only and self.has_master_list:
                # 有主檔且只提取評分：檢查學生是否在主檔中
                if student_id in self.student_scores:
                    self.student_scores[student_id]['scores'].append(score_data.get('score'))
                    matched_count += 1
                else:
                    logger.warning(f"學號 {student_id} 不在主檔中，跳過")
                    unmatched_count += 1
            else:
                # 傳統模式：第一次遇到該學生時記錄基本資訊
                if self.student_scores[student_id]['order'] is None:
                    self.student_scores[student_id]['order'] = order
                    self.student_scores[student_id]['name'] = score_data.get('name')
                    logger.debug(f"新增學生: {student_id} - {score_data.get('name')}")
                
                # 加入評分
                self.student_scores[student_id]['scores'].append(score_data.get('score'))
                matched_count += 1
        
        if unmatched_count > 0:
            logger.warning(f"  {unmatched_count} 位學生未在主檔中")
        logger.info(f"  成功配對 {matched_count} 位學生的評分")
        
        self.processed_files.append(file_name)
        return True
    
    def batch_add_results(self, ocr_results: List[Dict]) -> int:
        """
        批次加入多份評分表的 OCR 結果
        
        Args:
            ocr_results: OCR 辨識結果列表
            
        Returns:
            成功加入的檔案數量
        """
        logger.info(f"批次加入 {len(ocr_results)} 份評分表")
        
        success_count = 0
        for result in ocr_results:
            if self.add_ocr_result(result):
                success_count += 1
        
        logger.info(f"成功加入 {success_count}/{len(ocr_results)} 份評分表")
        return success_count
    
    def get_aggregated_data(self, sort_by_order: bool = True) -> List[Dict]:
        """
        取得彙整後的資料
        
        Args:
            sort_by_order: 是否依報告順序排序
            
        Returns:
            彙整後的學生資料列表
            [
                {
                    'student_id': str,
                    'order': int,
                    'name': str,
                    'scores': List[Optional[int]]
                },
                ...
            ]
        """
        # 轉換為列表格式
        data = []
        for student_id, info in self.student_scores.items():
            data.append({
                'student_id': student_id,
                'order': info['order'],
                'name': info['name'],
                'scores': info['scores']
            })
        
        # 排序
        if sort_by_order:
            data.sort(key=lambda x: x['order'])
        
        logger.info(f"取得彙整資料: {len(data)} 位學生")
        return data
    
    def get_statistics(self) -> Dict:
        """
        取得統計資訊
        
        Returns:
            統計資訊字典
        """
        total_students = len(self.student_scores)
        total_files = len(self.processed_files)
        
        if total_students == 0:
            return {
                'total_students': 0,
                'total_files': 0,
                'avg_scores_per_student': 0,
                'students_with_all_scores': 0
            }
        
        # 計算每位學生的平均評分數
        score_counts = [len(info['scores']) for info in self.student_scores.values()]
        avg_scores = sum(score_counts) / len(score_counts)
        
        # 計算有完整評分的學生數（評分數 == 檔案數）
        students_with_all = sum(1 for count in score_counts if count == total_files)
        
        stats = {
            'total_students': total_students,
            'total_files': total_files,
            'avg_scores_per_student': round(avg_scores, 2),
            'students_with_all_scores': students_with_all,
            'processed_files': self.processed_files
        }
        
        logger.info(f"統計: {total_students} 位學生, {total_files} 份評分表")
        return stats
    
    def clear(self):
        """清空所有資料"""
        self.student_scores.clear()
        self.processed_files.clear()
        logger.info("已清空所有資料")


def aggregate_ocr_results(ocr_results: List[Dict], master_list: Dict = None) -> DataAggregator:
    """
    便利函式：彙整 OCR 結果
    
    Args:
        ocr_results: OCR 辨識結果列表
        master_list: 原始學生名單（可選）
        
    Returns:
        已彙整資料的 DataAggregator 物件
    """
    aggregator = DataAggregator(master_list=master_list)
    aggregator.batch_add_results(ocr_results)
    return aggregator


if __name__ == "__main__":
    # 測試用
    import json
    from pathlib import Path
    logging.basicConfig(level=logging.INFO)
    
    # 讀取測試資料
    test_file = Path("test_ocr_results.json")
    if test_file.exists():
        with open(test_file, 'r', encoding='utf-8') as f:
            results =json.load(f)
        
        # 彙整資料
        aggregator = aggregate_ocr_results(results)
        
        # 顯示統計
        stats = aggregator.get_statistics()
        print(f"\n統計資訊:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # 顯示前5位學生
        data = aggregator.get_aggregated_data()
        print(f"\n前5位學生:")
        for student in data[:5]:
            scores_str = ','.join(str(s) if s is not None else '' for s in student['scores'])
            print(f"  {student['order']},{student['student_id']},{student['name']},{scores_str}")
