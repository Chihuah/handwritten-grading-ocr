# OCR 評分表辨識系統

自動辨識手寫評分表 PDF，使用 Gemini API 進行 OCR，並計算學生最終成績。

## 功能特色

- **隱私保護模式**：自動遮蓋學號和姓名後才上傳到 Gemini API
- **批次處理**：支援一次處理多個 PDF 評分表
- **極端值去除**：計算成績時自動去除前後各 10% 的極端評分
- **結構化輸出**：產生標準 CSV 格式的評分結果

## 工作流程

```
PDF 評分表 → 遮罩處理 → Gemini OCR → 彙整資料 → 評分 CSV → 計算最終成績 → 成績 CSV
```

### 步驟一：OCR 辨識評分表

使用 `main.py` 將評分表 PDF 轉換為遮罩圖片，上傳到 Gemini 進行 OCR，產生評分 CSV。

```bash
# 隱私模式（建議）
python main.py --input <PDF資料夾> --output <輸出CSV> --privacy-mode --api-key <API_KEY>

# 範例
python main.py --input report1 --output scoresI.csv --privacy-mode --api-key YOUR_API_KEY
python main.py --input report2 --output scoresII.csv --privacy-mode --api-key YOUR_API_KEY
```

**參數說明：**
| 參數 | 說明 |
|------|------|
| `--input, -i` | 包含評分表 PDF 的資料夾路徑 |
| `--output, -o` | 輸出 CSV 檔案路徑 |
| `--privacy-mode, -p` | 隱私模式：遮蓋學號姓名後才上傳（建議啟用）|
| `--api-key, -k` | Gemini API Key |
| `--model, -m` | Gemini 模型（預設: gemini-3-flash-preview）|
| `--recursive, -r` | 遞迴搜尋子資料夾 |
| `--verbose, -v` | 啟用詳細日誌 |

### 步驟二：計算最終成績

使用 `calculate_final_scores.py` 計算去除極端值後的最終成績。

```bash
python calculate_final_scores.py -i <評分CSV> -o <成績CSV>

# 範例
python calculate_final_scores.py -i scoresI.csv -o final_scoresI.csv -v
python calculate_final_scores.py -i scoresII.csv -o final_scoresII.csv -v
```

**成績計算邏輯：**
1. 收集每位學生的所有評分（可能 50-65 份不等）
2. 排序後去除前後各 10% 的極端值
3. 計算剩餘分數的平均值
4. 乘以 10 並四捨五入，得到最終成績（滿分 100）

## 專案結構

```
OCR_reportgrading/
├── main.py                    # 主程式入口
├── calculate_final_scores.py  # 最終成績計算
├── src/
│   ├── pdf_processor.py       # PDF 檔案掃描與驗證
│   ├── mask_processor.py      # 隱私遮罩處理
│   ├── privacy_ocr_extractor.py  # 隱私模式 OCR
│   ├── ocr_extractor.py       # 完整模式 OCR
│   ├── data_aggregator.py     # 資料彙整
│   └── csv_writer.py          # CSV 輸出
├── report1/                   # 期中報告 I PDF 檔案
├── report2/                   # 期中報告 II PDF 檔案
└── masked_images/             # 遮罩後的圖片快取
```

## 環境設置

### 前置需求

- Python 3.10 或以上版本
- Gemini API Key（[取得 API Key](https://aistudio.google.com/app/apikey)）

### 安裝步驟

1. **Clone 專案**
```bash
git clone https://github.com/Chihuah/handwritten-grading-ocr.git
cd handwritten-grading-ocr
```

2. **建立虛擬環境**
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **安裝依賴套件**
```bash
pip install -r requirements.txt
```

### API Key 設定

您需要設定 Gemini API Key 才能使用 OCR 功能：

**方法一：環境變數（建議）**
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your-api-key-here"

# Linux/Mac
export GEMINI_API_KEY="your-api-key-here"
```

**方法二：命令列參數**
```bash
python main.py --api-key your-api-key-here --input report1 --output scores.csv
```

⚠️ **重要**：請勿將 API Key 直接寫入程式碼或上傳到 GitHub！

## 注意事項

- **隱私保護**：建議使用 `--privacy-mode` 參數，系統會在上傳前自動遮蓋學號和姓名區域
- **評分表格式**：遮罩座標已針對標準評分表格式調整，支援最多 37 位學生
- **檔案管理**：上傳到 Gemini 的檔案會在處理完成後自動刪除
- **批次處理**：系統支援一次處理整個資料夾的 PDF 檔案

## 常見問題

### Q: 為什麼需要 Gemini API Key？
A: 本專案使用 Google Gemini API 進行 OCR 辨識。您可以在 [AI Studio](https://aistudio.google.com/app/apikey) 免費取得 API Key。

### Q: 隱私模式和完整模式有什麼差別？
A: 
- **隱私模式**（`--privacy-mode`）：會先遮蓋學號和姓名區域，只上傳遮罩後的圖片到 Gemini API
- **完整模式**：上傳完整的評分表圖片（包含個資）到 Gemini API

基於隱私保護，強烈建議使用隱私模式。

### Q: 支援哪些 PDF 格式？
A: 支援標準的單頁或多頁 PDF 評分表。系統會自動將 PDF 轉換為圖片後進行 OCR。

### Q: 如何確認處理結果？
A: 可以使用 `--verbose` 參數查看詳細的處理日誌，或使用 `--save-ocr-results` 參數儲存 OCR 原始結果到 JSON 檔案。

## 技術細節

- **OCR 引擎**：Google Gemini Vision API
- **PDF 處理**：PyMuPDF (fitz)
- **圖片處理**：Pillow (PIL)
- **成績計算**：Trimmed Mean（去除前後 10% 極端值）

## 授權協議

本專案採用 [MIT License](LICENSE) 授權。


