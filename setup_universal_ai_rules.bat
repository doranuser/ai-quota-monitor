@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ==============================================================================
echo  [Universal AI Rules Installer] 
echo  自動同步「三層省 Token 協同開發與品質監督規則」至全域 AI CLI 環境
echo  支援: Antigravity (AGY) / Claude Code CLI / GitHub Copilot / Cursor
echo ==============================================================================
echo.

set "TARGET_DIR=%USERPROFILE%"
set "CLAUDE_DIR=%USERPROFILE%\.claude"
set "GITHUB_DIR=%USERPROFILE%\.github"

if not exist "%CLAUDE_DIR%" mkdir "%CLAUDE_DIR%" 2>nul
if not exist "%GITHUB_DIR%" mkdir "%GITHUB_DIR%" 2>nul

echo [1/5] 正在寫入 Antigravity 全域規則: %TARGET_DIR%\AGENTS.md ...
(
echo # Global Agent Safety ^& Execution Rules
echo.
echo Even when running in auto-approve mode ^(e.g., with `--dangerously-skip-permissions` or `agya`^), the Agent must strictly adhere to the following safety constraints and **MUST NOT** execute high-risk or destructive actions without explicitly asking and receiving user confirmation first via the `ask_question` tool.
echo.
echo ---
echo.
echo ### 1. Destructive File ^& Directory Operations
echo - **Recursive/Force Deletion**: Commands such as `rmdir /s /q`, `Remove-Item -Recurse -Force`, `rm -rf`, or script equivalents.
echo - **Root/Bulk Deletion**: Deleting project root contents, system directories, or batch deleting non-temporary files.
echo.
echo ### 2. Risky Version Control ^(Git^) Operations
echo - **Hard Reset**: `git reset --hard` or `git checkout -- .` ^(which drops uncommitted work^).
echo - **Force Clean**: `git clean -fd` / `git clean -fx`.
echo - **Force Push**: `git push --force` or `git push -f`.
echo - **Branch Deletion**: Deleting branches via `git branch -D` or deleting remote branches.
echo.
echo ### 3. System, Registry ^& Process Modifications
echo - **Registry Changes**: Modifying Windows Registry keys ^(`reg add`, `reg delete`, PowerShell registry cmdlets^).
echo - **Process Termination**: Forcefully killing system or user processes ^(`taskkill /F`, `Stop-Process -Force`^) unless explicitly instructed by the user in the prompt.
echo - **Disk / Partition Operations**: Any disk formatting, volume modification, or partition restructuring ^(`diskpart`, `Format-Volume`^).
echo - **Global Environment Variables**: Overwriting system-wide environment variables ^(`setx /M`, modifying machine PATH^).
echo.
echo ---
echo.
echo ### Execution Protocol
echo - When any of the above operations is required to accomplish a task:
echo   1. Clearly explain what command will be executed, why it is needed, and the potential impact/risk.
echo   2. Use `ask_question` ^(or explicit confirmation prompt^) to ask the user for confirmation.
echo   3. Only execute the command after the user explicitly selects/confirms to proceed.
echo.
echo ---
echo.
echo # 🤖 三層省 Token 協同開發與自動品質監督工作流 ^(3-Tier Token-Saving Architecture^)
echo.
echo 本環境所有程式碼開發、除錯、重構與大型任務，一律強制遵循「三層代理人協同 SOP」，以達到**節省 70%%~85%% 旗艦 Token 成本**並確保**100%% 程式碼正確性**：
echo.
echo ### 1. 主模型負責架構與驗證規劃 ^(Architect ^& Planner^)
echo - 主模型 ^(如 Claude 3.7 Sonnet / Gemini 3.7 Pro^) 專注於：
echo   1. 與使用者溝通釐清需求與設計決策。
echo   2. 擬定清晰的模組架構、檔案清單與介面規範。
echo   3. 制定驗證條件與測試用例 ^(Test Suite / Invariants^)。
echo - **嚴格禁令**：主模型嚴禁在主對話中直接印出大量重複、冗長的樣板程式碼或龐大樣式表，避免過度膨脹主對話 Context。
echo.
echo ### 2. 指派輕量子 Agent 執行代碼實作 ^(Worker^)
echo - 所有具體程式碼編寫、檔案修改、QSS/CSS 樣式與大篇幅實作，一律透過 `invoke_subagent` 指派輕量快速模型 ^(`Model: "flash"` 或 `Model: "flash_lite"`^) 在背景獨立 Workspace 中執行。
echo - 子 Agent 需具備讀寫工具與指令執行權限，負責高速、低成本地完成所有實作細節。
echo.
echo ### 3. 自動化品質監督與驗證門檻 ^(Supervisor ^& Quality Gate^)
echo - 子 Agent 實作完成後，主模型或監督機制必須自動執行驗證：
echo   1. **靜態語法檢查**：執行 `python -m py_compile` 或對應語言 linter。
echo   2. **自動化功能測試**：執行 `pytest`、`test_*.py` 或單元測試腳本。
echo - **重試與修正機制**：若測試未達 100%% 通過或發現邏輯盲點（例如邊界條件遺漏），主模型必須主動將錯誤細節傳回子 Agent 進行針對性修復，直至所有測試 100%% 通過方可交付。
) > "%TARGET_DIR%\AGENTS.md"
echo      [OK] %TARGET_DIR%\AGENTS.md 已建立。

echo [2/5] 正在寫入 Claude Code CLI 全域規則: %TARGET_DIR%\CLAUDE.md ...
copy /y "%TARGET_DIR%\AGENTS.md" "%TARGET_DIR%\CLAUDE.md" >nul
copy /y "%TARGET_DIR%\AGENTS.md" "%CLAUDE_DIR%\CLAUDE.md" >nul
echo      [OK] %TARGET_DIR%\CLAUDE.md 及 %CLAUDE_DIR%\CLAUDE.md 已建立。

echo [3/5] 正在寫入 GitHub Copilot 全域指令: %GITHUB_DIR%\copilot-instructions.md ...
copy /y "%TARGET_DIR%\AGENTS.md" "%GITHUB_DIR%\copilot-instructions.md" >nul
echo      [OK] %GITHUB_DIR%\copilot-instructions.md 已建立。

echo [4/5] 正在寫入 Cursor 全域規則: %TARGET_DIR%\.cursorrules ...
copy /y "%TARGET_DIR%\AGENTS.md" "%TARGET_DIR%\.cursorrules" >nul
echo      [OK] %TARGET_DIR%\.cursorrules 已建立。

echo [5/5] 正在寫入 Windsurf 全域規則: %TARGET_DIR%\.windsurfrules ...
copy /y "%TARGET_DIR%\AGENTS.md" "%TARGET_DIR%\.windsurfrules" >nul
echo      [OK] %TARGET_DIR%\.windsurfrules 已建立。

echo.
echo ==============================================================================
echo  ✅ 恭喜！全域 AI CLI 規則部署完成！
echo.
echo  已同步配置完成之工具:
echo   • Antigravity (AGY)     - %TARGET_DIR%\AGENTS.md
echo   • Claude Code CLI       - %TARGET_DIR%\CLAUDE.md
echo   • GitHub Copilot        - %GITHUB_DIR%\copilot-instructions.md
echo   • Cursor / Windsurf     - %TARGET_DIR%\.cursorrules
echo.
echo  未來在此主機開啟任何 AI CLI / Session，都將自動套用三層省 Token 規範！
echo ==============================================================================
echo.
pause
