# 維護方式

此工作副本已完成文字表，Claude 1 已套用本機並正在進行實機驗收，尚未完成實機驗收。來源維護於私人 repo https://github.com/NiceJobGuys/FireAsh-Translate-zh-TW ，分支 main；本階段不建立 Release 或 tag。

## 翻譯來源與優先順序

`translation-source/catalog.jsonl` 是原訊息表匯出；每個鍵由 section 與完整英文共同識別。同一句英文在招式、屬性或人名可能有不同含義，不跨 section 任意替換。

`translations/reference.jsonl` 使用 `source-manifest.json` 固定的 PokeAPI commit。寶可夢、招式、道具、特性與屬性採 zh-Hant；遊戲自訂或不在參考資料內的名稱另有來源與草稿對照。

具名批次的英文 JSONL 及譯文 JSON 以 `source_sha256`、固定順序與筆數配對。英文檔使用 LF，勿自行重排、改換行、插列或覆寫舊批次；需要新增文字時使用新的批次名稱。逐鍵對照 JSON 不需要同名 JSONL。早期 045、065 的未配對英文批次為已由句型處理或空白的舊匯出，不代表尚待翻譯。

```powershell
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\fire_ash.py' batch --section 0 --limit 200 --name 130-dialogue
```

現有已納入資料無待翻，但不能據此斷言遊戲所有顯示路徑都有譯文。勿為了建立新批次而重置譯文。更新遊戲時，先保存原基準並比對新檔，重新匯出後審閱新增鍵，不直接套用舊版完整腳本。

2026-10-31 新增 `tools/runtime_catalog.py`：用本機遊戲 Ruby AST 讀取真正解碼後的單／雙引號字串，再核對原查詢表；另外追蹤 PWC／Grandeur 訓練家對話、敵方強化說明、戰場訊息與有限組合的隊伍標題。`130`–`145-runtime-missing` 為固定來源／譯文批次，1,207 筆，來源變更時建置拒絕繼續。工具專用 section 103／104 分別追加至語言檔 ScriptTexts／Map0，原鍵與順序保持不變；不把它們當成新的遊戲 section。

新增鍵必須走人工翻譯與 `validate_pair`，不能把所有 Ruby 字串自動翻譯，避免修改圖檔路徑、內部名稱、價格或存檔識別碼。人物名稱的新對照、同名 Drake 與刻意保留項目見 `runtime-translation-notes.json`。新增條目的來源行數只對固定原版 SHA 有效。

## 術語與保留項目

同名人物以具體來源字串及 `contextual_terms` 對照。Drake 分為勇次與源治，Liza 分為紀珂與小南，Daisy 分為櫻花與奈奈美，Flint 分為大葉與武能。不得以單字全域替換處理。

`*-terms.json` 內的數字 section 對照僅作用於該分類；`all` 只適用已確認沒有歧義的完整文字。訓練家人名不套用一般介面標籤，避免 Mark、Eva 等誤譯。

原文保留有兩種：完整鍵保留列於 `translations/preserved.json`；譯文中夾用的暱稱、製作者名稱、檔名及縮寫，列於 `glossary.json` 的保留術語與實際用量。用量只計算已翻譯／已明確保留的文字，重疊術語不能相加。

九個對戰背景名稱必須保留原文，否則圖片資源會失聯。不得更動內部強化識別名稱、訊息 lookup keys、OrderedHash 順序、選單變數／取消索引／選項數或控制碼。

## 檢查與建置

```powershell
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\fire_ash.py' self-test
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\prepare_baseline.py'
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\fire_ash.py' build --game 'D:\Code\Lab Testing\Artifacts\data\fire-ash-work\original-baseline'
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\verify_ruby.py' --game 'D:\Code\Lab Testing\Artifacts\data\fire-ash-work\original-baseline'
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\test_runtime_missing.py'
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\font_preview.py'
python 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\test_install_preview.py' --source-game 'D:\Code\Lab Testing\Artifacts\data\fire-ash-work\original-baseline'
```

依序等待上一個程序成功，再執行下一個。`coverage.json`、`validation.json`、`runtime-coverage-validation.json` 及 `deployment-validation.json` 的語言檔雜湊必須一致，不能用舊報告證明新產物。

`build` 不寫入遊戲；只產生獨立語言檔、本機修改腳本、像素字型與完整 OFL 授權。原生 Ruby 使用遊戲 DLL 做資料與函式測試，不啟動 Game.exe。`verify_display.rb` 以原遊戲的 drawItem／文字函式錄下實際繪製呼叫，`font_preview.py` 再以 FreeType 重播、最近鄰輸出 1／2／4 倍圖；不可另手寫一層陰影代替原本三層。4 倍圖只是檢查放大，不是遊戲顯示模式；這仍不能代替 SDL 遊戲實機畫面。

上述建置與原生驗證指令須使用符合 `source-manifest.json` 的原版副本，不對目前正在實機驗收的已套用目錄重新匯出或建置。套用前的驗證報告保留當時 `installed=false` 等歷史狀態；不得為了配合目前狀態，手動改寫既有測試結果。

套用工具測試會在 `Artifacts\data\fire-ash-work\install-fixtures\` 與 `Artifacts\backup\fire-ash-zhtw-install-fixtures\` 留下有時間識別的測試證據；先前兩個副本已由 Claude 1 代為清理。不得把原版副本或備份放進 repo。

## 發布邊界

repo 僅收原文／譯文、術語、工具與文件；完整原版／修改後 Scripts.rxdata、語言二進位、字型、存檔與備份不 commit。改用 Fusion Pixel Font 12px zh_tw（OFL 1.1），台灣標準字形較符合本專案目標；兩版字寬與覆蓋相同，翻譯與 PokeAPI zh-Hant 術語不變。下載及授權核對見 `font-source.json`；來源副本仍置於 repo 外。

本機 mkxp 將 API 字級乘 0.9 後取整數；一般文字 `Font.size=27` 對應實際 24px，小字 `14` 對應 12px。不得直接把 API 改成 24，否則實際成為 21px 而偏離原生格線。中文繪製暫停人工粗體／斜體，完成後還原；英文模式不動字型或樣式。完整字集 12／24px 已驗證無灰邊，`solidFonts` 不啟用、`mkxp.json` 不列入套用。這個決定只針對本次固定雜湊的引擎與字型，升級後需重驗。

繁中模式停用三條一般文字路徑的三層陰影：`pbDrawShadowText`、`renderLineBrokenChunksWithShadow`、`drawSingleFormattedChar`；保留明確 outline 標記及英文模式的完整陰影呼叫序列。使用者選 A，本輪不加入 3 倍 UI／getter，也不改 Game.exe、mkxp.json 或 Game.ini。UI_Options／StartGame 必須維持原版，Graphics stub 必須保留 0.5..2.0 上限。原因見 [3x-engine-blocker.md](3x-engine-blocker.md)。驗證器失敗時應寫入 passed=false，不讓舊 PASS 看似仍有效。

使用者已決定 repo 維持私人。來源修改前先 `git pull --ff-only`，修改後檢查 `git diff`、`git ls-files`，確認只有可 diff 的文字、工具與文件，再 commit、push。README、排除規則與 repo 設定參照私人 CoA-Translate-zh-TW；不把 CoA 用於二進位包的 `translations/` 排除規則直接套用，本專案的 `translations/` 是必須追蹤的 JSON／JSONL 來源。

實機驗收尚未完成，本次只推送 main，不建立 Release、tag、workflow 或排程。後續發布與可見性變更需另行授權。遊戲套用、啟動與實機驗收由 Claude 1 處理，與來源維護分開。
