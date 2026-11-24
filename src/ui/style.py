"""
Swiss Precision Dark Titanium HUD styling for AGY Token Monitor.
Features Obsidian Titanium material, hairline borders, tabular numerals,
Electric Emerald (#00e599), Deep Iris (#7b61ff), GitHub Blue (#58a6ff), and Claude Terracotta (#e57b39) accents.
Zero-Emoji Pure Typographic & Geometric Swiss Precision.
"""

MAIN_STYLESHEET = """
/* ==================== ROOT CONTAINER (Obsidian Titanium HUD) ==================== */
#CapsuleRootContainer {
    background-color: rgba(12, 13, 16, 0.96);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 18px;
}

#CapsuleRootContainer:hover {
    border: 1px solid rgba(255, 255, 255, 0.14);
    background-color: rgba(15, 17, 21, 0.98);
}

/* ==================== CAPSULE HEADER BAR ==================== */
#CapsuleBar {
    background: transparent;
    border: none;
    min-height: 36px;
    max-height: 36px;
}

/* ==================== COMPACT MODE FRAME ==================== */
#CompactFrame {
    background-color: rgba(12, 13, 16, 0.96);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    min-height: 28px;
}

#CompactFrame:hover {
    border: 1px solid rgba(255, 255, 255, 0.16);
    background-color: rgba(16, 18, 22, 0.98);
}

/* ==================== HEADER METRIC LABELS & TYPOGRAPHY ==================== */
/* Active CLI Micro Tag Badge (e.g. [ AGY ], [ COPILOT ], [ CLAUDE ]) */
#CliBadgeTag {
    background-color: rgba(255, 255, 255, 0.05);
    color: #8a909e;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 6px;
    padding: 1px 5px;
    font-size: 9px;
    font-weight: 700;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
    letter-spacing: 0.5px;
}

#CliBadgeTag[cli="agy"] {
    background-color: rgba(0, 229, 153, 0.08);
    color: #00e599;
    border-color: rgba(0, 229, 153, 0.22);
}

#CliBadgeTag[cli="copilot"] {
    background-color: rgba(88, 166, 255, 0.08);
    color: #58a6ff;
    border-color: rgba(88, 166, 255, 0.22);
}

#CliBadgeTag[cli="claude"] {
    background-color: rgba(229, 123, 57, 0.08);
    color: #e57b39;
    border-color: rgba(229, 123, 57, 0.22);
}

#CliBadgeTag[cli="codex"] {
    background-color: rgba(16, 163, 127, 0.08);
    color: #10a37f;
    border-color: rgba(16, 163, 127, 0.22);
}

/* Active Group & 5-Hour Quota Typography */
#GroupQuotaLabel, #RemainingTokensLabel, #TotalTokensLabel {
    color: #f0f2f5;
    font-size: 12px;
    font-weight: 700;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, -apple-system, BlinkMacSystemFont, sans-serif;
    letter-spacing: -0.2px;
}

#GroupQuotaSub, #RemainingTokensSub, #TotalTokensSub {
    color: #8a909e;
    font-size: 8px;
    font-weight: 600;
    letter-spacing: 0.6px;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Countdown Badge (e.g. 3h 10m / 45m / OPTIMAL) */
#CountdownBadge {
    background-color: rgba(245, 166, 35, 0.08);
    color: #f5a623;
    border: 1px solid rgba(245, 166, 35, 0.20);
    border-radius: 7px;
    padding: 1px 6px;
    font-size: 10.5px;
    font-weight: 600;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, Consolas, sans-serif;
}

#CountdownBadge[full="true"] {
    background-color: rgba(0, 229, 153, 0.08);
    color: #00e599;
    border: 1px solid rgba(0, 229, 153, 0.20);
}

/* Deduction Delta Chip (e.g. -1.2k) */
#DeductionBadge, #DeltaBadge {
    background-color: rgba(245, 166, 35, 0.10);
    color: #f5a623;
    border: 1px solid rgba(245, 166, 35, 0.22);
    border-radius: 6px;
    padding: 1px 5px;
    font-size: 9.5px;
    font-weight: 600;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, Consolas, sans-serif;
}

/* TPM Speed Badge */
#TpmBadge {
    background-color: rgba(255, 255, 255, 0.035);
    color: #8a909e;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 7px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 600;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, Consolas, sans-serif;
}

#TpmBadge[generating="true"] {
    background-color: rgba(0, 229, 153, 0.10);
    color: #00e599;
    border: 1px solid rgba(0, 229, 153, 0.30);
}

/* Group & CLI Switcher Buttons in Header */
#GroupSwitchBtn, #CliSwitchBtn {
    background-color: rgba(255, 255, 255, 0.04);
    color: #8a909e;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 7px;
    padding: 1px 6px;
    font-size: 9.5px;
    font-weight: 600;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
}

#GroupSwitchBtn:hover, #CliSwitchBtn:hover {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.16);
    color: #f0f2f5;
}

#GroupSwitchBtn:focus, #CliSwitchBtn:focus, #ExpandChevronBtn:focus {
    border: 1px solid rgba(0, 229, 153, 0.65);
    background-color: rgba(0, 229, 153, 0.08);
}

/* Model Pill Tag */
#ModelPillTag {
    background-color: rgba(123, 97, 255, 0.12);
    color: #7b61ff;
    border: 1px solid rgba(123, 97, 255, 0.25);
    border-radius: 7px;
    padding: 1px 6px;
    font-size: 9.5px;
    font-weight: 600;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
}

/* Expand Drawer Chevron Button */
#ExpandChevronBtn {
    background-color: transparent;
    color: #8a909e;
    border: none;
    font-size: 9px;
    font-weight: bold;
    padding: 2px 4px;
    border-radius: 5px;
}

#ExpandChevronBtn:hover {
    background-color: rgba(255, 255, 255, 0.08);
    color: #f0f2f5;
}

/* ==================== COMPACT LABELS ==================== */
#CompactRemainingLabel, #CompactTokenLabel {
    color: #f0f2f5;
    font-size: 11.5px;
    font-weight: 700;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, Consolas, sans-serif;
}

#CompactRemainingBadge, #CompactContextBadge {
    color: #00e599;
    background-color: rgba(0, 229, 153, 0.08);
    border: 1px solid rgba(0, 229, 153, 0.22);
    border-radius: 6px;
    padding: 1px 5px;
    font-size: 9.5px;
    font-weight: 700;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, Consolas, sans-serif;
}

#CompactCountdownBadge {
    color: #f5a623;
    background-color: rgba(245, 166, 35, 0.08);
    border: 1px solid rgba(245, 166, 35, 0.20);
    border-radius: 6px;
    padding: 1px 5px;
    font-size: 9.5px;
    font-weight: 600;
}

#CompactTpmLabel {
    color: #8a909e;
    font-size: 10px;
    font-weight: 600;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, Consolas, sans-serif;
}

/* ==================== MINI-DASHBOARD FLYOUT DRAWER ==================== */
#DrawerWidget {
    background-color: rgba(12, 13, 16, 0.98);
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    border-bottom-left-radius: 18px;
    border-bottom-right-radius: 18px;
}

/* Model Group & CLI Quota Cards */
#GeminiCard, #ClaudeGptCard, #CopilotCard, #ClaudeCodeCard, #CodexCard, .FlyoutCard {
    background-color: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    padding: 6px 10px;
}

#GeminiCard:hover {
    border: 1px solid rgba(0, 229, 153, 0.30);
    background-color: rgba(0, 229, 153, 0.025);
}

#ClaudeGptCard:hover {
    border: 1px solid rgba(123, 97, 255, 0.30);
    background-color: rgba(123, 97, 255, 0.025);
}

#CopilotCard:hover {
    border: 1px solid rgba(88, 166, 255, 0.30);
    background-color: rgba(88, 166, 255, 0.025);
}

#ClaudeCodeCard:hover {
    border: 1px solid rgba(229, 123, 57, 0.30);
    background-color: rgba(229, 123, 57, 0.025);
}

#CodexCard:hover {
    border: 1px solid rgba(16, 163, 127, 0.30);
    background-color: rgba(16, 163, 127, 0.025);
}

.FlyoutCard:hover {
    border: 1px solid rgba(255, 255, 255, 0.10);
    background-color: rgba(255, 255, 255, 0.035);
}

/* Card Header Titles */
#GeminiCardHeader {
    color: #00e599;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.6px;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
}

#ClaudeCardHeader {
    color: #7b61ff;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.6px;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
}

#CopilotCardHeader {
    color: #58a6ff;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.6px;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
}

#ClaudeCodeCardHeader {
    color: #e57b39;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.6px;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
}

#CodexCardHeader {
    color: #10a37f;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.6px;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
}

.ActiveGroupBadge {
    background-color: rgba(255, 255, 255, 0.08);
    color: #f0f2f5;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 5px;
    padding: 1px 5px;
    font-size: 8.5px;
    font-weight: 700;
}

.InactiveGroupBadge {
    background-color: transparent;
    color: #8a909e;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 5px;
    padding: 1px 5px;
    font-size: 8.5px;
    font-weight: 500;
}

/* Card Quota Row Labels */
.DrawerRowTitle {
    color: #8a909e;
    font-size: 10px;
    font-weight: 500;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
}

.DrawerRowVal {
    color: #f0f2f5;
    font-size: 10.5px;
    font-weight: 700;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, Consolas, sans-serif;
}

.DrawerRowTime {
    color: #f5a623;
    font-size: 9px;
    font-weight: 600;
    background-color: rgba(245, 166, 35, 0.08);
    border: 1px solid rgba(245, 166, 35, 0.18);
    border-radius: 4px;
    padding: 1px 4px;
}

.DrawerRowTimeFull {
    color: #00e599;
    font-size: 9px;
    font-weight: 600;
    background-color: rgba(0, 229, 153, 0.08);
    border: 1px solid rgba(0, 229, 153, 0.18);
    border-radius: 4px;
    padding: 1px 4px;
}

.DrawerTitle {
    color: #8a909e;
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.5px;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
}

.DrawerValue {
    color: #f0f2f5;
    font-size: 10.5px;
    font-weight: 700;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, Consolas, sans-serif;
}

.DrawerValueSub {
    color: #8a909e;
    font-size: 9px;
    font-weight: 500;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, Consolas, sans-serif;
}

/* Minimal 4px Rounded Progress Bars in Drawer */
QProgressBar.DrawerBar {
    background-color: rgba(255, 255, 255, 0.06);
    border: none;
    border-radius: 2px;
    min-height: 4px;
    max-height: 4px;
}

QProgressBar.DrawerBar::chunk {
    background-color: #00e599;
    border-radius: 2px;
}

QProgressBar.DrawerBar[group="claude_gpt"]::chunk {
    background-color: #7b61ff;
}

QProgressBar.DrawerBar[group="copilot"]::chunk {
    background-color: #58a6ff;
}

QProgressBar.DrawerBar[group="claude"]::chunk {
    background-color: #e57b39;
}

QProgressBar.DrawerBar[group="codex"]::chunk {
    background-color: #10a37f;
}

QProgressBar.DrawerBar[quota="warning"]::chunk {
    background-color: #f5a623;
}

QProgressBar.DrawerBar[quota="danger"]::chunk {
    background-color: #ff453a;
}

/* Quick Action Buttons in Drawer (Minimal Text-Link Style) */
QPushButton.DrawerActionBtn {
    background-color: rgba(255, 255, 255, 0.03);
    color: #8a909e;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 6px;
    padding: 4px 7px;
    font-size: 9.5px;
    font-weight: 600;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
}

QPushButton.DrawerActionBtn:hover {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.14);
    color: #f0f2f5;
}

QPushButton.DrawerActionBtn:pressed {
    background-color: rgba(255, 255, 255, 0.12);
}

QPushButton.DrawerActionBtnPrimary {
    background-color: rgba(0, 229, 153, 0.08);
    color: #00e599;
    border: 1px solid rgba(0, 229, 153, 0.22);
    border-radius: 6px;
    padding: 4px 7px;
    font-size: 9.5px;
    font-weight: 700;
}

QPushButton.DrawerActionBtnPrimary:hover {
    background-color: rgba(0, 229, 153, 0.16);
    border: 1px solid rgba(0, 229, 153, 0.40);
    color: #ffffff;
}
"""

