"""
PDF 批次處理模組
掃描指定資料夾，取得所有 PDF 檔案清單
"""
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF 檔案批次處理器"""
    
    def __init__(self, input_dir: str):
        """
        初始化 PDF 處理器
        
        Args:
            input_dir: 包含 PDF 檔案的資料夾路徑
        """
        self.input_dir = Path(input_dir)
        if not self.input_dir.exists():
            raise FileNotFoundError(f"找不到資料夾: {input_dir}")
        if not self.input_dir.is_dir():
            raise NotADirectoryError(f"路徑不是資料夾: {input_dir}")
    
    def get_pdf_files(self, recursive: bool = False) -> List[Path]:
        """
        取得資料夾中的所有 PDF 檔案
        
        Args:
            recursive: 是否遞迴搜尋子資料夾
            
        Returns:
            PDF 檔案路徑列表，按檔名排序
        """
        pattern = "**/*.pdf" if recursive else "*.pdf"
        pdf_files = list(self.input_dir.glob(pattern))
        
        # 過濾掉非檔案（例如符號連結）
        pdf_files = [f for f in pdf_files if f.is_file()]
        
        # 按檔名排序
        pdf_files.sort(key=lambda x: x.name)
        
        logger.info(f"在 {self.input_dir} 找到 {len(pdf_files)} 個 PDF 檔案")
        
        return pdf_files
    
    def validate_files(self, files: List[Path]) -> List[Path]:
        """
        驗證 PDF 檔案是否可讀取
        
        Args:
            files: PDF 檔案路徑列表
            
        Returns:
            驗證通過的檔案列表
        """
        valid_files = []
        for file_path in files:
            try:
                # 檢查檔案大小
                file_size = file_path.stat().st_size
                if file_size == 0:
                    logger.warning(f"檔案大小為 0: {file_path.name}")
                    continue
                
                # 檢查是否可讀取
                with open(file_path, 'rb') as f:
                    # 讀取前4個 bytes 檢查 PDF 標頭
                    header = f.read(4)
                    if header != b'%PDF':
                        logger.warning(f"不是有效的 PDF 檔案: {file_path.name}")
                        continue
                
                valid_files.append(file_path)
                logger.debug(f"驗證通過: {file_path.name} ({file_size} bytes)")
                
            except Exception as e:
                logger.error(f"驗證檔案時發生錯誤 {file_path.name}: {e}")
                continue
        
        logger.info(f"驗證完成: {len(valid_files)}/{len(files)} 個檔案有效")
        return valid_files


def get_pdf_list(input_dir: str, recursive: bool = False, validate: bool = True) -> List[Path]:
    """
    便利函式：取得並驗證 PDF 檔案列表
    
    Args:
        input_dir: 包含 PDF 檔案的資料夾路徑
        recursive: 是否遞迴搜尋子資料夾
        validate: 是否驗證檔案
        
    Returns:
        PDF 檔案路徑列表
    """
    processor = PDFProcessor(input_dir)
    pdf_files = processor.get_pdf_files(recursive=recursive)
    
    if validate:
        pdf_files = processor.validate_files(pdf_files)
    
    return pdf_files


if __name__ == "__main__":
    # 測試用
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        test_dir = sys.argv[1]
    else:
        test_dir = "examples"
    
    print(f"測試資料夾: {test_dir}")
    files = get_pdf_list(test_dir)
    
    print(f"\n找到 {len(files)} 個 PDF 檔案:")
    for i, f in enumerate(files, 1):
        print(f"{i}. {f.name} ({f.stat().st_size} bytes)")
