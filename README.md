# Pokémon Fire Ash 繁體中文化

**2026-11-01 情境誤譯與插件漏翻已修正並套用：**五月、薄霧場地、寄放盒桌布改用符合用途的譯文，保留人物姓名；補齊讀檔／極巨大冒險提示及選項，圖鑑屬性與命名鍵盤圖片也有中文。安裝 Scripts `8797f897…`、語言 `d4cc61cd…`，保留現有編輯器與提示 MOD。原生查詢與選項分支、173 個 CPU 畫面案例通過；未啟動遊戲驗收。詳見 [修正與還原紀錄](context-ui-fix.md)。

**2026-11-01 報名選單修正已套用：**`Entry`／`No Entry` 改為「報名參賽／取消報名」，本次只更新語言檔（`a1f89d69…`），保留現有 Scripts（`65816813…`）及全部 MOD。原生文字查詢、兩筆差異比對與 11 項安裝測試通過；未啟動遊戲驗收。備份及還原見 [報名選單修正](registration-fix.md)。以下為先前各輪的歷史紀錄。

**2026-11-01 性別／PP 補正已套用：**前一版確實已安裝，但 PP 測試誤把邊框當成可用區域，性別字型重播也與實機不同。本版依真正白底邊界安排 PP，性別改為固定像素圖示並與 Lv. 留 8px。合併安裝 SHA `105ea77f…`，152 個畫面案例通過，仍待實機確認。現行備份為 `D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-battle-spacing-20261101`，詳見 [battle-ui-spacing-fix.md](battle-ui-spacing-fix.md)。

**2026-11-01 戰鬥 UI 修正已套用：**戰鬥指令、共用屬性及行動按鈕圖片改為中文，並修正姓名／性別／等級、招式與 PP 的欄位邊界。已保留現有寶可夢編輯器 v5 與 EV 結算修正，只更新三個 UI 腳本；實際安裝 SHA 為 `2469c484…`。純翻譯版與相容合併版分別通過 140 個畫面案例，實機待確認。現行備份為 `D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-battle-ui-fix-20261101`，還原及後續更新務必依 [battle-ui-fix.md](battle-ui-fix.md)，下方為前輪紀錄。

**2026-11-01 選項裁切與對齊修正已套用：**修正共用選項 painter 的固定下移與格式化選單少算 6px 高度，PC 選單最後一列完整顯示、文字與箭頭對齊。30 個選單案例、既有對話回歸、9 項安裝／還原及 5 項樣本隔離測試通過，實機待確認。詳見 [command-window-fix.md](command-window-fix.md)。目前備份為 `D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-command-window-fix-20261101`，下方為前輪紀錄。

**2026-11-01 第二行裁切修正已套用：**前版只加大 bitmap，仍被外層 64px 可見範圍裁切。現版讓文字完整落在各 32px 行框內，Noto 對話上移 6 個原生像素，字型／字級／行距／視窗大小不變。32 個雙層裁切與捲動案例、8 個圖示案例、9 項安裝／還原及 5 項樣本隔離測試通過。實機畫面待確認，詳見 [text-buffer-fix.md](text-buffer-fix.md)。現行備份為 `D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-viewport-fix-20261101`；下方為前輪紀錄。

**2026-11-01 套用更新：**使用者已授權每次翻譯驗證完成後直接備份套用。Codex 已將下述 1,207 筆修正與先前選定的 Noto Medium 安裝至本機遊戲，四檔 SHA 校驗通過；未啟動遊戲，畫面仍待實機驗收。現行備份為 `D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-runtime-translation-20261101`。下文 2026-10-31 的未套用敘述為建置時紀錄，以本段更新為準。

2026-10-31 實機漏翻修正：追加 **1,207 筆**實際執行時使用的繁中查詢（1,206 筆腳本、1 筆共用地圖文字），涵蓋收納道具、開新遊戲／存檔、化石復活、奇蹟交換、世界錦標賽與俱樂部對話、強化說明及挑戰隊伍標題。修正獨立地圖選單與直接提示繞過翻譯、中文強化名稱對不到說明的問題。原有 42,534 個語言欄位內容與順序不變，新版共 43,741 個欄位。**已建置，尚未套用至遊戲或完成實機驗收。** 詳見 [runtime-translation-fix.md](runtime-translation-fix.md)。

