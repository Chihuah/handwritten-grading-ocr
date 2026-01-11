"""
OCR 評分表辨識工具 - 主程式
整合所有模組，提供命令列介面
"""
import argparse
import logging
import os
import sys
from pathlib import Path

# 加入 src 目錄到路徑
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from pdf_processor import get_pdf_list
from data_aggregator import DataAggregator
from csv_writer import write_csv
from privacy_ocr_extractor import PrivacyOCRExtractor


def setup_logging(verbose: bool = False):
    """設置日誌"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description='OCR 評分表辨識工具 - 自動辨識手寫評分並輸出 CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例用法:
  # 隱私模式（建議）- 遮蓋個資後才上傳 Gemini
  python main.py --input examples --output scores.csv --privacy-mode
  
  # 完整模式 - 上傳完整圖片（包含個資）
  python main.py --input examples --output scores.csv
  
  # 啟用詳細日誌
  python main.py --input examples --output scores.csv --privacy-mode --verbose
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='包含評分表 PDF 的資料夾路徑'
    )
    
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='輸出 CSV 檔案路徑'
    )
    

    
    parser.add_argument(
        '--api-key', '-k',
        default=None,
        help='Gemini API Key（若未指定則使用環境變數 GEMINI_API_KEY）'
    )
    
    parser.add_argument(
        '--model', '-m',
        default='gemini-3-flash-preview',
        help='使用的 Gemini 模型（預設: gemini-3-flash-preview）'
    )
    
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='遞迴搜尋子資料夾中的 PDF'
    )
    
    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='不驗證 PDF 檔案'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='啟用詳細日誌'
    )
    
    parser.add_argument(
        '--save-ocr-results',
        action='store_true',
        help='儲存 OCR 原始結果到 JSON 檔案'
    )
    
    parser.add_argument(
        '--privacy-mode', '-p',
        action='store_true',
        help='隱私模式：遮蓋學號姓名後才上傳到 Gemini（建議啟用）'
    )
    
    parser.add_argument(
        '--masked-output-dir',
        default='masked_images',
        help='隱私模式下遮罩圖片的儲存目錄（預設: masked_images）'
    )
    
    args = parser.parse_args()
    
    # 設置日誌
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("OCR 評分表辨識工具")
    logger.info("="*60)
    
    # 取得 API Key
    api_key = args.api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("錯誤：未設置 GEMINI_API_KEY")
        logger.error("請使用 --api-key 參數或設置環境變數")
        logger.error("  Windows PowerShell: $env:GEMINI_API_KEY='your-api-key'")
        logger.error("  Linux/Mac: export GEMINI_API_KEY='your-api-key'")
        return 1
    
    try:
        # 步驟計數
        total_steps = 4
        
        # 步驟 1: 掃描 PDF 檔案
        logger.info(f"\n[步驟 1/{total_steps}] 掃描 PDF 檔案...")
        logger.info(f"  資料夾: {args.input}")
        
        pdf_files = get_pdf_list(
            args.input,
            recursive=args.recursive,
            validate=not args.no_validate
        )
        
        if not pdf_files:
            logger.error("錯誤：未找到任何 PDF 檔案")
            return 1
        
        logger.info(f"  找到 {len(pdf_files)} 個 PDF 檔案")
        
        # 步驟 2: OCR 辨識
        logger.info(f"\n[步驟 2/{total_steps}] OCR 辨識...")
        logger.info(f"  使用模型: {args.model}")
        
        if args.privacy_mode:
            # 隱私模式：使用遮罩圖片
            logger.info(f"  模式: 隱私模式（遮蓋個資）")
            logger.info(f"  遮罩圖片儲存目錄: {args.masked_output_dir}")
            
            masked_dir = Path(args.masked_output_dir)
            masked_dir.mkdir(exist_ok=True)
            
            privacy_extractor = PrivacyOCRExtractor(api_key, model=args.model)
            ocr_results = privacy_extractor.batch_extract(
                pdf_files,
                masked_output_dir=masked_dir
            )
        else:
            # 完整模式：上傳完整圖片
            logger.info(f"  模式: 完整模式（包含個資）")
            from ocr_extractor import OCRExtractor
            extractor = OCRExtractor(api_key, model=args.model)
            ocr_results = extractor.batch_extract(
                pdf_files,
                save_results=args.save_ocr_results,
                output_path=Path("ocr_results.json") if args.save_ocr_results else None
            )
        
        # 統計
        success_count = sum(1 for r in ocr_results if r.get('success', False))
        if success_count == 0:
            logger.error("錯誤：所有 PDF 辨識都失敗")
            return 1
        
        logger.info(f"  成功辨識: {success_count}/{len(ocr_results)}")
        
        # 步驟 3: 資料彙整
        logger.info(f"\n[步驟 3/{total_steps}] 資料彙整...")
        
        aggregator = DataAggregator()
        aggregator.batch_add_results(ocr_results)
        
        stats = aggregator.get_statistics()
        logger.info(f"  學生總數: {stats['total_students']}")
        logger.info(f"  評分表數: {stats['total_files']}")
        logger.info(f"  平均評分數/學生: {stats['avg_scores_per_student']}")
        logger.info(f"  有完整評分的學生: {stats['students_with_all_scores']}")
        
        data = aggregator.get_aggregated_data(sort_by_order=True)
        
        # 步驟 4: 輸出 CSV
        logger.info(f"\n[步驟 4/{total_steps}] 輸出 CSV...")
        logger.info(f"  輸出路徑: {args.output}")
        
        success = write_csv(data, args.output)
        
        if not success:
            logger.error("錯誤：寫入 CSV 失敗")
            return 1
        
        # 完成
        logger.info(f"\n{'='*60}")
        logger.info("✓ 處理完成！")
        logger.info(f"{'='*60}")
        logger.info(f"輸出檔案: {Path(args.output).absolute()}")
        logger.info(f"學生數: {len(data)}")
        logger.info(f"評分表數: {stats['total_files']}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\n\n使用者中斷")
        return 130
    except Exception as e:
        logger.error(f"\n錯誤: {e}", exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
