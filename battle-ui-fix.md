# 2026-11-01 戰鬥 UI 圖片翻譯與欄位修正

後續實機發現性別／PP 仍遮擋，已由 [battle-ui-spacing-fix.md](battle-ui-spacing-fix.md) 補正並套用；本頁為前版紀錄，最新版本與備份以補正文為準。

已套用至 `D:\Games\Pokemon Fire Ash\Pokemon Fire Ash 3.7`。安裝版保留目前的寶可夢編輯器 v5、特性介面與超上限 EV 結算修正；未啟動遊戲，修正版實機畫面待使用者確認。

## 本次範圍

- 戰鬥指令圖：12 列、各兩種選取狀態，顯示「戰鬥／寶可夢／背包／逃跑／呼喚／投球／扔石頭／誘餌／取消／加油／場地」。投球對應兩個原圖列。
- 共用屬性圖：19 列由 `GameData::Type.name` 取得現行語言名稱，Electric 顯示「電」。透過同一個圖片載入入口，戰鬥、能力資訊、寶可夢盒子、招式回憶與三合一紙牌等使用此圖的介面一起取得中文圖示。
- 四種行動按鈕圖及 SHIFT SPECIAL 圖：改顯示「行動」與「特殊切換」，保留原圖案、選取狀態與按鈕邊框。
- 招式名稱改在各自按鈕內的安全矩形置中，採高對比文字，保持文字 overlay 位於按鈕之上。
- PP 標籤與數字分欄，正常數值保持大字；較長數值才縮小，避免文字跨出右側資訊框。
- 名稱固定在姓名欄位內，過長時改用小字，仍過長才加省略號；只影響顯示，不改寶可夢的名字。性別符號使用獨立的小字欄位，不再壓到 Lv. 圖示。姓名字界保留在 HP／狀態圖示上方。

原 PNG 不修改。`RPG::Cache.load_bitmap` 僅針對 7 個明確指定的 UI 圖，在繁中模式建立獨立副本並畫上中文；英文直接使用原快取。其餘圖片不受影響。副本依遊戲既有 refcount／dispose 管理，繪製失敗時釋放副本，字型狀態在成功或失敗後均還原。

PIKA 來自寶可夢名稱欄位，未作為介面字串替換。HP、PP、Lv. 保留原有縮寫。

## 驗證

`tools/test_battle_ui.py` 載入真正的 `CommandMenuDisplay`、`FightMenuDisplay`、`PokemonDataBox`，以 CPU 後端記錄 bitmap 繪製與 sprite 座標／裁切／z-order，再以 FreeType 合成。

- 純翻譯候選版與實際合併安裝版均通過 **140 個畫面案例、1,010 次文字繪製**。包含五種戰鬥指令模式、四個選取位置、PP 0／14／99、男女／無性別、等級 2／100、長名稱與各翻譯圖集。
- 44 個英文畫面與原版類別重播結果逐像素相同。
- 招式字界位於各自按鈕內，PP 字界位於資訊框內；性別不越過等級欄，姓名不進入下方圖示區。招式文字層的 z 值高於所有按鈕。
- 原始圖片檔與原始快取像素不變；繁中副本共用、英文快取隔離、失敗時副本釋放及字型狀態還原均有回歸。
- 43,741 個語言欄位、404 段腳本語法、既有 32 個對話與 30 個選單案例、1,207 筆補譯、45 組獨立選單、十項敵方強化說明均通過。
- self-test、9 項安裝／還原測試、5 項樣本隔離測試通過。

這些是原生 Ruby 類別與 CPU 圖層重播，不是 Game.exe 截圖。未宣稱全遊戲所有 UI 已無英文；未出現的自訂畫面仍待實機驗收。

## 與現有編輯器合併

安裝前發現遊戲已是編輯器 v5，SHA `3dd29e7d…`。未執行舊漢化的 restore，也未修改舊 manifest。

使用 `tools/merge_script_update.py` 進行三方比對：共同基準為編輯器第一版備份中的 `4d1dd01d…`，候選為本次純翻譯建置，現況為已安裝編輯器 v5。雙方同時修改同一腳本時工具會拒絕；本次沒有衝突，只替換 `PokeBattle_SceneElements`、`PokeBattle_SceneMenus`、`FireAsh_ZHTW_Runtime` 三段，其他 **401 段完整保留**。合併檔再經原生 Marshal／404 段語法及完整戰鬥 UI 測試。

套用沿用本機既有 `editor.install(game=...,package=...,backup=...)` 函式，其內使用相同的關閉遊戲、備份路徑及雜湊檢查。只更新 Scripts.rxdata，先備份目前腳本與 Save Files，失敗會回復。安裝後檢查存檔、語言、字型、Game.exe、Game.ini、mkxp.json 皆未變。

| 產物 | SHA-256 |
| --- | --- |
| 純翻譯建置 Scripts | `aedc301c215339e398a69e500a577f48290616fff0907d1b070268c9d3726613` |
| 實際安裝的相容合併 Scripts | `2469c484364264a3b630a42196893b712fc30ceadb29fc07e6dedecb08df80be` |
| 語言檔（不變） | `259ee43ce16e5d24cc60a63eaea722e67657f8b8501ed8bf2476fc898696256d` |

純翻譯報告位於 repo 的 `battle-ui-validation.json`；合併安裝版報告位於 `D:\Code\Lab Testing\Artifacts\release\fire-ash-battle-ui-compatible\battle-ui-validation.json`。兩個 SHA 不同是因安裝版包含另外的編輯器功能，不可混稱為同一產物。

## 備份、後續更新與還原

現行有效備份：`D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-battle-ui-fix-20261101`。

合併套件：`D:\Code\Lab Testing\Artifacts\release\fire-ash-battle-ui-compatible\`，含 Scripts、manifest、合併版驗證報告，以及供下次三方合併使用的純翻譯基準 `translation-base.rxdata`。**後續翻譯更新不得直接用純翻譯包覆蓋編輯器版本**；應以上次純翻譯基準、新建置與目前安裝三方合併，衝突時先檢查。

要撤銷這次 UI 更新、回到原編輯器 v5，正常關閉遊戲後使用：

```powershell
python -B -X utf8 'D:\Code\Lab Testing\Artifacts\scripts\fire-ash-pokemon-editor\editor.py' restore --backup 'D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-battle-ui-fix-20261101'
```

這份備份是單檔相容更新格式，應使用上述工具；不是 `install_preview.py restore` 的四檔 manifest。還原只回復腳本，不回復或覆蓋玩家進度。

合併版離線預覽：`D:\Code\Lab Testing\Artifacts\images\fire-ash\battle-ui-compatible\`。未建立 Release／tag，原遊戲檔與原圖未上傳。
