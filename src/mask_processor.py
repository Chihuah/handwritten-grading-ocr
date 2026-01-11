"""
隱私遮罩處理模組
將 PDF 轉換為圖片後，對學號和姓名區域套用遮罩，保護個人資料
"""
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import io

logger = logging.getLogger(__name__)


class MaskProcessor:
    """隱私遮罩處理器"""
    
    # 預定義遮罩區域（基於 300 DPI 轉換的圖片，尺寸約 2484 x 3475）
    # 格式: (x1, y1, x2, y2) - 左上角到右下角
    # 這些區域覆蓋「學號」和「姓名」欄位
    # 圖片結構：左邊學生1-18，右邊學生19-36
    
    DEFAULT_MASKS = {
        'dpi': 300,
        'expected_width': 2484,
        'expected_height': 3475,
        'masks': [
            # 左邊表格的學號和姓名區域 (學生 1-18)
            {
                'name': 'left_student_info',
                'x1': 339,
                'y1': 394,
                'x2': 835,
                'y2': 1946,
            },
            # 右邊表格的學號和姓名區域 (學生 19-37)
            {
                'name': 'right_student_info',
                'x1': 1319,
                'y1': 404,
                'x2': 1808,
                'y2': 2067,
            },
            # 底部評分參考區域 (避免干擾 OCR)
            {
                'name': 'rubric_section',
                'x1': 147,
                'y1': 2085,
                'x2': 2008,
                'y2': 3147,
            },
        ],
        'mask_color': (255, 255, 255)  # 白色遮罩
    }
    
    def __init__(self, mask_config: Dict = None, dpi: int = 300):
        """
        初始化遮罩處理器
        
        Args:
            mask_config: 自訂遮罩配置（可選）
            dpi: PDF 轉圖片的 DPI（預設 300）
        """
        self.dpi = dpi
        self.mask_config = mask_config or self.DEFAULT_MASKS
        logger.info(f"初始化遮罩處理器 (DPI: {dpi})")
    
    def pdf_to_image(self, pdf_path: Path) -> Image.Image:
        """
        將 PDF 轉換為 PIL Image
        
        Args:
            pdf_path: PDF 檔案路徑
            
        Returns:
            PIL Image 物件
        """
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        
        zoom = self.dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # 轉換為 PIL Image
        img_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_bytes))
        
        doc.close()
        logger.debug(f"PDF 轉圖片: {pdf_path.name} -> {image.size}")
        
        return image
    
    def apply_mask(self, image: Image.Image, save_debug: bool = False,
                  debug_path: Path = None) -> Image.Image:
        """
        對圖片套用隱私遮罩
        
        Args:
            image: 原始圖片
            save_debug: 是否儲存調試圖片
            debug_path: 調試圖片儲存路徑
            
        Returns:
            套用遮罩後的圖片
        """
        # 複製圖片以避免修改原始圖片
        masked_image = image.copy()
        draw = ImageDraw.Draw(masked_image)
        
        # 取得圖片尺寸
        width, height = image.size
        
        # 計算縮放比例（如果圖片尺寸不同於預期）
        expected_w = self.mask_config['expected_width']
        expected_h = self.mask_config['expected_height']
        scale_x = width / expected_w
        scale_y = height / expected_h
        
        logger.debug(f"圖片尺寸: {width}x{height}, 縮放比例: ({scale_x:.2f}, {scale_y:.2f})")
        
        # 套用每個遮罩區域
        mask_color = self.mask_config['mask_color']
        for mask in self.mask_config['masks']:
            # 根據縮放比例調整座標
            x1 = int(mask['x1'] * scale_x)
            y1 = int(mask['y1'] * scale_y)
            x2 = int(mask['x2'] * scale_x)
            y2 = int(mask['y2'] * scale_y)
            
            # 繪製白色矩形
            draw.rectangle([x1, y1, x2, y2], fill=mask_color)
            logger.debug(f"套用遮罩 '{mask['name']}': ({x1}, {y1}) -> ({x2}, {y2})")
        
        # 儲存調試圖片
        if save_debug and debug_path:
            masked_image.save(debug_path)
            logger.info(f"調試圖片已儲存: {debug_path}")
        
        return masked_image
    
    def process_pdf(self, pdf_path: Path, output_path: Path = None,
                   save_masked: bool = True) -> Tuple[Image.Image, Optional[Path]]:
        """
        處理單個 PDF 檔案：轉換並套用遮罩
        
        Args:
            pdf_path: PDF 檔案路徑
            output_path: 輸出圖片路徑（可選）
            save_masked: 是否儲存遮罩後的圖片
            
        Returns:
            (遮罩後的圖片, 儲存路徑)
        """
        logger.info(f"處理 PDF: {pdf_path.name}")
        
        # PDF 轉圖片
        image = self.pdf_to_image(pdf_path)
        
        # 套用遮罩
        masked_image = self.apply_mask(image)
        
        # 儲存結果
        saved_path = None
        if save_masked:
            if output_path is None:
                output_path = pdf_path.with_suffix('.masked.png')
            masked_image.save(output_path)
            saved_path = output_path
            logger.info(f"遮罩圖片已儲存: {output_path}")
        
        return masked_image, saved_path
    
    def batch_process(self, pdf_files: List[Path], 
                     output_dir: Path = None) -> List[Dict]:
        """
        批次處理多個 PDF 檔案
        
        Args:
            pdf_files: PDF 檔案列表
            output_dir: 輸出目錄
            
        Returns:
            處理結果列表
        """
        logger.info(f"批次處理 {len(pdf_files)} 個 PDF 檔案")
        
        results = []
        for pdf_path in pdf_files:
            try:
                if output_dir:
                    output_path = output_dir / f"{pdf_path.stem}.masked.png"
                else:
                    output_path = pdf_path.with_suffix('.masked.png')
                
                image, saved_path = self.process_pdf(pdf_path, output_path)
                
                results.append({
                    'pdf_path': str(pdf_path),
                    'masked_image_path': str(saved_path) if saved_path else None,
                    'image': image,
                    'success': True
                })
            except Exception as e:
                logger.error(f"處理 {pdf_path.name} 時發生錯誤: {e}")
                results.append({
                    'pdf_path': str(pdf_path),
                    'success': False,
                    'error': str(e)
                })
        
        success_count = sum(1 for r in results if r.get('success'))
        logger.info(f"批次處理完成: {success_count}/{len(pdf_files)} 成功")
        
        return results
    
    def image_to_bytes(self, image: Image.Image, format: str = 'PNG') -> bytes:
        """
        將 PIL Image 轉換為 bytes
        
        Args:
            image: PIL Image 物件
            format: 輸出格式
            
        Returns:
            bytes 資料
        """
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()


