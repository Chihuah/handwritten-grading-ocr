"""
隱私安全的 OCR 提取器
將 PDF 轉換為圖片並套用隱私遮罩後，使用 Gemini API 提取評分
只輸出順序編號和評分，不包含任何個人資料
"""
import logging
import base64
import json
import io
from pathlib import Path
from typing import Dict, List, Optional
from google import genai
from PIL import Image

from mask_processor import MaskProcessor

logger = logging.getLogger(__name__)


class PrivacyOCRExtractor:
    """隱私安全的 OCR 提取器"""
    
    # 專用於遮罩圖片的提示詞（只提取序號和評分）
    MASKED_OCR_PROMPT = """You are an OCR assistant. This is a grading sheet with personal information masked (shown as white rectangles).

Please extract only the visible information from the table:
- order: the sequence number (序) on the left side of each row
- score: the handwritten score (評分) on the right side of each row, should be 1-10

The sheet has two columns of students. The left column typically has students 1-18, and the right column has students 19 and beyond (could be up to 36, 37, or more depending on the class size).

Return the data as JSON:
{
  "total_students": <actual count>,
  "scores": [
    {"order": 1, "score": 6},
    {"order": 2, "score": 7},
    ...
  ]
}

IMPORTANT:
- Only extract the ORDER NUMBER and SCORE
- The middle columns are intentionally masked and should be ignored
- If a score is unclear, use null
- Count ALL students visible in the table, including any beyond row 36
- Output ONLY valid JSON, no explanations"""
    
    def __init__(self, api_key: str = None, model: str = "gemini-3-flash-preview"):
        """
        初始化隱私安全的 OCR 提取器
        
        Args:
            api_key: Gemini API key（可選，會從環境變數讀取）
            model: Gemini 模型名稱
        """
        import os
        
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("需要提供 GEMINI_API_KEY")
        
        self.model = model
        self.client = genai.Client(api_key=self.api_key)
        self.mask_processor = MaskProcessor(dpi=300)
        
        logger.info(f"初始化隱私安全 OCR 提取器 (模型: {model})")
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """將 PIL Image 轉換為 base64"""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return base64.standard_b64encode(buffer.getvalue()).decode('utf-8')
    
    def _parse_json_response(self, text: str) -> Optional[Dict]:
        """解析 JSON 回應"""
        # 清理回應
        clean_text = text.strip()
        
        # 移除 markdown 程式碼區塊
        if '```json' in clean_text:
            clean_text = clean_text.split('```json')[1].split('```')[0].strip()
        elif '```' in clean_text:
            clean_text = clean_text.split('```')[1].split('```')[0].strip()
        
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失敗: {e}")
            return None
    
    def extract_from_pdf(self, pdf_path: Path, 
                        save_masked_image: bool = True,
                        masked_output_dir: Path = None) -> Dict:
        """
        從 PDF 提取評分（使用隱私遮罩）
        
        Args:
            pdf_path: PDF 檔案路徑
            save_masked_image: 是否儲存遮罩後的圖片
            masked_output_dir: 遮罩圖片儲存目錄
            
        Returns:
            包含評分資料的字典
        """
        logger.info(f"處理 PDF（隱私模式）: {pdf_path.name}")
        
        try:
            # 1. PDF 轉圖片並套用遮罩
            masked_image, _ = self.mask_processor.process_pdf(
                pdf_path, 
                save_masked=False
            )
            
            # 儲存遮罩後的圖片
            if save_masked_image:
                if masked_output_dir is None:
                    masked_output_dir = Path("masked_images")
                masked_output_dir.mkdir(exist_ok=True)
                
                output_path = masked_output_dir / f"{pdf_path.stem}.masked.png"
                masked_image.save(output_path)
                logger.info(f"遮罩圖片已儲存: {output_path}")
            
            # 2. 上傳圖片到 Gemini
            img_bytes = self.mask_processor.image_to_bytes(masked_image)
            
            # 使用 inline data 方式傳送圖片
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    {
                        "parts": [
                            {"text": self.MASKED_OCR_PROMPT},
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": base64.standard_b64encode(img_bytes).decode('utf-8')
                                }
                            }
                        ]
                    }
                ]
            )
            
            # 3. 解析回應
            result_text = response.text
            data = self._parse_json_response(result_text)
            
            if data:
                logger.info(f"成功提取 {len(data.get('scores', []))} 筆評分")
                return {
                    'success': True,
                    'file_name': pdf_path.name,
                    'data': data
                }
            else:
                return {
                    'success': False,
                    'file_name': pdf_path.name,
                    'error': '無法解析 JSON 回應',
                    'raw_response': result_text
                }
                
        except Exception as e:
            logger.error(f"處理 {pdf_path.name} 時發生錯誤: {e}")
            return {
                'success': False,
                'file_name': pdf_path.name,
                'error': str(e)
            }
    
    def batch_extract(self, pdf_files: List[Path],
                     masked_output_dir: Path = None) -> List[Dict]:
        """
        批次處理多個 PDF 檔案
        
        Args:
            pdf_files: PDF 檔案列表
            masked_output_dir: 遮罩圖片儲存目錄
            
        Returns:
            處理結果列表
        """
        logger.info(f"批次處理 {len(pdf_files)} 個 PDF 檔案（隱私模式）")
        
        results = []
        for i, pdf_path in enumerate(pdf_files, 1):
            logger.info(f"[{i}/{len(pdf_files)}] 處理: {pdf_path.name}")
            result = self.extract_from_pdf(pdf_path, masked_output_dir=masked_output_dir)
            results.append(result)
        
        success_count = sum(1 for r in results if r.get('success'))
        logger.info(f"批次處理完成: {success_count}/{len(pdf_files)} 成功")
        
        return results


if __name__ == "__main__":
    import os
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    # 測試單一檔案
    pdf_path = Path("examples/期中報告I_30-1-1.pdf")
    
    if not pdf_path.exists():
        print(f"✗ 檔案不存在: {pdf_path}")
        sys.exit(1)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("✗ 請設定 GEMINI_API_KEY 環境變數")
        sys.exit(1)
    
    print("="*60)
    print("隱私安全 OCR 提取器測試")
    print("="*60)
    
    extractor = PrivacyOCRExtractor(api_key=api_key)
    result = extractor.extract_from_pdf(pdf_path)
    
    print("\n" + "="*60)
    print("測試結果:")
    print("="*60)
    
    if result['success']:
        data = result['data']
        print(f"✓ 成功!")
        print(f"  學生總數: {data.get('total_students', 'N/A')}")
        print(f"  評分記錄數: {len(data.get('scores', []))}")
        
        print("\n評分資料（前10筆）:")
        for score in data.get('scores', [])[:10]:
            print(f"  序號 {score.get('order')}: {score.get('score')} 分")
    else:
        print(f"✗ 失敗: {result.get('error')}")
