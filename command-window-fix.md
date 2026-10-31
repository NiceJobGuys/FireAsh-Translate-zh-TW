# 2026-11-01 選項裁切與游標對齊修正

已備份並套用至 `D:\Games\Pokemon Fire Ash\Pokemon Fire Ash 3.7`，四檔 SHA 校驗一致；未啟動遊戲，實機畫面待確認。翻譯、字型檔、字級、選項順序與取消行為不變。

## 原因與修正

使用者的 PC 選單由 `UI_PC → pbShowCommandsWithHelp → Window_CommandPokemonEx` 顯示。其共用 `pbDrawShadowText` 仍固定將文字往下移 4px，但游標在原列位置；Noto 的字型高度較高，導致字比箭頭低、最後一列超過 bitmap／contents src_rect 的底部。前輪僅修正對話的 `setText`，沒有涵蓋這條選單繪字路徑。

- 對話與選單共用 `FireAshZHTW.row_text_offset(bitmap,height)`，繁中依行框與實際字型高度計算偏移。Noto 的 32px 列從 +4 改為 -2，文字上移 6px；英文保留 +4。
- 一般選單直接使用修正後的共用 painter，PC 四列視窗大小與箭頭位置均不變。
- 格式化選單的 `resizeToFit` 原本無條件減少 6px 高度，會截斷最後一列；繁中取消這項減高，英文維持原狀。雙欄最後項目原本甚至可能不進入繪製迴圈，恢復完整列高後可正常顯示其游標。
- 格式化文字套用同一個垂直偏移，內嵌圖示不向上移出行框。前輪對話修正改為呼叫同一個 helper，行為不變。

## 驗證

- 以原生 `getAutoDims`、`resizeToFit`、`itemRect`、`refresh`、`drawItem`、`drawCursor` 與真實 contents src_rect 程式碼重播；箭頭使用本機 `selarrow.png`，不是另畫假游標。
- 使用截圖四個選項重現 43 個筆畫像素被裁掉；修正後為 0。每個選取項目的文字字界中心與箭頭中心差距不超過 2 個原生像素。
- 30 個選單案例通過：英文／繁中 × 一般／進階純文字／格式化選單 × 第一列／最後列／捲動／雙欄／英文下伸筆畫。英文呼叫與幾何配置逐項保持原值。
- 前輪 32 個對話雙層裁切與捲動案例、8 個圖示案例通過。測試中的 TEXTPADDING 改從實際 SpriteWindow 來源擷取（4px），不再硬寫 16px。
- 43,741 個語言欄位、404 段腳本語法、5,337 處固定查詢與 1,207 個補譯項目驗證通過；45 組獨立選單與十項敵方強化說明回歸通過。
- self-test、9 項安裝／還原測試、5 項樣本隔離測試與既有 41 張字型預覽檢查通過。

新測試：`tools/verify_command_window.py`，由 `tools/verify_ruby.py` 執行。證據：`command-window-validation.json`，並受樣本隔離測試保護。像素部分為 FreeType 離線重播，並非 Game.exe 實機截圖；不同選單皮膚與未覆蓋的自訂介面仍需實機確認。

## 已安裝版本

- Scripts SHA：`4d1dd01da2cad21f3c4edc88990b2a8bf336d14b6f268854e367ffccf1b657c8`。
- 語言 SHA：`259ee43ce16e5d24cc60a63eaea722e67657f8b8501ed8bf2476fc898696256d`（不變）。
- 字型、授權、Game.exe、Game.ini、mkxp.json 雜湊均不變，未改玩家存檔。
- 現行有效備份：`D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-command-window-fix-20261101`。
- 前一份 `fire-ash-zhtw-before-viewport-fix-20261101` 已還原，不再作為目前版本的 restore 入口。

```powershell
python -B -X utf8 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\install_preview.py' restore --backup 'D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-command-window-fix-20261101'
```

離線預覽：`D:\Code\Lab Testing\Artifacts\images\fire-ash\command-window-fix\noto-before-2x.png`、`D:\Code\Lab Testing\Artifacts\images\fire-ash\command-window-fix\noto-after-2x.png`。