def create_mask_preview(pdf_path: Path, output_path: Path = None):
    """
    創建遮罩預覽圖（顯示遮罩區域）
    """
    processor = MaskProcessor()
    
    # PDF 轉圖片
    image = processor.pdf_to_image(pdf_path)
    
    # 繪製遮罩區域邊框（用於調試）
    draw = ImageDraw.Draw(image)
    
    width, height = image.size
    expected_w = processor.mask_config['expected_width']
    expected_h = processor.mask_config['expected_height']
    scale_x = width / expected_w
    scale_y = height / expected_h
    
    for mask in processor.mask_config['masks']:
        x1 = int(mask['x1'] * scale_x)
        y1 = int(mask['y1'] * scale_y)
        x2 = int(mask['x2'] * scale_x)
        y2 = int(mask['y2'] * scale_y)
        
        # 繪製紅色邊框
        draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0), width=3)
    
    if output_path is None:
        output_path = Path("mask_preview.png")
    
    image.save(output_path)
    print(f"遮罩預覽圖已儲存: {output_path}")
    return output_path


if __name__ == "__main__":
    # 測試用
    import sys
    logging.basicConfig(level=logging.INFO)
    
    pdf_path = Path("examples/期中報告I_30-1-1.pdf")
    
    if pdf_path.exists():
        # 創建遮罩預覽
        print("創建遮罩預覽圖...")
        preview_path = create_mask_preview(pdf_path)
        
        # 套用遮罩
        print("\n套用遮罩...")
        processor = MaskProcessor()
        masked_img, saved_path = processor.process_pdf(pdf_path)
        print(f"遮罩圖片已儲存: {saved_path}")
    else:
        print(f"檔案不存在: {pdf_path}")
