# Pokémon Fire Ash 繁體中文化

目前已完成訊息表與補充腳本介面的繁中預覽版，所有區段待翻數為 0；保留的姓名、暱稱、縮寫及程式識別碼另列明細。Claude 1 已套用到本機遊戲，實機驗收正在進行，尚未完成實機驗收。

維護來源：[NiceJobGuys/FireAsh-Translate-zh-TW](https://github.com/NiceJobGuys/FireAsh-Translate-zh-TW)。這是私人專案，存取需要自己的 GitHub 帳號與 repo 權限。

版本基準為本機現有安裝：資料夾名稱為 3.7，內附 Changelog 最新條目為 3.7.1，程式內 Settings::GAME_VERSION 仍為 3.7.0。因此以 `source-manifest.json` 的檔案 SHA-256 作為實際基準，不僅依資料夾名稱判斷版本。

2026-10-30 第129批及校對建置已翻譯 40,775／42,534 筆非空白文字位置，明確保留 1,759 個位置。原訊息檔 29／29 個區段均無待翻項目；其中劇情已翻 15,218／15,288 種文字，另 70 種明確保留。原訊息檔以外的腳本介面亦完成 115／115 種。每個 section 的譯文、保留與待翻數見 `coverage.json`。這是訊息表覆蓋量，包含重複、開發及未使用文字，不代表圖片、實際流程與畫面已經驗收。名稱與部分說明取自 [PokeAPI 資料](https://github.com/PokeAPI/pokeapi/tree/2bf639e5572812a67d2b94903fdcb9d095f5aeb2/data/v2/csv)的繁中欄位，其餘由 Codex 翻譯，未使用外部翻譯 API。

遊戲介紹與下載：[開發者發布頁](https://eeveeexpo.com/threads/9489/)。

## 下載與安裝（或套用）

目前只提供翻譯來源、工具、測試與文件，尚未發布安裝包，不建立 Release 或 tag。實機驗收完成並決定發布後，才會在 [最新 Release](https://github.com/NiceJobGuys/FireAsh-Translate-zh-TW/releases/latest) 提供下載；該連結在首次發布前沒有可下載版本。

目前產出均在 `D:\Code\Lab Testing\Artifacts\`：

| 產出 | 路徑 | 狀態 |
| --- | --- | --- |
| 繁中語言檔 | `release\fire-ash-zh-tw-preview\Data\traditional_chinese.dat` | 已建置並由原遊戲 Ruby DLL 載入驗證 |
| 修改後腳本 | `data\fire-ash-work\patched\Scripts.rxdata` | 新增繁中選項、字型與中文斷行支援；僅本機保留 |
| 本機中文字型 | `data\fire-ash-work\fonts\fire-ash-zhtw.ttf` | Fusion Pixel Font 12px zh_tw，OFL 1.1；不 commit 字型 |
| 字型授權 | `data\fire-ash-work\fonts\fire-ash-zhtw-OFL.txt` | 原始及上游授權文字，隨字型套用 |
| 覆蓋報告 | `release\fire-ash-zh-tw-preview\coverage.json` | 各類別詳細統計 |

本機已由 Claude 1 套用，原檔備份位於 `D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-install-20261030`。套用與實機驗收由 Claude 1 管理；repo 不包含遊戲檔、字型、存檔或還原備份。

本機套用範圍僅有：

1. 備份並替換 `Data\Scripts.rxdata`。
2. 新增 `Data\traditional_chinese.dat`。
3. 新增 `Fonts\fire-ash-zhtw.ttf`。
4. 新增 `Fonts\fire-ash-zhtw-OFL.txt`，保留字型與上游授權。

實機回報舊版正黑體模糊後，已改用 [Fusion Pixel Font](https://github.com/TakWolf/fusion-pixel-font) 2026.10.25 的 `zh_tw` 等寬版（OFL 1.1）。`zh_tw` 參考台灣標準字形，`zh_hant` 參考傳統印刷字形；兩者零缺字、字寬相同，本專案以台灣繁中為目標而選 `zh_tw`，不改譯文或 PokeAPI 的 zh-Hant 詞彙來源。Cubic 11 缺「戽」「桄」而未採用；新字型涵蓋全部 3,195 個用字。普通／小字實際為 24／12px，皆為原生 12px 格線的整數倍。本機引擎會將 API 字級乘 0.9 後取整數，因此 `Font.size` 設為 27／14。字型 SHA、下載來源與原始授權雜湊見 `font-source.json`。

`solidFonts` 維持原設定，不修改 `mkxp.json`。完整字集在 12／24px 的未二值化 FreeType 灰階遮罩只有 0／255，無需全域改動英文渲染。中文繪製暫停人工粗體／斜體，結束後還原樣式；原有硬邊陰影仍保留。新版本仍須 Claude 1 還原舊版、重新套用後完成實機驗收。

保留所有既有語言的索引，繁中加在語言清單最後。遊戲內由 Options → Language 選擇「繁體中文」。此路徑已由程式與資料結構核對，遊戲畫面結果待 Claude 1 完成驗收後更新。

腳本修改包含 Settings 的語言清單、DrawText 兩個排版函式的中文斷行點，以及 Main 前新增的字型與執行期翻譯支援模組。原版依空白斷行，無空白中文會超框；新增的斷行點不插入字元，也不變更訊息索引。Game.ini 不需修改。

另修正 11 處先插入動態數值、才查語言表而漏翻的呼叫，並將強化商店名稱／說明與地區紀錄標題改為只在顯示時翻譯。內部強化名稱、價格、等級、能量、比較及存檔識別名稱仍為原版。實際修改呼叫及來源腳本見 `runtime-localization-patches.json`。

## 還原與更新

套用前先把原始腳本與原有同名檔案備份到 `Artifacts\backup\`，並記錄原始 SHA-256。還原時放回原腳本，移回／移出本次新增的語言檔與字型。請保留 Claude 1 套用時的完整備份；本次 repo 建立作業不執行套用或還原。

本機套用工具預設只顯示計畫，核對來源與產物雜湊。`install` 先備份原檔，再透過同目錄暫存檔校驗與替換；`restore` 從備份還原腳本，將新增語言與字型移回備份目錄。套用後另被修改的檔案會拒絕覆寫。工具不啟動或關閉遊戲。

還原接受兩種完整清單：舊版三檔，或含 OFL 的新版四檔。仍拒絕不完整、重複、額外及越界路徑，且還原前校驗全部原檔／套用檔雜湊；不需要修改既有備份 manifest。

`plan`／`install` 的基準是尚未套用、符合 `source-manifest.json` 的原版檔案。已套用中的遊戲不應重跑安裝；驗收期間不要對該目錄重新匯出或建置。以下指令供未套用的基準副本及後續維護使用。

```powershell
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\install_preview.py' plan
```

後續需要重新套用時，先核對原版基準、取得對應寫入授權並正常退出遊戲，再指定尚未使用過的備份目錄，例如：

```powershell
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\install_preview.py' install --game 'D:\Games\Pokemon Fire Ash\Pokemon Fire Ash 3.7' --backup 'D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-reinstall'
```

目前這次套用的還原指令如下。重新套用後，還原時須改用該次實際備份目錄：

```powershell
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\install_preview.py' restore --backup 'D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-install-20261030'
```

遊戲更新後重新比對來源雜湊、匯出新增文字並重建，不直接覆蓋新版腳本。發佈包不應包含修改後完整 `Scripts.rxdata`，應由套用工具對玩家本機原檔重建；目前的修改後腳本僅供本機驗證。

## 原始碼與翻譯

| 檔案 | 用途 |
| --- | --- |
| `translation-source/catalog.jsonl` | 按類別去重的英文文字、類別及出現次數 |
| `translations/reference.jsonl` | 5,740 筆 PokeAPI 繁中對照與來源 |
| `translations/manual.json` | 選單、常用訊息、開場與術語 |
| `translations/manual-names.json` | 官方名稱拼字差異與自訂招式、特性、道具名稱草稿 |
| `translations/manual-story.json` | 真新鎮及相關角色對話 |
| `translations/batches/*.json` | 後續分批譯文；包含逐鍵對照或原文雜湊加固定順序譯文 |
| `translation-source/batches/*.jsonl` | 固定順序批次的原文，與同名譯文檔配對 |
| `translations/preserved.json` | 刻意保留原文的類別、筆數明細及理由 |
| `translations/teleport-template.json` | 已審閱的傳送句型用語、地名及保留暱稱 |
| `translations/template-derived.jsonl` | 由固定傳送句型產生的完整原文／譯文對照 |
| `translations/runtime-identifiers.json` | 不得翻譯的執行期背景資源名稱及程式依據 |
| `translations/runtime-ui.json` | 直接寫在腳本、未納入原訊息檔的介面譯文 |
| `translation-source/runtime-ui.jsonl` | 補充介面英文來源，含依原程式產生的等級標籤 |
| `translations/terminology-sources.json` | PokeAPI 未涵蓋的動畫地名補充查證來源 |
| `glossary.json` | 人名、地名、劇情及自訂專有名詞對照與原文保留政策 |
| `terminology-audit.json` | 官方名稱一致性與禁止用語檢查結果 |
| `tools/fire_ash.py` | 匯出、參考資料對照、控制碼驗證與本機建置 |
| `tools/font_support.rb` | 字型切換、中文選項字型、中文斷行及標點禁則 |
| `tools/verify_ruby.py` | 用原遊戲 Ruby DLL 驗證 Marshal、腳本語法與字型切換邏輯 |
| `tools/verify_layout.rb` | 重現原版中文超框；原遊戲排版函式搭配新字型實際 FreeType 字寬 |
| `font-source.json` | 固定字型來源、雜湊、OFL、原生字級與引擎換算證據 |
| `tools/prepare_baseline.py` | 從既有備份與未改動原檔建立四檔原版建置副本，不寫入遊戲 |
| `tools/font_preview.py` | 512x384 字型算繪與四倍最近鄰預覽，非遊戲截圖 |
| `font-preview-validation.json` | 預覽字界、排版與產物雜湊，不代表實機通過 |
| `tools/runtime_support.rb` | 動態句子查詢、舊編碼字串相容及只用於顯示的強化名稱 |
| `tools/verify_runtime.rb` | 用原強化程式驗證翻譯後的選項、購買、升級、能量與原始識別名稱 |
| `runtime-localization-patches.json` | 腳本顯示呼叫的修改清單 |
| `translation-source/known-source-issues.json` | 保留原控制碼時發現的原文問題 |
| `source-manifest.json` | 基準檔案雜湊 |
| `coverage.json` | 每類翻譯數量；由建置產生 |
| `validation.json` | 原生 Ruby 驗證結果；不代表遊戲實測 |
| `tools/install_preview.py` | 本機四檔套用計畫（含 OFL）、事前備份、校驗與還原 |
| `tools/test_install_preview.py` | Artifacts 內的套用／還原、複製中斷與拒絕覆寫測試 |
| `deployment-validation.json` | 本機套用工具測試結果與程式雜湊；不是實際安裝紀錄 |
| `script-character-audit.json` | 簡繁候選字人工判讀、採用字形與語言檔雜湊 |
| `trainer-title-audit.json` | 原始訓練家／類型資料與博士頭銜組合的核對結果 |
| `deployment-notes.json` | 測試副本曾遇的 Windows 替換錯誤與未重現紀錄 |
| `MAINTAINING.md` | 批次格式、重建及交付維護限制 |

SQLite 工作資料位於 repo 以外的 `Artifacts\data\fire-ash-work\catalog.sqlite`。下載的參考資料及第三方套件也放在 repo 以外的 `Artifacts\downloads\`。

目前工具使用本專案的 Artifacts 目錄配置；本機套用工具已備妥，尚未製作跨電腦獨立安裝包。Windows／PowerShell 7 重建指令：

```powershell
python -m pip install --no-compile --no-deps --target 'D:\Code\Lab Testing\Artifacts\downloads\fire-ash-python' rubymarshal==1.2.10
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\fire_ash.py' self-test
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\prepare_baseline.py'
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\fire_ash.py' build --game 'D:\Code\Lab Testing\Artifacts\data\fire-ash-work\original-baseline'
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\verify_ruby.py' --game 'D:\Code\Lab Testing\Artifacts\data\fire-ash-work\original-baseline'
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\font_preview.py'
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\test_install_preview.py' --source-game 'D:\Code\Lab Testing\Artifacts\data\fire-ash-work\original-baseline'
```

需本機已有 Python、fontTools、Pillow 及原遊戲的 `x64-msvcrt-ruby300.dll`。先將 `font-source.json` 指定的官方壓縮檔解壓至 `Artifacts\downloads\fusion-pixel-font\`，保留原始 TTF、`OFL.txt` 與 `LICENSES\`。`extract`／`reference` 僅在建立或更新原文時使用，對符合原版雜湊的副本執行；現有翻譯重建不需重新匯出。

建置及驗證須使用符合來源雜湊的原版副本。現有 `coverage.json`、`validation.json` 與 `deployment-validation.json` 是套用前的建置／測試證據，其中 `installed=false` 記錄當時狀態，不代表 Claude 1 目前的實機套用狀態。

## 驗證與已知限制

- 尚未完成實機驗收。Claude 1 已套用本機並正在驗收，以下為先前的文字與原生函式測試結果，不能代替最終遊戲畫面驗收。
- 905 種不同英文寶可夢名稱全部對照完成，涵蓋 1,295 個型態共用名稱欄位；不代表 1,295 種不同寶可夢。
- 1,064／1,065 種不同招式名稱已有譯文，剩餘 `UUDDLRLRBAS` 為按鍵代碼名稱，保留原文。
- 966 種不同道具名稱與 421 種不同特性名稱已有譯文；自訂名稱仍需校對。
- 招式說明 1,025／1,025、道具說明 896／896、特性說明 408／408 種不同文字已翻譯。分類、型態、訓練家類型、電話及獎章說明也已補齊；字母型態、按鍵代碼等有明確保留清單。
- 開場 Map001 與真新鎮 Map033 的語言表文字已有譯文，實際劇情流程待 Claude 1 完成驗收。
- 原訊息表及補充腳本介面均無待翻項目。刻意保留的人名、暱稱、標準縮寫與資源識別碼見保留清單；圖片上的英文尚未處理。
- 使用預設 `messages.dat` 作為基底，包含英文語言檔缺少的較新條目。
- 原始基底可逐位元組往返序列化；產出的所有 42,534 個文字欄位，位置與內容均通過 Python／原生 Ruby 讀取比對。
- 404 段腳本均通過原遊戲 Ruby 3.0.2 語法編譯，並驗證英文／繁中兩種設定下的字型初始化與 setter 行為。
- 每次建置核對像素字型來源 SHA、全部 3,195 個用字及 12／24px 未二值化灰階遮罩；無缺字且透明度僅有 0／255。512x384 設定與對話樣本已實際算繪並放大四倍檢查；測試畫布非遊戲實機截圖。
- 英文模式中遇到中文選項時，文字量測與繪製也會暫時切換至中文字型，完成後還原；已通過邏輯測試，遊戲畫面仍待實測。
- 已在原生 Ruby 重現原版中文無空白時超框。以原遊戲的純文字及格式排版函式搭配新字型實際 FreeType 字寬，驗證 12 個中文案例，涵蓋標點、名字中間點、混合英文、明確換行與停頓碼，並核對 4 個英文排版案例維持相同結果；仍不能代替遊戲截圖驗收。
- 補充介面在覆蓋報告列為工具專用 section 102，不是新的遊戲訊息區段。它的 `occurrences=0` 代表不在原訊息檔中；115 種譯文嵌入腳本，不增加或改動原 42,534 個訊息位置。
- 原生 Ruby 已逐筆核對全部補充字串，並用原強化程式驗證中文選項、說明、數值插入、選項順序、購買價格、升級、裝備及卸下能量。內部英文名稱與舊字串編碼未被顯示翻譯改寫；英文模式回到原顯示方式。
- 術語檢查包含 3,703 筆參考名稱、2,832 處寶可夢名稱、1,036 處地名、2,792 筆具名發話者及 111 筆招式教學台詞。姓名表與劇情以雙向檢查確保同步，21 筆 Drake／Flint 發話維持明示同名例外；其他同名人物的特定劇情對照列於 `glossary.json` 的 `contextual_terms`。
- 本機套用工具已通過 3 個檔案測試：套用與還原、複製中途失敗後還原、拒絕覆寫套用後另行修改的檔案。測試只用 Artifacts 內的副本，原安裝基準檔案雜湊保持相同。
- 測試副本曾出現一次 WinError 5 替換錯誤；備份與原檔完整，單獨再執行三個測試通過，原因未確認，見 deployment-notes.json。實際套用若受阻，保留備份與錯誤，不強制覆寫。
- 已確認原版用「訓練家類型＋姓名」顯示名稱，8 個博士姓名移除重複頭銜，劇情頭銜維持不變；11 個實際組合已核對。Claude 1 兩輪退回項目均已補正，但未發起第三輪驗收，尚無最終接受結論。
- 原版 Masked／Royal 將類型與姓名拆開，可能顯示「蒙面者 Royal」，列為實機待核項。
- 官方繁中名稱「精靈球」保留使用；禁止舊稱「精靈」獨立指稱寶可夢。人名採專用對照，避免將 Mark、Eva 等人名誤譯成介面或能力名稱。
- 字級調整屬預覽設定，尚未經遊戲畫面驗收。存檔相容性及語言切換流程亦未實測。
- Codex 翻譯與建立此 repo 時未呼叫付費翻譯 API，未啟動遊戲或修改玩家存檔；本機套用與實機驗收由 Claude 1 另行處理。

本專案不包含遊戲原版檔案與字型；權利屬各原權利人，為非官方中文化。