原遊戲文字擷取器會漏掉單引號、動態資料對話，並錯誤處理部分反斜線。新工具使用遊戲原生 Ruby AST 取得實際字串，另涵蓋已追查的動態資料來源；不把既有表的 pending=0 當成全遊戲漢化完成。新增回歸：5,337 個含英文字母的固定查詢零缺鍵、1,207 筆補充值、45 組獨立選單、10 項強化分支、兩條實際道具取得函式與英文回退均通過。圖片與未涵蓋的動態路徑仍需驗收。

2026-10-31 使用者選定字重樣本 A：Noto Sans CJK TC Medium 500。新增 Noto 原始 OTF 試裝來源，repo 的建置預設在實機通過前仍為 Fusion Pixel，正黑體流程保留；本次報告記錄 Noto 建置，尚未套用或完成實機驗收。語言檔保留「全螢幕」修正。字型皆不進 repo，正黑體與衍生檔也不進 Release；本輪不建立 Release／tag。原五種顯示選項不變，3 倍未納入，原因見 [3x-engine-blocker.md](3x-engine-blocker.md)。

目前已完成既有訊息表、補充腳本介面及本輪發現的漏翻，所有已納入來源的區段待翻數為 0；保留的姓名、暱稱、縮寫及程式識別碼另列明細。Claude 1 先前套用的是舊版，本輪修正尚未套用。

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
| 本機中文字型 | `data\fire-ash-work\fonts\fire-ash-zhtw.otf` | Noto 原檔、未轉換；pixel／jhenghei 建置改用同目錄 `.ttf`，皆不 commit 字型 |
| 字型說明 | `data\fire-ash-work\fonts\fire-ash-zhtw-OFL.txt` | Noto 的原始 LICENSE；pixel 是 Fusion Pixel 授權，jhenghei 改用 LOCAL-ONLY，依報告 SHA 核對 |
| 覆蓋報告 | `release\fire-ash-zh-tw-preview\coverage.json` | 各類別詳細統計 |

本機遊戲目前已套用性別／PP 補正版（Scripts `105ea77f…`），使用 Noto Medium，保留編輯器 v5；現行備份為 `D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-battle-spacing-20261101`。語言、字型、Game.exe／Game.ini／mkxp.json 與存檔未變，未啟動遊戲；畫面待使用者實機確認。repo 不包含遊戲檔、字型、存檔或還原備份。

本機套用範圍僅有：

1. 備份並替換 `Data\Scripts.rxdata`。
2. 新增 `Data\traditional_chinese.dat`。
3. Noto 新增 `Fonts\fire-ash-zhtw.otf`；pixel／jhenghei 使用 `Fonts\fire-ash-zhtw.ttf`。
4. Noto／pixel 新增各自的 `Fonts\fire-ash-zhtw-OFL.txt`，內容與 SHA 不同；jhenghei 新增 `Fonts\fire-ash-zhtw-LOCAL-ONLY.txt`。先完整還原舊版，再依該次 coverage／plan 的字型及授權 SHA 套用，不混用另一來源。

Noto 沿用 `NotoSansCJKtc-Medium.otf`（Sans2.004）及同目錄 LICENSE 的完整原始位元組，沒有轉換、子集或改字型名稱。來源與 SHA 見 `font-source-noto.json`。本機 Game.exe 靜態檢查已確認 `.otf`／`.ttf` 都會掃描、非 Regular 字面會進 other 槽、FreeType 預設模組含 CFF。family 使用 FreeType 的 `Noto Sans CJK TC`，並容許同字檔的舊式 family `Noto Sans CJK TC Medium`；不是換成別的字型。僅繁中模式檢查 `Font.exist?`，若未註冊則顯示 `Noto font not loaded: Fonts/fire-ash-zhtw.otf` 並停止目前流程，避免靜默退回英文字型／方塊。真正遊戲載入仍待實機，不能以靜態檢查宣稱通過。

