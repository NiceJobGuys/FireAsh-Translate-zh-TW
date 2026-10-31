# 2026-11-01 對話文字下緣裁切修正

已套用至 `D:\Games\Pokemon Fire Ash\Pokemon Fire Ash 3.7`，四檔校驗通過；未啟動遊戲，實機畫面待使用者確認。翻譯、字型、字級、文字座標與行距皆不變。

## 原因與最小修正

`Window_AdvancedTextPokemon#setText` 先以 32px 行框計算 `@bitmapheight`，隨後將每個字向下移 4px，卻未將位移納入緩衝區。單行 Noto 文字因而超出底部，單行或最後一行的下緣會被裁掉。換成大畫布的舊預覽沒有模擬這層對話窗 bitmap 裁切，所以未發現問題。

只修改 `SpriteWindow_text` 中非空白文字的緩衝區高度：繁中模式增加既有 4px 位移，並保留字型實際高度超出 32px 行框的餘量。Noto 24px 的測試字型高度為 35px，因此單行透明緩衝區由 32 增至 39px。字形不移動、行距仍為 32px；英文與空字串配置完全不變。

最初只增加 4px 時，截圖中的中文字已完整，但延伸的 `Pokémon gyjqp` 混排案例仍有 27 個像素被裁掉。因此改依執行時 `text_size("Ag").height` 預留餘量，不硬寫另一個僅適合此字型的偏移。

像素重播依 [mkxp Bitmap::drawText](https://raw.githubusercontent.com/Ancurio/mkxp/master/src/bitmap.cpp) 的垂直置中方式計算，使用 FreeType 字形並裁到原生 Ruby `setText` 真正計算出的 bitmap 尺寸。這是離線模型與原生 Ruby 函式測試，未宣稱直接執行本機 Game.exe／SDL 渲染。

## 驗證

- 先對未修正版本加入回歸，確認失敗；截圖同句「大木博士是寶可夢研究的頂尖專家。」重現 263 個筆畫像素被裁掉，修正後為 0。
- 28 個原生 setText 配置與像素案例：單行、雙行、三行、自動換行、混排、下伸筆畫與空字串，涵蓋逐字／一次顯示及英文／繁中。繁中案例零裁切，英文配置與呼叫完全相同，所有字的位置與換行不變。
- 43,741 個語言欄位、404 段腳本語法、既有排版／陰影／縮放／商店邏輯回歸通過。
- 1,207 筆補譯、5,337 處固定查詢、45 組獨立選單及十項強化說明回歸通過。
- 9 項安裝／還原測試通過；5 項樣本隔離測試通過。
- 樣本測試曾因前輪新增譯文後字數仍寫死 3,195 而失敗；已改為核對現行建置的 3,210 字，沒有放寬缺字檢查。三種樣本字型均零缺字。
- 與修復前安裝腳本逐段比對，只有 `SpriteWindow_text` 改變。語言檔、Noto 字型、授權、Game.exe、Game.ini、mkxp.json 雜湊均不變。

新增回歸：`tools/verify_window_buffer.py`，由既有 `tools/verify_ruby.py` 執行。證據：`text-buffer-validation.json`；失敗／執行中狀態會使本報告標為未通過，避免沿用舊 PASS。實驗字型樣本不覆寫正式報告。

## 安裝與備份

- Scripts SHA-256：`b150e3f53e088cdd3a3ec2e18a8c7d8540eefcac82421715326167a46b2e4401`。
- 語言 SHA-256：`259ee43ce16e5d24cc60a63eaea722e67657f8b8501ed8bf2476fc898696256d`（不變）。
- 現行有效備份：`D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-text-buffer-fix-20261101`。
- 前一份 `fire-ash-zhtw-before-runtime-translation-20261101` 已執行還原，不再是目前版本的 restore 入口。

```powershell
python -B -X utf8 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\install_preview.py' restore --backup 'D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-text-buffer-fix-20261101'
```

預覽是原生呼叫重播，不是實機截圖：

- `D:\Code\Lab Testing\Artifacts\images\fire-ash\text-buffer-fix\noto-before-3x.png`
- `D:\Code\Lab Testing\Artifacts\images\fire-ash\text-buffer-fix\noto-after-3x.png`

請以相同對話及含英文小寫的對話確認實機下緣。這輪不啟動遊戲、不改玩家存檔、不建立 Release／tag。
