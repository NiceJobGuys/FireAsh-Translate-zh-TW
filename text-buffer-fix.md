# 2026-11-01 對話文字下緣裁切修正

後續選項裁切修正已併入並套用，現在使用 [command-window-fix.md](command-window-fix.md) 的版本與備份。下方保留本輪對話修正過程；此處原備份已執行還原，不再是目前版本的還原入口。

已套用至 `D:\Games\Pokemon Fire Ash\Pokemon Fire Ash 3.7`，四檔校驗通過；未啟動遊戲，實機畫面待使用者確認。翻譯、字型、字級、水平位置、行距與視窗大小不變；Noto 對話文字相對原版向上移 6 個原生像素，使完整筆畫落在每行內。

## 原因與最小修正

`Window_AdvancedTextPokemon#setText` 先以 32px 行框計算 `@bitmapheight`，隨後將每個字向下移 4px，卻未將位移納入緩衝區。單行 Noto 文字因而超出底部，單行或最後一行的下緣會被裁掉。換成大畫布的舊預覽沒有模擬這層對話窗 bitmap 裁切，所以未發現問題。

使用者回報「第一行正常，第二行仍裁切」後，確認上一版只修正內部 bitmap；`SpriteWindow#privRefresh` 仍以 `@height-trimHeight` 限制 contents sprite 的 `src_rect`。96px 對話窗扣掉 32px 邊緣，兩行可見範圍只有 64px，放大 bitmap 仍會在這一層裁切。先新增此外層測試，確實讓上一版失敗後才修正。

最終移除放大 bitmap 的補丁，改讓文字真正落在每個 32px 行框：繁中對話的垂直位移取 `min(4, (32-font_height)/2)`，`font_height` 由執行時 `text_size("Ag").height` 取得。Noto 高度 35px 時位移從 +4 變成 -2，因此上移 6px。英文仍為 +4；圖示的位移不小於 0，避免 32px 圖示頂部被裁。單行 bitmap 回到 32px，雙行 64px，視窗及分頁行數保持原值。

像素重播依 [mkxp Bitmap::drawText](https://raw.githubusercontent.com/Ancurio/mkxp/master/src/bitmap.cpp) 的垂直置中方式計算，使用 FreeType 字形，先裁到原生 Ruby `setText` 真正計算出的 bitmap，再透過從實際 `SpriteWindow` 擷取的 src_rect 程式碼檢查可見範圍。這是離線模型與原生 Ruby 函式測試，未宣稱直接執行本機 Game.exe／SDL 渲染。

## 驗證

- 先對未修正版本加入回歸，確認失敗；截圖同句「大木博士是寶可夢研究的頂尖專家。」重現 263 個筆畫像素被裁掉，修正後為 0。
- 32 個原生 setText 配置與像素案例，新增使用者第二張截圖的兩行內容；每例檢查內部 bitmap 及 64px 可見區域，涵蓋捲動 0／32px。繁中案例零裁切且無上一行殘留；英文配置與呼叫完全相同，水平排版與換行不變。
- 第二張截圖文字在舊配置有 229 個筆畫像素缺失，修正後為 0。3,207 個可顯示字元逐字檢查垂直字界，皆位於行框；另有 8 個 24／32px 圖示位置案例通過。
- 43,741 個語言欄位、404 段腳本語法、既有排版／陰影／縮放／商店邏輯回歸通過。
- 1,207 筆補譯、5,337 處固定查詢、45 組獨立選單及十項強化說明回歸通過。
- 9 項安裝／還原測試通過；5 項樣本隔離測試通過。
- 樣本測試曾因前輪新增譯文後字數仍寫死 3,195 而失敗；已改為核對現行建置的 3,210 字，沒有放寬缺字檢查。三種樣本字型均零缺字。
- 與修復前安裝腳本逐段比對，只有 `SpriteWindow_text` 改變。語言檔、Noto 字型、授權、Game.exe、Game.ini、mkxp.json 雜湊均不變。

新增回歸：`tools/verify_window_buffer.py`，由既有 `tools/verify_ruby.py` 執行。證據：`text-buffer-validation.json`；失敗／執行中狀態會使本報告標為未通過，避免沿用舊 PASS。實驗字型樣本不覆寫正式報告。

## 安裝與備份

- Scripts SHA-256：`902ca39867fd6fc7e542fc1b0b912f73e746f0b398ea5921b93d3485373f6d72`。
- 語言 SHA-256：`259ee43ce16e5d24cc60a63eaea722e67657f8b8501ed8bf2476fc898696256d`（不變）。
- 現行有效備份：`D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-viewport-fix-20261101`。
- 前一份 `fire-ash-zhtw-before-text-buffer-fix-20261101` 已執行還原，不再是目前版本的 restore 入口。

```powershell
python -B -X utf8 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\install_preview.py' restore --backup 'D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-viewport-fix-20261101'
```

預覽是原生呼叫重播，不是實機截圖：

- `D:\Code\Lab Testing\Artifacts\images\fire-ash\text-buffer-fix\noto-before-3x.png`
- `D:\Code\Lab Testing\Artifacts\images\fire-ash\text-buffer-fix\noto-after-3x.png`
- `D:\Code\Lab Testing\Artifacts\images\fire-ash\text-buffer-fix\noto-two-lines-before-3x.png`
- `D:\Code\Lab Testing\Artifacts\images\fire-ash\text-buffer-fix\noto-two-lines-after-3x.png`

請以相同對話及含英文小寫的對話確認實機下緣。這輪不啟動遊戲、不改玩家存檔、不建立 Release／tag。