正黑體試裝選用 Windows 本機 `C:\Windows\Fonts\msjh.ttc` 第 0 個 face，Microsoft JhengHei Regular 6.15。建置工具保留完整字面與原始著作權／fsType 中繼資料，輸出本機 TTF；不是 subset，不變造名稱或宣稱為 OFL。24／12px 對應 API 27／14，中文無陰影，英文 Power 字型、陰影與原先顯示行為不變。來源與 SHA 見 `font-source-jhenghei.json`；所有字型檔及衍生檔均被 `.gitignore` 排除。

實機回報舊版正黑體模糊後，已改用 [Fusion Pixel Font](https://github.com/TakWolf/fusion-pixel-font) 2026.10.25 的 `zh_tw` 等寬版（OFL 1.1）。`zh_tw` 參考台灣標準字形，`zh_hant` 參考傳統印刷字形；兩者零缺字、字寬相同，本專案以台灣繁中為目標而選 `zh_tw`，不改譯文或 PokeAPI 的 zh-Hant 詞彙來源。Cubic 11 缺「戽」「桄」而未採用；新字型涵蓋全部 3,195 個用字。普通／小字實際為 24／12px，皆為原生 12px 格線的整數倍。本機引擎會將 API 字級乘 0.9 後取整數，因此 `Font.size` 設為 27／14。字型 SHA、下載來源與原始授權雜湊見 `font-source.json`。

`solidFonts` 維持原設定，不修改 `mkxp.json`。完整字集在 12／24px 的未二值化 FreeType 灰階遮罩只有 0／255。繁中模式的選單、分行文字與格式對話不再疊畫三層陰影；英文模式及明確指定的外框效果保留。中文字型仍暫停人工粗體／斜體，結束後還原樣式。

設定 → 畫面大小沿用 S／M／L／XL／全螢幕，依序為 0.5／1／1.5／2 倍及全螢幕，索引與 getter 維持原版。原 Scripts 中完整 `Full` 字串只有 UI_Options 第 374 行一處，用於畫面大小；未與容量已滿共用，證據見 `full-key-usage.json`。因此直接修正 section 24，不加情境攔截。保留既有設定，預設仍為 L／1.5 倍，畫布維持 `512×384`；五個值以原生 draw calls 核對不重疊、不碰邊。

保留所有既有語言的索引，繁中加在語言清單最後。遊戲內由 Options → Language 選擇「繁體中文」。此路徑已由程式與資料結構核對，遊戲畫面結果待 Claude 1 完成驗收後更新。

腳本修改包含 Settings 的語言清單、DrawText 兩個排版函式的中文斷行點，以及 Main 前新增的字型與執行期翻譯支援模組。原版依空白斷行，無空白中文會超框；新增的斷行點不插入字元，也不變更訊息索引。Game.ini 不需修改。

另修正 11 處先插入動態數值、才查語言表而漏翻的呼叫，並將強化商店名稱／說明與地區紀錄標題改為只在顯示時翻譯。內部強化名稱、價格、等級、能量、比較及存檔識別名稱仍為原版。實際修改呼叫及來源腳本見 `runtime-localization-patches.json`。

## 還原與更新

套用前先把原始腳本與原有同名檔案備份到 `Artifacts\backup\`，並記錄原始 SHA-256。還原時放回原腳本，移回／移出本次新增的語言檔與字型。請保留 Claude 1 套用時的完整備份；本次 repo 建立作業不執行套用或還原。

本機套用工具預設只顯示計畫，核對來源與產物雜湊。`install` 先備份原檔，再透過同目錄暫存檔校驗與替換；`restore` 從備份還原腳本，將新增語言與字型移回備份目錄。套用後另被修改的檔案會拒絕覆寫。工具不啟動或關閉遊戲。

還原只接受四種完整白名單：舊版三檔、含 OFL 的像素四檔、含 LOCAL-ONLY 的正黑體四檔、含 `.otf` 與 Noto OFL 的 Noto 四檔。仍拒絕不完整、重複、額外及越界路徑，還原前校驗全部原檔／套用檔 SHA；不修改既有備份 manifest。`--font-source pixel|jhenghei|noto` 可核對指定來源與最後建置是否一致。正黑體現行備份的還原案例使用實際 manifest／原檔／已套用檔快照，只在 Artifacts fixture 還原，不觸碰真正遊戲。

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
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\install_preview.py' restore --backup 'D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-jhenghei-trial-20261031'
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
| `tools/verify_display.rb` | 執行原版／修改後繪字函式、選單 drawItem 與縮放流程；錄下真實繪製呼叫 |
| `font-source.json` | 固定字型來源、雜湊、OFL、原生字級與引擎換算證據 |
| `font-source-jhenghei.json` | 本機正黑體 Regular face 0 的固定來源、SHA 與禁止散布限制 |
| `font-source-noto.json` | 未修改的 Noto Medium OTF／LICENSE SHA、family 與尺寸 |
| `tools/font_loader_audit.py` | 唯讀核對指定 Game.exe 的 OTF 掃描／family／CFF 模組位元組，不執行遊戲 |
| `full-key-usage.json` | 原 Scripts 完整 Full 字串的使用情境查核 |
| `tools/prepare_baseline.py` | 從既有備份與未改動原檔建立四檔原版建置副本，不寫入遊戲 |
| `tools/font_preview.py` | 以 FreeType 重播原生 Ruby 繪製呼叫，產生 1／2／4 倍最近鄰對照；非遊戲截圖 |
| `tools/test_font_sample.py` | 驗證平滑字型樣本成功／失敗均不覆寫正式產物、報告及預覽 |
| `tools/weight_sample.py` | 固定 A／B／C 字重的隔離比較；不重建套用檔、不選定正式字型 |
| `font-preview-validation.json` | 預覽字界、排版與產物雜湊，不代表實機通過 |
| `tools/runtime_support.rb` | 動態句子查詢、舊編碼字串相容及只用於顯示的強化名稱 |
| `tools/verify_runtime.rb` | 用原強化程式驗證翻譯後的選項、購買、升級、能量與原始識別名稱 |
| `runtime-localization-patches.json` | 腳本顯示呼叫的修改清單 |
| `translation-source/known-source-issues.json` | 保留原控制碼時發現的原文問題 |
| `source-manifest.json` | 基準檔案雜湊 |
| `coverage.json` | 每類翻譯數量；由建置產生 |
| `validation.json` | 原生 Ruby 驗證結果；不代表遊戲實測 |
| `tools/install_preview.py` | 三種字型的本機四檔計畫、事前備份、校驗及四種完整白名單還原 |
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

預設 `build` 等同 `--font-source pixel`，保留 Fusion Pixel 的下載、OFL、格線與零灰邊檢查；明確指定 `jhenghei` 或 `noto` 才建置該來源。三種來源共用 staging 與四份正式報告，最後一次建置會取代 staging；切換後須重跑 Ruby、安裝 fixtures、預覽與隔離測試，不可混用前一來源的報告。Noto 建置另外需要本機已有 pefile，唯讀核對固定引擎指紋。

```powershell
# Noto Medium 原始 OTF 試裝
python tools\fire_ash.py self-test --font-source noto
python tools\fire_ash.py build --game '..\fire-ash-work\original-baseline' --font-source noto
# 正黑體本機試裝
python tools\fire_ash.py self-test --font-source jhenghei
python tools\fire_ash.py build --game '..\fire-ash-work\original-baseline' --font-source jhenghei
# 切回預設像素來源（保留「全螢幕」修正）
python tools\fire_ash.py self-test --font-source pixel
python tools\fire_ash.py build --game '..\fire-ash-work\original-baseline' --font-source pixel
```

切回實際遊戲前，先以試裝時的新備份完整還原，再重建像素、重新驗證，以 `install_preview.py plan/install --font-source pixel` 套用；不能直接覆蓋試裝中的遊戲。新備份請用未使用過的目錄，舊備份保留。

## 驗證與已知限制

### 平滑字型樣本（未套用）

使用者選擇先看保留原介面的平滑文字樣本。目前以本機 Microsoft JhengHei Regular、實際 24px、無陰影製作；先在 512×384 算繪，再最近鄰放大。這不是高解析度 UI，也不是劍盾的原字型。

樣本只在獨立 Ruby 測試程序中暫時替換字型 family，以候選字型的 FreeType BASIC 字寬重新執行排版與 painter；不重建／套用遊戲字型。輸出在 repo 外的 `Artifacts\data\fire-ash-work\smooth-font-sample\`，圖片檔名含 `smooth-sample`、`pixel-vs-smooth` 或 `baseline-vs-smooth`。這條樣本路徑維持隔離，與上面的可套用正黑體建置是不同用途；樣本字型直接從本機讀取，不複製或上傳。

```powershell
python tools\verify_ruby.py --game '..\fire-ash-work\original-baseline' --font-sample 'C:\Windows\Fonts\msjh.ttc'
python tools\font_preview.py --font-sample 'C:\Windows\Fonts\msjh.ttc'
python tools\test_font_sample.py
```

樣本報告與正式報告分開；樣本錯誤不會覆寫正式 PASS。測試涵蓋成功／找不到字型兩條路徑，核對正式報告、產物、draw calls 與全部正式預覽的雜湊不變。平滑字型保留正常抗鋸齒，放大後字緣較柔和，不代表已完成實機清晰度驗收。

### 隔離字重比較（未採用）

使用者實機看過 Regular 後要求稍微加粗，固定比較 A：Noto Sans CJK TC Medium 500、B：Microsoft JhengHei Bold 700、C：現行 Regular 400。直接開啟字檔 face 0，實際 24／12px，沒有合成粗體或偏移重畫；各自重新執行原生排版／painter。正式來源預設與套用產物維持不變，是否採用由使用者決定。

Noto 原始 `NotoSansCJKtc-Medium.otf`（Sans2.004）與 LICENSE 放在 `Artifacts\downloads\noto-sans-cjk-tc\`；本機 FreeType 2.14.3 能直接讀取 CFF／OTF，沒有轉 TTF。遊戲 SDL_ttf 靜態包含在 Game.exe，本輪未執行該載入路徑或進遊戲驗證，不以離線結果宣稱遊戲必然可用。Noto 可依 OFL 1.1 隨作品發布並保留授權／著作權；微軟字型及衍生檔僅供本機，不進 repo／Release。

```powershell
python tools\weight_sample.py
python tools\test_font_sample.py
```

輸出是 repo 外的 `Artifacts\images\fire-ash\weight-sample\`：藍色對話、紅色對話、橘色設定、深色 12px 小字四組，每組固定 A／B／C 三欄，保留 1 倍及從 1 倍最近鄰放大的 3.75 倍原檔（寬 5,760px），另有各欄全圖與放大裁切。藍／紅取原 Messages 的 `\b`／`\r` 主色 `#3050C8`／`#E00808`；這是離線原生 draw calls 重播，不是實機截圖。

`Artifacts\data\fire-ash-work\weight-sample\validation.json` 記錄本輪字寬、字界、碰撞、cmap 與工具 SHA，原生 Ruby log 放 `Artifacts\logs\fire-ash-weight-sample\`。既有正式報告保留前一輪建置記錄，沒有因產生樣本而重寫；測試也逐像素核對共用 painter 與既有六張 1 倍預覽相同，並確認正式產物／報告／安裝檔 SHA 不變。12px 複雜字仍密，字重與灰階的取捨需看原尺寸放大圖，不能以較粗直接宣稱實機更清楚。

### 正式版本與實機驗收

- Noto 保留原始 24／12px、API 27／14，不新增 y 偏移；對話、設定與原戰鬥訊息內容區 `(32,306,448,64)` 以實際字面邊界檢查。實機繪製仍待確認；12px 複雜字的擁擠及灰階限制沒有因為字重增加而消失。英文 Power 與三條陰影路徑維持原生回歸。
- 預覽若被 Windows 記憶體映射的檢視器開著，原地覆寫會出現 Errno 22；已以 mmap fixture 重現並補測。相同像素不再覆寫，變更圖另存後替換；無法替換時保留原圖及暫存證據，不關閉使用者的預覽。

- 本輪先交付無陰影以供 Claude 1 套用及實機檢查；原生 draw calls 算繪的預覽不算實機證據。先前含 3 倍選項的預覽與回歸結果不作為本版驗收證據。
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
- 每次建置核對來源 SHA 與全部 3,195 字，正黑體 face 0 與像素版均零缺字（含戽、桄）。像素版的 12／24px 遮罩仍強制只有 0／255；正黑體保留正常灰階抗鋸齒，不假裝是點陣字型。512×384 原生 draw calls 包含設定、淺／深色對話與 12px 小字，從 1 倍原圖最近鄰輸出 3.75 倍全圖與裁切；不是遊戲實機截圖。小字複雜字筆畫仍密，橘色細筆畫仍偏淡，保留 12px 以避免未經驗證的版面擴張，實機可讀性由使用者確認。
- 12 個原生繪製案例確認繁中一般文字由四次繪字降為一次，主字位置／色彩不變；英文模式三條陰影繪製路徑與原版呼叫序列完全相同，明確外框也不變。原五種顯示選項、預設 1.5 倍、2 倍啟動讀回及 stub 的 2.0 上限均有回歸檢查；UI_Options／StartGame 腳本內容與原版相同。
- 英文模式中遇到中文選項時，文字量測與繪製也會暫時切換至中文字型，完成後還原；已通過邏輯測試，遊戲畫面仍待實測。
- 已在原生 Ruby 重現原版中文無空白時超框。以原遊戲的純文字及格式排版函式搭配新字型實際 FreeType 字寬，驗證 12 個中文案例，涵蓋標點、名字中間點、混合英文、明確換行與停頓碼，並核對 4 個英文排版案例維持相同結果；仍不能代替遊戲截圖驗收。
- 補充介面在覆蓋報告列為工具專用 section 102，不是新的遊戲訊息區段。它的 `occurrences=0` 代表不在原訊息檔中；115 種譯文嵌入腳本，不增加或改動原 42,534 個訊息位置。
- 原生 Ruby 已逐筆核對全部補充字串，並用原強化程式驗證中文選項、說明、數值插入、選項順序、購買價格、升級、裝備及卸下能量。內部英文名稱與舊字串編碼未被顯示翻譯改寫；英文模式回到原顯示方式。
- 術語檢查包含 3,703 筆參考名稱、2,832 處寶可夢名稱、1,036 處地名、2,792 筆具名發話者及 111 筆招式教學台詞。姓名表與劇情以雙向檢查確保同步，21 筆 Drake／Flint 發話維持明示同名例外；其他同名人物的特定劇情對照列於 `glossary.json` 的 `contextual_terms`。
- 本機套用工具包含 9 個案例：既有 7 項加上實際正黑體現行備份 manifest 的 fixture 還原、Noto 安裝／還原及錯誤授權 SHA 拒絕。Noto 建置執行全部 9 項；其他來源跳過僅適用 Noto 的一項。歷史完整白名單與使用者修改／原檔 SHA 保護不放寬，測試只寫入 Artifacts。
- 測試副本曾出現一次 WinError 5 替換錯誤；備份與原檔完整，單獨再執行三個測試通過，原因未確認，見 deployment-notes.json。實際套用若受阻，保留備份與錯誤，不強制覆寫。
- 已確認原版用「訓練家類型＋姓名」顯示名稱，8 個博士姓名移除重複頭銜，劇情頭銜維持不變；11 個實際組合已核對。Claude 1 兩輪退回項目均已補正，但未發起第三輪驗收，尚無最終接受結論。
- 原版 Masked／Royal 將類型與姓名拆開，可能顯示「蒙面者 Royal」，列為實機待核項。
- 官方繁中名稱「精靈球」保留使用；禁止舊稱「精靈」獨立指稱寶可夢。人名採專用對照，避免將 Mark、Eva 等人名誤譯成介面或能力名稱。
- 字級調整屬預覽設定，尚未經遊戲畫面驗收。存檔相容性及語言切換流程亦未實測。
- Codex 翻譯與建立此 repo 時未呼叫付費翻譯 API，未啟動遊戲或修改玩家存檔；本機套用與實機驗收由 Claude 1 另行處理。

本專案不包含遊戲原版檔案與字型；權利屬各原權利人，為非官方中文化。
