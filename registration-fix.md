# 出賽隊伍報名選單誤譯修正

2026-11-01，使用者截圖中的「圖鑑說明」其實是 UI_Party 出賽隊伍選擇的 `Entry`；該分支把寶可夢加入出賽順序。已選擇寶可夢的 `No Entry` 分支則移除報名，原譯「無法報名」也不符合操作。

- `Entry`：圖鑑說明 → 報名參賽。
- `No Entry`：無法報名 → 取消報名。
- 來源：`translations/batches/146-party-registration-terms.json`，只覆寫訊息區段 24；移除 manual.json 的泛用 Entry 誤譯。

完整建置後對照已安裝語言檔，43,741 個文字位置只有上述兩筆不同，所有查詢鍵與其他區段的序列化內容不變。`test_runtime_missing.py` 使用原生 Ruby 與遊戲 `_INTL` 查詢，新增兩句回歸檢查並通過；self-test 通過。未啟動 Game.exe，實機畫面尚未驗收。

既有 `install_preview.py` 新增 `--expect-language-sha256` 單檔更新模式：要求現行語言 SHA、其他原版資料基準與字型吻合，仍使用原有備份、暫存校驗、原子替換及失敗還原流程；不部署 Scripts。11 項安裝測試全部通過，包括保留 MOD、原雜湊不符拒絕、單檔還原和中途複製失敗還原。

## 本次安裝

- 遊戲：`D:\Games\Pokemon Fire Ash\Pokemon Fire Ash 3.7`。
- 已安裝語言 SHA-256：`a1f89d694d5cbe2361aac24748501e031d3951dd23828404260a9302bc9ec1a8`。
- 原語言 SHA-256：`259ee43ce16e5d24cc60a63eaea722e67657f8b8501ed8bf2476fc898696256d`。
- Scripts 保持 `65816813a9c23c1aad3328803fe17b35aeda7c302d539017d5365da12f72d7c4`；PluginScripts、引擎、設定、字型及 Save Files 檔案套用前後雜湊一致。
- 備份：`D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-registration-20261101`；`manifest.json` 記錄單一語言檔，`installed.json` 記錄安裝後校驗。

正常退出遊戲後，可只還原本次兩句文字，保留 MOD 與存檔：

```powershell
python -B -X utf8 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\install_preview.py' restore --backup 'D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-registration-20261101'
```

後續純譯文更新可用 `plan`／`install --font-source noto --expect-language-sha256 <當時已安裝語言檔的完整雜湊>`。先比對語言差異與所需 Scripts 相容性；若需新增執行階段程式，不適用單檔更新模式。
