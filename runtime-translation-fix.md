# 2026-10-31 執行時漏翻修正

Codex 已補譯 1,207 筆、建置並通過原生回歸；尚未套用或進遊戲實測。此次沿用前輪選定的 Noto Medium 建置設定，沒有變更字型、陰影、畫布或遊戲執行檔。

## 修正內容

- 1,206 個腳本查詢鍵及 1 個共用地圖查詢鍵，分別追加到繁中語言檔的 ScriptTexts 與 Map0。原來的 42,534 個欄位內容與順序均保留，新版共 43,741 個欄位。
- 收納道具、解毒、遺忘招式、被動能力的實際換行查詢鍵已有對應譯文，不再依賴原擷取器錯誤解碼的鍵。
- 補齊單引號訊息與動態資料：新遊戲、存檔、化石復活、奇蹟交換、世界錦標賽與俱樂部的訓練家台詞、四種戰場訊息、十項敵方強化說明、45 種可能的挑戰隊伍標題。
- 獨立選單 `command_102` 在繁中模式透過 `_MAPINTL` 顯示，原選項陣列、索引、取消值、分支均不修改；英文使用原資料。
- 八處直接提示（其中七處為開發／編輯工具）補 `_INTL`；敵方強化說明以已翻譯的選項名選擇正確分支；中文隊伍標題改用原繪字函式的置中對齊，英文座標維持原樣。

`tools/runtime_catalog.py` 以原生 Ruby AST 擷取實際字串，不執行遊戲腳本。來源批次 130–145 保留 SHA 與順序，建置重新擷取並比對；來源改變或缺譯時拒絕繼續。這是已檢查路徑的覆蓋，不宣稱任何 Ruby 字串都應翻譯。

## 驗證

- self-test：來源 SHA、控制碼、代入值、批次筆數、既有術語及字型檢查通過。
- 原生 Ruby：43,741 個欄位逐一比對、404 段腳本編譯、既有語言／排版／強化商店／英文回歸通過。
- 新增執行時測試：5,337 處含英文字母的固定 `_INTL`／`_ISPRINTF` 查詢零缺鍵；1,207 個新增原生值與譯文一致。
- 實際 `pbItemBall`／`pbReceiveItem` 方法透過無檔案操作的背包／訊息 stub 重現原英文，再驗證中文結果、取得數量與控制碼。
- 45 組獨立選單檢查中文、英文、順序、取消值、回傳分支與輸入不被修改。既有明確保留地名 Izabe 仍照術語政策保留。
- 十項敵方強化說明使用實際修改後的方法測試，中文與英文皆選中正確分支。
- 45 個標題組合檢查中文字串／置中座標及英文座標不變。三處缺漏地圖對話驗證 Map0 回退。
- 新台詞的具名發話者依既有 glossary 與新名稱筆記逐一比對，Drake 依訓練家類型區分源治與勇次。
- 安裝／還原 fixtures：9 tests OK，僅在 Artifacts 中操作；原三檔、四檔與正黑體備份還原規則維持。
- 既有字型預覽：41 張／418 字界通過。新語言檔 3,052 個 CJK 字元在 pixel／jhenghei／noto 字型均無缺字；這是 cmap 檢查，不是三版本遊戲實測。

主要報告：`coverage.json`、`validation.json`、`runtime-coverage-validation.json`、`deployment-validation.json`、`font-preview-validation.json`，語言與 Scripts SHA 一致。舊 `script-character-audit.json`、`trainer-title-audit.json` 是前輪語言 SHA 的歷史紀錄，不能拿來證明這批新譯文已經過相同的完整人工驗收。

## 套用檔

| 檔案 | SHA-256 |
| --- | --- |
| Data/Scripts.rxdata | `36d4bb0c44aa147f91b95b946ab13a783439fd900740d5cd0f1ac3fb18093171` |
| Data/traditional_chinese.dat | `259ee43ce16e5d24cc60a63eaea722e67657f8b8501ed8bf2476fc898696256d` |
| Fonts/fire-ash-zhtw.otf | `2905dd3de65d7b7de764596e2294978407986f4cc0a66c9584c5b95c5aa9572e` |
| Fonts/fire-ash-zhtw-OFL.txt | `6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2` |

這輪檢查後安裝目錄仍為舊正黑體：Scripts `19624fe4…`、語言 `bb8d8f7f…`。套用交接與完整本機命令位於 `Artifacts/docs/fire-ash/runtime-translation-handoff.md`。先核對現況、正常退出遊戲、依當前備份還原後才重新安裝，勿直接覆寫使用中的檔案。

## 限制與名稱來源

未啟動遊戲、未改玩家存檔、未發 Release／tag。原圖英文、未涵蓋的動態／公共事件路徑、實際劇情與存檔切換仍待實機驗收。四句原稿本身的 `PN` 缺反斜線，此次未擅自新增控制碼；自訂融合角色 `Luc-ker` 保留原名。

新補的人名以[《阿爾宙斯》官方角色頁](https://www.pokemon.co.jp/ex/legends_arceus/tc/character/)核對菊伊、阿芒、木春、濱廉；青葙與麥可參考 [Argenta 名稱表](https://bulbapedia.bulbagarden.net/wiki/Argenta)、[Buck 名稱表](https://bulbapedia.bulbagarden.net/wiki/Buck)，小進參考 [Trace 名稱表](https://wiki.pokemoncentral.it/Trace_%28gioco%29)。具體保留與同名例外見 `runtime-translation-notes.json`。
