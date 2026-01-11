# OCR 評分表辨識工具

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

## 使用範例

以下是一個完整的使用範例，展示如何使用隱私模式處理評分表：

### 執行命令
```bash
python main.py --input examples/ --output example_output.csv --privacy-mode
```

### 處理流程
```
[步驟 1/4] 掃描 PDF 檔案...
  找到 1 個 PDF 檔案

[步驟 2/4] OCR 辨識...
  使用模型: gemini-3-flash-preview
  模式: 隱私模式（遮蓋個資）
  遮罩圖片儲存目錄: masked_images
  成功提取 36 筆評分

[步驟 3/4] 資料彙整...
  學生總數: 36
  評分表數: 1

[步驟 4/4] 輸出 CSV...
  ✓ 處理完成！
```

### 輸出結果
生成的 CSV 檔案格式（隱私模式）：
```csv
報告順序,學號,姓名,評分1
1,order_1,,9
2,order_2,,8
3,order_3,,6
...
36,order_36,,4
```

**說明**：
- 隱私模式下，學號以 `order_N` 顯示，姓名為空
- 遮罩後的圖片儲存在 `masked_images/` 供檢視
- 僅評分數據上傳到 Gemini API，確保個資安全

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

---

## 專案開發緣起

### 教學場景
本專案源於實際的教學場景需求。在一門課程中，學生除了自己要上台報告外，還需要聆聽同學的口頭報告並給予評分（同儕互評機制），每位同學會對其他同學的報告在評分表上手寫 1-10 分的評分。課程包含兩次期中報告（第一次 36 人，第二次 37 人，共 73 位學生），每次報告會收集約 65 份評分表（因部分學生缺席或未繳交）。

### 資料處理挑戰
評分表是以 PDF 格式掃描保存，每張評分表包含該評審（學生）對所有其他學生的評分。傳統做法需要人工逐一輸入每份評分表的數據，不僅耗時費力，還容易出錯。更重要的是，這些資料需要進行**轉置處理**：

- **原始資料結構**（評分表視角）：每份 PDF 記錄一位評審對所有 36-37 位學生的評分
- **目標資料結構**（學生視角）：每位學生收到的所有評分需要彙整成一列

### 解決方案
本專案利用 Google Gemini Vision API 的 OCR 能力，開發了一套自動化系統來解決這些問題：

1. **批次處理**：自動讀取資料夾中的所有評分表 PDF 檔案
2. **手寫辨識**：使用 Gemini-3-flash API 的多模態視覺處理能力準確辨識手寫評分（1-10 分）
3. **資料轉置**：將「評分表視角」自動轉換為「學生視角」
4. **隱私保護**：提供隱私模式，在上傳前遮蓋學號和姓名等個人資料
5. **CSV 輸出**：自動產生結構化的 CSV 檔案，每位學生一列，包含所有評分

透過這套系統，原本需要一至三小時的人工輸入工作，現在只需十幾分鐘即可完成，大幅提升了教學行政效率，並確保資料的準確性與隱私安全。

---

## 致謝

本專案採用 **Antigravity** 做為開發 IDE，並使用 **Claude Opus 4.5 (Thinking)** 模型來規劃與實作所有程式碼。專案的 OCR 核心功能得力於 **Google Gemini-3-Flash** 的強大視覺識別能力。

