# 補充：不經語言檔的英文顯示文字

2026-11-02 Claude 2 製作（Codex 額度用完，使用者直接交辦），已備份並套用至 `D:\Games\Pokemon Fire Ash\Pokemon Fire Ash 3.7`。

## 問題

原訊息表 pending=0，但遊戲有一批英文不經查表就直接顯示，所以語言檔再完整也看不到中文：

- 字面字串直接傳給顯示函式：戰鬥被動特性招牌（`pbShowAbilitySplash(user,false,true,"Sandy Brawn Gain")` 等 62 個）、場地效果選單、極巨團體戰／極巨大冒險的選項（Catch、Train、Details…）、天氣結束訊息、寶可夢箱子／淨化室提示。
- `_INTL(變數)` 查不到鍵：極巨大冒險的地形與陷阱訊息（`text1 = "{1} pushed you aside..."`）、場地效果訊息、地圖 47 對決台詞（`_I` → `_MAPINTL`）。
- 英文單字當 `_INTL` 參數代入：Dynamax／Gigantamax、Any／Legendary／Hard、Z 招式的 sharply／drastically、紀錄畫面的 - Veteran 等難度、Sync／Titan Challenge、梅洛耶塔「{1} Performance」的屬性名。
- 句中片段：寶可夢箱子搜尋的 `[Level_Filter_Applied]` 等篩選標記。

## 做法

- 對照表：`translations/extra-text.json`（text 195 筆、override 1 筆、patterns 3 條、fragments 5 筆）。與語言檔重複的鍵譯文必須相同；需要調整語序的才放 override（目前只有 Z 力量提升訊息）。
- 掛鉤：`tools/extra_text.rb`，由建置接在 `FireAsh_ZHTW_Runtime` 段尾，只在繁中模式生效，表外的文字原樣通過。
  - `_INTL`、`_MAPINTL`：表內的鍵先換成譯文，英文參數逐一對照。
  - `pbDrawTextPositions`、`pbDrawShadowText`、`drawTextEx`：要畫的字對照後再畫（被動特性招牌走這條）。
  - `Window_CommandPokemon` 的建構與 `commands=`、`Window_UnformattedTextPokemon` 的建構與 `text=`、`Window_AdvancedTextPokemon#setText`：用 prepend。選項陣列有變才回傳新陣列，呼叫端的原陣列不改。
- 掃描工具（唯讀）：`D:\Code\Lab Testing\Artifacts\scripts\fire-ash-untranslated\`，`scan.py` 用遊戲 Ruby 的 AST 列出 Scripts／PluginScripts 裡不在查表函式內的英文字串，`filter.py` 去掉程式識別字與語言檔已有的鍵，`scan_maps.py` 掃地圖事件腳本，`lookup.py` 查現有譯文。

## 刻意不處理

- 除錯、編輯器、Log、例外訊息、存檔轉換標題（玩家正常遊玩看不到）。
- Wonder Trade 隨機產生的外國訓練家名與寶可夢暱稱：交換後會寫進存檔，維持原 NPC 暱稱政策不改玩家擁有的寶可夢資料。
- Essentials 示範地圖殘留的人名（Triad 對手 Sophie、Tim，交換 NPC Doris 等）。
- 戰利品稀有度 Common／Rare 等是內部雜湊鍵，不顯示。

## 驗證

- `python -B -X utf8 tools/test_extra_text.py`（相容套件加 `--scripts <套件 Scripts.rxdata>`）：遊戲 Ruby 執行掛鉤，涵蓋缺鍵、地圖鍵、參數、override、patterns、fragments、選項／訊息視窗與三個繪字函式；英文模式不變；檢查 Scripts 之後與 Plugins 沒有重新 def 被 alias 的函式、也沒有 alias 被 prepend 的方法；與語言檔重複的鍵譯文一致。
- 既有 self-test、verify_ruby、test_runtime_missing、test_battle_ui、test_context_ui、test_npc_nicknames 通過（verify_ruby 與 test_context_ui 改為接受 runtime 段尾多一段 extra_text）。Noto 字型涵蓋對照表全部 464 個字。
- 未啟動 Game.exe，以上不是實機畫面驗收。

## 安裝與還原

- 純翻譯 Scripts：`55e4e8b7eeb2461f602a7a5c5285b97135bff150bb996fe50e45c5399299efe0`（三方合併的 base 為 `82e38745…`，即 NPC 暱稱版）。
- 相容套件：`D:\Code\Lab Testing\Artifacts\release\fire-ash-extra-text-compatible`，只改 `FireAsh_ZHTW_Runtime`，其他 403 段（含遊戲提示 MOD 第十一版、編輯器）逐位元保留。
- 安裝前 `96c19917…`，安裝後 `a8d08db45311bd3f3170d9129fd228ed9e6d35a1dc273f6afd5ae9b527538f49`；語言檔 `d4cc61cd…` 不變。
- 備份：`D:\Code\Lab Testing\Artifacts\backup\fire-ash-before-extra-text-20261102`。正常退出遊戲後可還原：

```powershell
python -B -X utf8 'D:\Code\Lab Testing\Artifacts\scripts\fire-ash-pokemon-editor\editor.py' restore --backup 'D:\Code\Lab Testing\Artifacts\backup\fire-ash-before-extra-text-20261102'
```

新增譯文時改 `translations/extra-text.json`，重新 build、跑 `test_extra_text.py`，再用 `merge_script_update.py` 合併；之後的翻譯更新 base 改用 `55e4e8b7…`。
