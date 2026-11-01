# 情境誤譯、插件漏翻與圖片文字修正

2026-11-01，依已安裝版檢查結果修正並直接備份套用。

## 修改內容

- 日期的 May 顯示「５月」，BattleTerrain 的 Misty 顯示「薄霧」。人物姓名仍是「小遙／小霞」，其他月份不變。
- 寄放盒桌布 Machine／Checks／Space 顯示「機械／格紋／宇宙」；Space 環境名稱也顯示「宇宙」。
- 新增 10 筆插件缺漏文字：讀取遊戲、無存檔／讀取失敗／刪檔確認、極巨大冒險的地圖／隊伍／離開選項及訓練提示、極巨化陰影編輯說明。
- 4 個直接呼叫 pbMessage 的插件提示改走既有翻譯表。極巨大冒險的選項只翻譯顯示副本，原英文陣列仍供 case 判斷，回傳索引、取消值、預設選項與 block 不變。
- 圖鑑專用屬性圖片 `Pokedex/icon_types`、命名介面的 `Naming/overlay_controls` 與 `Naming/icon_mode` 使用獨立快取副本繪製中文，保留原 PNG。命名介面的 BACK 依實際動作譯為「刪除」，ACTION 捷徑標示「跳至確定」。
- 編輯器已有的「設為一般顏色」保持不變；沒有再套用共用表內的舊誤譯。

實作在 `tools/context_ui.rb`、`tools/battle_ui.rb`；新翻譯與來源是第 147 批。`runtime_catalog.py` 現在也掃描已核對 SHA-256 的 PluginScripts，避免只掃主 Scripts 而漏掉插件。PluginScripts 檔案本身未改。

## 驗證

- 6,189 個主腳本／插件靜態查詢無缺鍵；1,217 筆補充譯文與原生 Ruby 查詢相符。
- 43,751 個文字位置通過原生 Marshal 讀取；404 個腳本區塊語法通過。
- `test_context_ui.py` 使用實際月份／桌布／場地方法，先重現五月誤譯再驗證修正；測試插件原選單程式的中英文共 10 個操作／取消分支、4 個直接提示、10 個新增鍵及控制碼。
- 173 個 CPU 畫面案例、1,358 次繪字檢查通過；包含載入 ZUD 的實際資料框／招式覆寫、原命名介面四種選取狀態。55 個英文畫面與原版像素相同，原始圖片與共享快取保持不變。這不是 Game.exe 實機畫面。
- 原有 32 個對話框、30 個選項視窗案例、11 項安裝／還原測試、5 項字型工具隔離測試通過。
- 原有語言鍵和值逐筆保持相同，只追加 10 個鍵。

報告：`validation.json`、`runtime-coverage-validation.json`、`context-ui-validation.json`、`battle-ui-validation.json`、`deployment-validation.json`。一般建置報告對應純翻譯腳本；context 報告與本機相容套件內的 battle 報告對應實際合併版本。

## 安裝與保留內容

- 遊戲：`D:\Games\Pokemon Fire Ash\Pokemon Fire Ash 3.7`。
- 實際安裝 Scripts SHA-256：`8797f8974ba4907a0f0507387c6d032cafa45bd75031da497222bf17ddb4674b`。
- 語言 SHA-256：`d4cc61cdd16be413cca6838f2f9d8401945bce6339e2586b5d918076af414edf`。
- 純翻譯 Scripts：`f5066d3c06bf9c433cdacf7965b8eafa08d20f14a8fe020845c243eefdb607db`。
- 相容套件：`D:\Code\Lab Testing\Artifacts\release\fire-ash-context-ui-compatible`，含合併 manifest、純翻譯基準與 installed.json 收據。
- 三方合併僅更換 FireAsh_ZHTW_Runtime；其餘 403 個區塊逐位元組保留，因此編輯器、地圖提示、相剋符號與能力畫面招式分類 MOD 保持原樣。
- PluginScripts、Game.exe、Game.ini、mkxp.json、字型、原 PNG 及 Save Files 套用前後雜湊相同。

## 還原本次更新

正常退出遊戲後依序執行；兩個工具都不會還原或覆蓋玩家存檔：

```powershell
python -B -X utf8 'D:\Code\Lab Testing\Artifacts\scripts\fire-ash-pokemon-editor\editor.py' restore --backup 'D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-context-ui-20261101'
python -B -X utf8 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\install_preview.py' restore --backup 'D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-plugin-text-20261101'
```

這會回到 Scripts `65816813…`、語言 `a1f89d69…`，仍保留先前的報名選單修正與既有 MOD。

## 限制

未啟動遊戲，尚待使用者在實際讀檔、圖鑑、命名與極巨大冒險流程驗收。本次處理上輪已確認問題，不宣稱全部劇情與所有圖片均已逐一驗收。未建立 Release 或 tag。
