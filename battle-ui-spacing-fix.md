# 2026-11-01 性別與 PP 遮擋補正

使用者回報上一版仍遮擋。已先核對安裝檔 SHA 為上一輪 `2469c484…`，截圖也顯示新版中文屬性圖，確認不是沒有套用；先前修正／驗證不足。

本版已重新套用，安裝 SHA `105ea77f2389826529cf8caaac086c36c33ab8e46299784d13251796232d3da7`。未啟動遊戲，實機效果仍待確認。

## PP：由原圖像素驗證真正邊界

前測試容許文字到 x=504，但 `overlay_fight.png` 的白色內部實際是 `[402,494)`。對已安裝舊版加入正確邊界斷言後，實際重現 `14/15` 字界為 `(434,52,499,76)`，超出白底 5px。

現在 PP 標籤放在 `(404,46,20,32)`，數字放在 `(424,46,68,32)`；包含使用者截圖的 `30/30`。測試先由原圖白色像素確認內框，再檢查數字，不再把灰色邊框算成可用區域。

## 性別：移除字型尺寸的不確定性

實機性別字形與先前的字型重播結果不一致，尚未獨立定位引擎字形差異的底層原因。因此不再靠該字型的估算寬度解決，而是以程式繪製固定 **14×14** 像素性別圖示，與原 Lv.／HP 的像素 UI 一致。

圖示放在 `spriteBaseX+118,16`，Lv. 原圖從 `spriteBaseX+140` 開始，兩者保留 8px。名字欄寬度由 112 改為 104px，和性別欄也有間隔；不改寶可夢的實際名稱。男女顏色維持原設定，無性別不畫圖示。

測試檢查每個圖示的非透明像素在最終圖層合成後仍完整存在，避免僅檢查字寬卻漏掉後畫的 Lv. 圖片覆蓋。

## 驗證及相容性

- 純翻譯與合併版均通過 152 個畫面案例；新增 PP 30/30、實際白底邊界，以及 10 個性別圖示逐像素未遮擋案例。
- 48 個英文畫面與原版重播逐像素一致；既有文字、對話、選單、9 項安裝／還原及 5 項樣本隔離測試通過。
- 三方合併只更新三個 UI 腳本，另外 401 段保持原樣，包含寶可夢編輯器 v5／EV 結算修正。
- 安裝後核對 Scripts SHA 與備份 manifest 相符，Save Files 各檔雜湊不變。
- 測試仍是原生 Ruby 類別與 CPU 圖層重播，不能替代 Game.exe 實機驗收。

## 產物與還原

- 純翻譯 Scripts SHA：`64be03f8c9fc782228e9d940768972cd5ed46ad31d43b2e90fcc1111ac6de779`。
- 合併安裝版 Scripts SHA：`105ea77f2389826529cf8caaac086c36c33ab8e46299784d13251796232d3da7`。
- 合併包／本次純翻譯基準：`D:\Code\Lab Testing\Artifacts\release\fire-ash-battle-ui-spacing\`。
- 現行備份：`D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-battle-spacing-20261101`。
- 合併版離線圖：`D:\Code\Lab Testing\Artifacts\images\fire-ash\battle-ui-spacing\box-1-1-0-2-3x.png` 與 `fight-1-1-30-3x.png`。

正常退出遊戲後，如需回到前一版 UI：

```powershell
python -B -X utf8 'D:\Code\Lab Testing\Artifacts\scripts\fire-ash-pokemon-editor\editor.py' restore --backup 'D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-battle-spacing-20261101'
```

只還原腳本，不覆蓋後續存檔。未發布 Release／tag。
