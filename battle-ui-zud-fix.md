# 2026-11-01 性別圖示被 Lv. 蓋住：真正原因是 ZUD Plugin

使用者在 `105ea77f…` 版實機截圖仍看到 ♂ 疊在 Lv. 上，而且 ♂ 邊緣有反鋸齒，Lv. 是硬邊像素圖，代表畫面上的 ♂ 不是 14×14 像素圖示而是字型字形。

## 原因

`Data/PluginScripts.rxdata` 的 ZUD Plugin（`[004] Battle Core/UI Databox.rb`）重新定義 `PokemonDataBox#refresh`。Essentials 19.1 在 Scripts 之後才載入 Plugins，所以遊戲實際執行的是 ZUD 版，它仍以字型在 `spriteBaseX+126` 畫 ♂／♀，與 `spriteBaseX+140` 的 Lv. 重疊。前幾輪只修改 Scripts 內 `PokeBattle_SceneElements` 的 `refresh`，在遊戲中從未執行；`test_battle_ui.py` 也只載入 Scripts 版，所以一直顯示通過。

同一個 ZUD `refresh` 另有凍結風險：名字寬度超過 122px 時會以 `font.size -= 1` 縮字，但繁中模式的 `Font#size=` 會把 26 吸回 27，迴圈永不結束。物種名最長 5 字（120px）不會觸發，10 個英文字母的暱稱（例如 Charmander）約 130px 就會讓戰鬥畫面卡死。隊伍、能力、電腦箱子的名字縮字迴圈（`UI_Party`、`UI_Summary`、`UI_PokemonStorage`）也是同一個原因。

## 修正

- `tools/battle_ui.rb`：以 `prepend` 掛上 `PokemonDataBox`，攔截資料框自己的 `pbDrawTextPositions`。名字改用既有的 `fit_ui_text`（104px），♂／♀ 改畫既有的 14×14 圖示於 `spriteBaseX+118`。prepend 的方法排在類別之前，所以之後 ZUD 再定義 `refresh` 也不影響；不改 PluginScripts.rxdata，套用仍只動 Scripts.rxdata。英文模式與 Max Raid 的白名字不攔截。
- `tools/font_support.rb`：同一個縮小請求重複出現（縮字迴圈卡住）時，退到下一個像素字級（27→14），14 以下不再吸附。單次請求維持原本吸附（例如 Voltorb Flip 的 `font.size=26` 仍是 24px）。遊戲腳本沒有直接設定小於 14 的字級。
- Scripts 內 `PokeBattle_SceneElements` 的舊補丁在遊戲中不會執行，本次未刪除。

## 測試

- `test_battle_ui.py` 改照遊戲順序載入：Scripts 的 `PokemonDataBox`、`FireAsh_ZHTW_Runtime`，再載入 ZUD 的 `refresh`；英文原版對照也同樣載入 ZUD。用舊 `battle_ui.rb` 跑會在性別圖示斷言失敗（重現使用者截圖），新版 152 個畫面、10 個性別圖示未遮擋、48 個英文畫面逐像素一致。
- `verify_ruby.py` 新增縮字迴圈斷言：`Charmander` 依序 27、14、13、12 結束。已安裝的舊字型程式在同一迴圈停在 27（會凍結）。
- self-test（noto）、verify_ruby、test_runtime_missing 全過。仍是 CPU 重播，不能代替 Game.exe 實機。

## 合併與套用

安裝目錄的 `FireAsh_ZHTW_Font` 另含寶可夢編輯器 `layout_patch.py` 追加的 `layout_support.rb`，`merge_script_update.py` 因雙方都改同一段而拒絕合併。本次先確認「舊純翻譯 + 編輯器追加」與安裝版逐字相同，再把同一追加套在新建置上做三方合併（`Artifacts\scripts\fire-ash-databox\layer_editor_font.py`）。之後只要字型段有改，都要這樣處理，不能直接用純翻譯段覆蓋。

| 產物 | SHA-256 |
| --- | --- |
| 純翻譯建置（noto） | `d7db84b9a3b67945ae1afc67a7ad845e41f6588836cf00be8783d66d6eca91ac` |
| 安裝版（合併編輯器 v5） | `1606fde755b5a64ac7f0429145dfaa5f71ab33c4a37a4edaa36a8f9c3490f825` |
| 語言檔（不變） | `259ee43ce16e5d24cc60a63eaea722e67657f8b8501ed8bf2476fc898696256d` |

合併只更新 `FireAsh_ZHTW_Font`、`FireAsh_ZHTW_Runtime`，其餘 402 段逐位元相同，404 段皆可編譯。套件 `D:\Code\Lab Testing\Artifacts\release\fire-ash-zud-databox\`，其中 `translation-base.rxdata` 是純翻譯建置，供下次三方合併。套用後 Game.exe、Game.ini、mkxp.json、語言檔、字型、PluginScripts.rxdata 與 Save Files 雜湊皆未變。

正常退出遊戲後，如需回到上一版：

```powershell
python -B -X utf8 'D:\Code\Lab Testing\Artifacts\scripts\fire-ash-pokemon-editor\editor.py' restore --backup 'D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-zud-databox-20261101'
```

## 後續：招式名（同日，使用者同意）

ZUD 的 `FightMenuDisplay#refreshButtonNames` 同樣覆寫了 Scripts 版，招式名的 `fit_ui_text` 補丁在遊戲中沒有生效；PP 所在的 `refreshMoveData` 未被覆寫，PP 修正一直有效。

- `tools/battle_ui.rb` 以 prepend 攔截 `FightMenuDisplay` 畫到 `@overlay` 的文字，依座標對回按鈕後用 `fit_ui_text` 畫進按鈕內框。顏色沿用 ZUD 依屬性取的顏色（舊 Scripts 補丁固定用 `TEXT_BASE_COLOR`）。
- 測試同時載入 ZUD 的 `refreshButtonNames`；招式案例改含 7 字的「超極巨萬雷轟頂」。上一版 `battle_ui.rb` 會在 `fight-1-0-0` 的按鈕邊界斷言失敗，新版通過（152 畫面、48 英文畫面逐像素一致）。
- 純翻譯建置 `58203dfeef9daeaf612a5a0ede3f4d7ebc1301c7bb8ebf6ec7c834beaa0e31fc`；安裝版 `348ad26bb2ee7181d9ad92622bae3e2073c1344ff58a5533f02e98aba6fdbb50`，只改 `FireAsh_ZHTW_Runtime`，其餘 403 段不變。字型段這次沒改，合併工具直接保留編輯器追加段。
- 套件 `D:\Code\Lab Testing\Artifacts\release\fire-ash-zud-fight-menu\`；現行備份 `D:\Code\Lab Testing\Artifacts\backup\fire-ash-zhtw-before-zud-fight-menu-20261101`（還原回 `1606fde7…`，用法同上）。
