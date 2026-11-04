# Fire Ash 3.7 繁中與額外功能 EXE

版本：`3.7-extras.2`（取代 `.1`：修正遊戲檔為唯讀時安裝失敗後無法還原）。Windows 10／11 x64，單一 EXE，內含 Python、Tk 與差分套用程式；玩家不需自行安裝 Python、PowerShell 7 或額外套件。目前以 Windows 11 x64 驗證，未在乾淨 Windows 10 VM 驗證。

## 玩家操作

1. 從遊戲發布頁下載並**完整解壓**支援的 Fire Ash 3.7 版本。
2. 從本專案 Release 下載 `FireAsh-zhTW-3.7-extras.2.exe`。
3. 正常退出遊戲，雙擊 EXE，選擇**包含 Game.exe 的資料夾**，按「安裝全部功能」。若 EXE 放在遊戲資料夾，會自動帶入路徑。
4. 安裝完成後自行開啟遊戲，在 Language 選擇「繁體中文」。不修改既有玩家語言設定／存檔，也不代為啟動遊戲。

首次安裝需網路：程式從 Noto 官方 GitHub 的固定 commit 自動取得約 16 MB 的 Noto Sans CJK TC Medium，校驗 SHA-256 後僅放入遊戲 Fonts 資料夾，不安裝 Windows 系統字型。字型下載失敗時不會開始修改遊戲。EXE 不內含字型，OFL 原文隨補丁提供。

安裝包尚未數位簽章，Windows 可能顯示未知發行者／SmartScreen 提示。請核對 Release 的 SHA-256，不需要關閉防毒。

## 包含的現行功能

- 繁中翻譯、NPC 固定暱稱與補充文字、中文戰鬥介面與字型排版修正。
- 既有寶可夢編輯器 v5 與 EV 結算／編輯介面修正。
- 遊戲提示 MOD v20：隱藏道具閃光、送道具 NPC／加入隊伍寶可夢驚嘆號、主線任務與城鎮地圖提示。
- 招式相剋符號、分類圖、招式資訊、能力階級圖示、中文特性招牌修正。
- 除錯招式／寶可夢中文列表、招式資訊、一鍵提高並補滿 PP。
- 遇敵平均間隔加倍、速度影響命中、連續等級曲線與野外神獸機率。

這是使用者現有安裝的**整合快照**，不提供個別功能勾選。玩法 MOD 會改變原版遊戲平衡。部分功能仍未完成實機遊玩驗收；安裝測試不代表全部遊戲流程驗收。

## 版本檢查、備份與還原

資料夾名為 3.7、Changelog 為 3.7.1、內部版本為 3.7.0；安裝程式以原始檔案 SHA-256 判定相容性，不僅看資料夾名稱。會檢查 Scripts、messages、english、Game.ini、Game.exe 與 PluginScripts。未對剛重新下載的官網壓縮檔獨立驗證；若官方 3.7 有不同修訂，程式會拒絕安裝，需另加版本支援。

只寫入四個遊戲檔：

- `Data/Scripts.rxdata`（由原檔與 BSDIFF 差分重建）
- `Data/traditional_chinese.dat`
- `Fonts/fire-ash-zhtw.otf`
- `Fonts/fire-ash-zhtw-OFL.txt`

原檔與交易紀錄位於遊戲內 `FireAsh-Extras-backup/`。安裝失敗會嘗試回復原狀；完整安裝後再次執行會判定無需重複安裝。按「還原」可回到安裝前狀態，保留備份與被移除的 MOD 檔，存檔不變。還原前會先驗證所有備份與現有檔案，遇到後續 MOD 變更會停止，不覆蓋別的修改。

要取代的遊戲檔若設為唯讀，安裝會在下載與備份前停止並指出檔案，不會自動改屬性；在檔案「內容」取消「唯讀」後重試。`.1` 遇到唯讀檔而留下無法還原的中斷紀錄時，用 `.2` 按「還原」即可解除。

意外終止若留下 `FireAsh-Extras.lock`，確認沒有安裝程序後刪除此鎖檔，再執行「還原」。搬移遊戲後要先放回安裝時的位置才能使用現有備份。舊中文化／其他 MOD 不會被自動覆蓋；使用原套件還原，或另外解壓乾淨遊戲再安裝。

## 原始碼與重建

- `installer.py`：視窗、版本驗證、字型下載、備份、安裝、還原。
- `build.py`：從原版基準與已校驗的整合安裝產生 BSDIFF 與單檔 EXE；拒絕非本版快照。
- `script-changes.patch`：本版相對原版各腳本段的可讀差異，供審查整合功能；不含原版遊戲封裝檔。
- `export_changes.py`：產生上述可讀差異。
- `test_installer.py`：失敗回復、備份損壞、未知版本、其他 MOD、並行鎖、中斷恢復等隔離測試。
- `verify_exe.py`：清空 PATH 後測試真正 EXE，含中文路徑、線上下載、重複安裝、還原及 Tk 載入。

維護端需要 Python 3.14、PyInstaller 6.22.3、bsdiff4 1.4.1；可讀差異匯出沿用專案的 rubymarshal。玩家不需要這些工具。以下路徑請換成自己的本機資料夾：

```powershell
python tools/installer/build.py --baseline '<original-baseline>' --installed '<verified-game>' --output '<release-folder>' --work '<build-folder>'
```

遊戲原檔、字型、玩家存檔與還原備份不進 GitHub。EXE 與校驗碼放 Releases；原始碼放 repo。本專案為非官方整合補丁，遊戲與各素材權利屬原權利人。
