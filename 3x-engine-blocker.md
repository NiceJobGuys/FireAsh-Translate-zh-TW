# 3 倍顯示未納入本版

2026-10-31 使用者選擇 A：先交付無陰影版，保留原有顯示方式，先看實機效果。本版移除先前未生效的 3 倍選項、getter 與啟動讀回修改；不修改 Game.exe、mkxp.json、Game.ini，安裝範圍維持四檔。

## 已確認原因

本機 Game.exe SHA-256 為 `b8994af47f7c911c0550197ccd8566df4638b3b3c147807c33f45b2a06c6d6e0`。靜態檢查確認 `Graphics.scale=` 的原生 setter 會將倍率限制在 0.5..2.0；即使 Ruby 送入 3.0，仍會被裁成 2.0。

- Ruby binding wrapper：VA `0x140089c30`。
- 原生 setter：VA `0x140038b80`。
- VA `0x140038bd8` 讀上限 2.0，VA `0x140038be0` 執行 minsd。
- mkxp.json 的 defScreenW／defScreenH 是啟動視窗預設；遊戲啟動仍會經過 resize_screen 與上述 scale setter，單改這兩個值不能讓選單接受 3.0。

上游參考：https://github.com/mkxp-z/mkxp-z/blob/v1.2.2/src/graphics.cpp 。本機結論同時有執行檔靜態機器碼證據，不只靠上游版本推測。

## 驗證修正

先前 Graphics stub 沒有模擬 2.0 上限，造成 3 倍呼叫測試的 PASS 不足以證明實際支援。已保留 0.5..2.0 限制並加入回歸檢查；現在測試原有五個顯示選項、預設 1.5 倍與 2 倍啟動讀回。UI_Options／StartGame 與原版內容比對相同。

驗證器發生錯誤時會寫入 `validation.json` 的 `passed=false`，避免先前成功報告被誤當成當前結果。原先 local commit `3ad2cbc` 保留歷史，本輪以後續 commit 修正。

本版未新增 3 倍功能；4 倍預覽圖僅供檢查字形，不是可選的遊戲顯示倍率。日後若要重新處理 3 倍，須另確認修改範圍、備份還原與真正視窗驗證。
