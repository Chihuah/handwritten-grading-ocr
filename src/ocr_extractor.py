"""
OCR 辨識與數據提取模組
使用 Gemini API 對 PDF 進行 OCR 並提取結構化資料
"""
from pathlib import Path
from typing import Dict, List, Optional
import json
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class OCRExtractor:
    """OCR 辨識提取器"""
    
    # OCR 提示詞
    PROMPT_TEMPLATE = """
請仔細分析這份評分表 PDF，並提取以下資訊：

1. 評分表的結構（有多少位學生需要被評分）
2. 每位學生的資訊，包括：
   - 報告順序（編號）
   - 學號
   - 姓名
   - 手寫評分（1-10分）

請以 JSON 格式輸出，格式如下：
```json
{{
  "total_students": 總學生數,
  "scores": [
    {{
      "order": 報告順序數字,
      "student_id": "學號",
      "name": "姓名",
      "score": 評分數字或null
    }}
  ]
}}
```

注意事項：
- 請特別留意手寫數字的辨識，評分範圍應該在 1-10 之間
- 如果某個評分框是空白或無法辨識，請將 score 設為 null
- 請確保學號和姓名的準確性
- 只輸出 JSON，不要有其他說明文字
- order 和 score 應為數字類型（如果有值的話）
"""
    
    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview"):
        """
        初始化 OCR 提取器
        
        Args:
            api_key: Gemini API Key
            model: 使用的模型名稱
        """
        self.api_key = api_key
        self.model = model
        self.client = genai.Client(api_key=api_key)
        logger.info(f"初始化 OCR 提取器，使用模型: {model}")
    
    def extract_from_pdf(self, pdf_path: Path) -> Dict:
        """
        從 PDF 提取評分資料
        
        Args:
            pdf_path: PDF 檔案路徑
            
        Returns:
            包含提取結果的字典：
            {
                "file_name": str,
                "success": bool,
                "data": dict (如果成功)，
                "error": str (如果失敗)
            }
        """
        logger.info(f"開始處理: {pdf_path.name}")
        
        if not pdf_path.exists():
            error_msg = f"檔案不存在: {pdf_path}"
            logger.error(error_msg)
            return {
                "file_name": pdf_path.name,
                "success": False,
                "error": error_msg
            }
        
        try:
            # 上傳檔案
            logger.debug("上傳檔案到 Gemini API...")
            with open(pdf_path, 'rb') as f:
                uploaded_file = self.client.files.upload(
                    file=f,
                    config={
                        'mime_type': 'application/pdf',
                        'display_name': pdf_path.name
                    }
                )
            logger.debug(f"檔案已上傳: {uploaded_file.uri}")
            
            # 執行 OCR
            logger.debug("執行 OCR 辨識...")
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role='user',
                        parts=[
                            types.Part.from_uri(
                                file_uri=uploaded_file.uri,
                                mime_type='application/pdf'
                            ),
                            types.Part.from_text(text=self.PROMPT_TEMPLATE)
                        ]
                    )
                ]
            )
            
            # 解析結果
            result_text = response.text
            logger.debug(f"收到回應，長度: {len(result_text)} 字元")
            
            # 移除可能的 markdown 代碼塊標記
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()
            
            # 解析 JSON
            try:
                data = json.loads(result_text)
                logger.info(f"✓ 成功辨識 {pdf_path.name}，學生數: {data.get('total_students', 'N/A')}")
                
                # 刪除上傳的檔案
                self.client.files.delete(name=uploaded_file.name)
                
                return {
                    "file_name": pdf_path.name,
                    "success": True,
                    "data": data
                }
                
            except json.JSONDecodeError as e:
                error_msg = f"JSON 解析失敗: {e}"
                logger.error(f"✗ {pdf_path.name} - {error_msg}")
                logger.debug(f"原始回應: {result_text[:200]}...")
                
                return {
                    "file_name": pdf_path.name,
                    "success": False,
                    "error": error_msg,
                    "raw_response": result_text
                }
                
        except Exception as e:
            error_msg = f"處理檔案時發生異常: {e}"
            logger.error(f"✗ {pdf_path.name} - {error_msg}")
            return {
                "file_name": pdf_path.name,
                "success": False,
                "error": error_msg
            }
    
    def batch_extract(self, pdf_files: List[Path], 
                     save_results: bool = True,
                     output_path: Optional[Path] = None) -> List[Dict]:
        """
        批次處理多個 PDF 檔案
        
        Args:
            pdf_files: PDF 檔案路徑列表
            save_results: 是否儲存結果到 JSON 檔案
            output_path: 輸出 JSON 檔案路徑（預設為 ocr_results.json）
            
        Returns:
            提取結果列表
        """
        logger.info(f"開始批次處理 {len(pdf_files)} 個檔案")
        
        results = []
        for i, pdf_path in enumerate(pdf_files, 1):
            logger.info(f"[{i}/{len(pdf_files)}] 處理: {pdf_path.name}")
            result = self.extract_from_pdf(pdf_path)
            results.append(result)
        
        # 統計
        success_count = sum(1 for r in results if r.get('success', False))
        logger.info(f"\n批次處理完成: {success_count}/{len(pdf_files)} 成功")
        
        # 儲存結果
        if save_results:
            if output_path is None:
                output_path = Path("ocr_results.json")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"結果已儲存至: {output_path}")
        
        return results


if __name__ == "__main__":
    # 測試用
    import sys
    import os
    logging.basicConfig(level=logging.INFO)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("錯誤：未設置 GEMINI_API_KEY 環境變數")
        sys.exit(1)
    
    # 測試單一檔案
    test_file = Path("examples/期中報告I_30-1-1.pdf")
    if test_file.exists():
        extractor = OCRExtractor(api_key)
        result = extractor.extract_from_pdf(test_file)
        print(f"\n測試結果:")
        print(f"成功: {result['success']}")
        if result['success']:
            print(f"學生數: {result['data']['total_students']}")