MENU_STYLESHEET = """
QMenu {
    background-color: rgba(12, 13, 16, 0.98);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 5px;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
}

QMenu::item {
    padding: 6px 18px 6px 10px;
    border-radius: 5px;
    color: #8a909e;
    font-size: 11.5px;
    font-weight: 500;
}

QMenu::item:selected {
    background-color: rgba(255, 255, 255, 0.08);
    color: #f0f2f5;
}

QMenu::separator {
    height: 1px;
    background-color: rgba(255, 255, 255, 0.06);
    margin: 3px 4px;
}
"""

DIALOG_STYLESHEET = """
QDialog {
    background-color: #0c0d10;
    color: #f0f2f5;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
}

QLabel {
    color: #8a909e;
    font-size: 11.5px;
}

QTextEdit, QLineEdit {
    background-color: rgba(255, 255, 255, 0.035);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 7px;
    padding: 7px 9px;
    color: #f0f2f5;
    font-size: 11.5px;
    font-family: Consolas, 'Segoe UI', Inter, monospace;
}

QTextEdit:focus, QLineEdit:focus {
    border: 1px solid #00e599;
    background-color: rgba(255, 255, 255, 0.05);
}

QPushButton {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 7px;
    padding: 6px 12px;
    color: #f0f2f5;
    font-size: 11.5px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.10);
    border-color: rgba(255, 255, 255, 0.20);
}

QPushButton:focus {
    border: 1px solid rgba(0, 229, 153, 0.65);
    background-color: rgba(0, 229, 153, 0.08);
}

QPushButton#PrimaryBtn {
    background-color: #00e599;
    border: 1px solid #00e599;
    color: #0c0d10;
    font-weight: 700;
}

QPushButton#PrimaryBtn:hover {
    background-color: #00ffaa;
    border-color: #00ffaa;
}

QPushButton.CliTabBtn {
    background-color: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 10.5px;
    font-weight: 600;
    color: #8a909e;
}

QPushButton.CliTabBtn[active="true"] {
    background-color: rgba(255, 255, 255, 0.10);
    border-color: rgba(255, 255, 255, 0.25);
    color: #f0f2f5;
}

/* ==================== AUTO-SYNC STATUS BAR ==================== */
#SyncStatusBar {
    color: #7d8492;
    font-size: 9.5px;
    font-family: "Consolas", "Menlo", monospace;
    letter-spacing: 0.3px;
    background: transparent;
    border-top: 1px solid rgba(255, 255, 255, 0.04);
    padding: 3px 0 1px 0;
}

#SyncNowBtn {
    background-color: rgba(0, 229, 153, 0.08);
    border: 1px solid rgba(0, 229, 153, 0.25);
    border-radius: 4px;
    color: #00e599;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 2px 8px;
    min-width: 56px;
}

#SyncNowBtn:hover {
    background-color: rgba(0, 229, 153, 0.16);
    border-color: rgba(0, 229, 153, 0.5);
}
"""
