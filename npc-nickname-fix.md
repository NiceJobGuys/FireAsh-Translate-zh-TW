# NPC 寶可夢暱稱漏翻修正

2026-11-02 已備份並套用至 `D:\Games\Pokemon Fire Ash\Pokemon Fire Ash 3.7`。

## 問題與範圍

使用者截圖中的 `Porygon Zero` 來自秋葉原博士的訓練家隊伍資料，並非物種名稱。原版及插件的 `GameData::Trainer#to_trainer` 直接把 `trainers.dat` 的 `:name` 指派給寶可夢，沒有經過訊息表，因此既有物種翻譯與靜態 `_INTL` 覆蓋檢查都抓不到。

盤點固定來源的 3,470 筆訓練家資料，共 250 個暱稱位置、216 種暱稱。本次翻譯 214 種，包括「多邊獸零號」「白滾滾」「小魔」「天然鳥一號／二號／三號」；`J A & M` 和 `D4C` 是明列保留的識別縮寫。譯文在 `translations/npc-nicknames.json`；除沿用可核對名稱外，其餘採本專案音譯或意譯，不宣稱全部是官方台灣譯名。

參考名稱核對：[小魔／Mimey](https://wiki.52poke.com/wiki/%E5%B0%8F%E9%AD%94)、[雷恩／Sparky](https://wiki.52poke.com/zh-hant/%E9%9B%B7%E6%81%A9)、[吉波／Zippo](https://wiki.52poke.com/wiki/%E5%90%89%E6%B3%A2)。本機 `trainers.dat` 是暱稱、物種與訓練家對應的直接來源，SHA-256 `4c8363de9c85ca9f573165f9daece46b7c8b939fea5160025c8fbd6d7b3fb621`。

`tools/npc_nicknames.rb` 只在繁中模式建立 NPC 隊伍後處理固定暱稱。沒有全域替換 `Pokemon#name`，玩家自訂暱稱、未知暱稱及英文模式維持原樣。ZUD、Randomized Trainer Teams 會在主腳本之後重新定義 `to_trainer`，因此用 prepend 接在最後實際方法外層；本機全部來源已檢查，沒有後續 alias 此方法。

此對照只適用 NPC 隊伍資料，不覆寫舊劇情對話中先前保留的拼字。一般訊息表與靜態查詢也重新檢查，但不宣稱已逐一驗收全部地圖、動態文字及圖片。另掃描本機地圖事件的固定 `.name =` 腳本指派，未發現其他字面值指派。

## 驗證結果

- 在遊戲原生 Ruby DLL 中先重現 `Porygon Zero`，再測試修正與實際插件載入順序。
- 原版、ZUD、RTT 三條實際建隊方法各跑全部 3,470 筆資料、250 個暱稱位置；以相同亂數種子核對隊伍，除名稱以外的物種、等級、招式、道具、IV／EV、特性、極巨化欄位等序列化資料完全相同。
- 214 筆譯文與 2 筆保留項目完整對應來源；未知名稱及玩家自行命名的 `Porygon Zero` 不變，Noto 字型零缺字。
- 43,751 個訊息位置、404 個腳本語法、6,189 個主程式／插件靜態查詢與 1,217 個補充譯文檢查通過。
- 32 個對話框、30 個選項視窗、173 個 CPU 畫面案例及 11 項安裝／還原測試通過；55 個英文畫面與原版逐像素相同。
- 未啟動 Game.exe，以上不是實機畫面驗收。

建隊回歸執行原版／插件原始方法，寶可夢物件與周邊服務使用記錄欄位的測試替身；不是完整引擎或實際對戰模擬。

回歸指令：

```powershell
python -B -X utf8 'D:\Code\Lab Testing\Artifacts\data\fire-ash-translate-zh-tw\tools\test_npc_nicknames.py' --scripts 'D:\Games\Pokemon Fire Ash\Pokemon Fire Ash 3.7\Data\Scripts.rxdata'
```

## 安裝與還原

- 相容套件：`D:\Code\Lab Testing\Artifacts\release\fire-ash-npc-nicknames-compatible`，內含 `manifest.json`、`installed.json` 與畫面回歸報告。
- 備份：`D:\Code\Lab Testing\Artifacts\backup\fire-ash-before-npc-nicknames-20261102`。
- 安裝前 Scripts：`f39b440f722465cf8eb6230c6997aebc33d22ef5e9864d67adcac9bc0b93db07`。
- 安裝後 Scripts：`7d75d0c1e6e2858548fff4624cd60b8188b23a39fa40c6cf523f9177c9e65b04`。
- 純翻譯 Scripts：`82e3874508437d8c77f5a4292934cd7b7cb09469f86f6460ebdfed01959764a7`。

三方合併只改 `FireAsh_ZHTW_Runtime`，其他 403 個區塊逐位元保留，包括編輯器 v5、EV 修正與遊戲提示 MOD 第八版。沿用既有 `editor.install` 的單腳本套用流程及其引用的 `install_preview.py` 退出檢查、備份路徑與雜湊驗證；沒有還原舊版全套翻譯。套用後 21 個非腳本檔案雜湊不變，包含存檔、字型、語言檔、trainers.dat、PluginScripts、Game.exe／Game.ini／mkxp.json。

正常退出遊戲後，可用既有工具撤銷本次腳本更新；還原會保留提示 MOD 第八版，不修改玩家存檔：

```powershell
python -B -X utf8 'D:\Code\Lab Testing\Artifacts\scripts\fire-ash-pokemon-editor\editor.py' restore --backup 'D:\Code\Lab Testing\Artifacts\backup\fire-ash-before-npc-nicknames-20261102'
```

後續若遊戲又有其他腳本更新，工具會拒絕直接覆蓋，須重新合併。未建立 Release 或 tag。

## 本輪測試暫存

清理下列三個本輪產生的測試目錄時，Codex 工具政策回覆 `blocked by policy`，未提供更細的理由；沒有執行刪除或改寫命令重試。不影響已完成的安裝，正式套件與還原備份也不在清理範圍。三個完整目標已確認位於本專案 Artifacts 內，且不是連結；如需手動清理，可在 PowerShell 7 執行：

```powershell
Remove-Item -LiteralPath 'D:\Code\Lab Testing\Artifacts\data\fire-ash-work\install-fixtures\run-20261102-144111-007829','D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-install-fixtures\run-20261102-144111-007829','D:\Code\Lab Testing\Artifacts\images\fire-ash\npc-nicknames' -Recurse -Force
```
