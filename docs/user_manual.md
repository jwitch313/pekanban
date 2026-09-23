# PeKanBan — User Manual

PeKanBan is a local, offline Kanban board application for Windows. It lets you
organize work into **boards**, split each board into **columns**, and track
individual **tasks** (cards) with priorities, due dates, labels, and sub-tasks.
All data is stored on your machine — no account or internet connection is
required.

---

## 1. Getting Started

### First run

When you launch PeKanBan for the first time:

1. The main window opens at a default size (1100 × 700).
2. A starter board named **My Board** is created automatically.
3. The board appears in the **Boards** list on the left, and its columns are
   shown in the main area.

The application remembers your data between sessions. Your data lives in a
hidden folder in your user profile (see [Data Storage & Backup](#10-data-storage--backup)).

### Layout overview

The window is divided into three regions:

| Region | Location | Purpose |
| --- | --- | --- |
| **Sidebar** | Left | Switch boards, create/rename/delete boards, and manage labels. |
| **Search & filter bar** | Top of the main area | Filter the visible cards by text, priority, column, label, or due date. |
| **Board view** | Main area | The columns and their task cards. |

---

## 2. Boards

Boards are the top-level containers. They are managed from the **Boards**
section of the sidebar.

- **Switch board** — click a board name in the list. The main area reloads with
  that board's columns, and any active filters are cleared.
- **Create board** — type a name in the *New board…* field and press **Enter**
  or click **+**. The new board is created and selected immediately.
- **Rename board** — double-click a board name (or click the **✎** button) to
  edit it inline, then press **Enter** to commit.
- **Delete board** — select a board and click the **✕** button. If you delete
  the board you are currently viewing, PeKanBan switches to another board (or
  recreates a starter board if none remain).

> **Note:** Deleting a board removes its columns, tasks, labels, and sub-tasks.

---

## 3. Columns

Columns are the vertical lanes within a board (for example *To Do*, *Doing*,
*Done*).

- **Add column** — type a title in the *Add a column…* field at the start of
  the board and press **Enter**, or click **+ Add column**.
- **Rename column** — double-click the column title to edit it inline, then
  press **Enter**.
- **Move column** — use the **◀** (left) and **▶** (right) buttons in the
  column header to reorder it relative to its neighbors.
- **Delete column** — click the **✕** button in the column header. This removes
  the column and all of its tasks.

---

## 4. Tasks (Cards)

Each card represents a single task.

- **Add task** — type a title in the *Add a task…* field at the bottom of a
  column and press **Enter** or click **+**.
- **Move task** — **drag and drop** a card into another column (or to a new
  position within the same column). Drop it where you want it to land.
- **Delete task** — click the **✕** button on the card.

Adding, moving, and deleting tasks are **undoable** (see
[Keyboard Shortcuts](#8-keyboard-shortcuts)).

---

## 5. Priority & Due Dates

Every task has a **priority** shown as a colored badge on the card:

| Priority | Color |
| --- | --- |
| Low | Blue |
| Medium | Amber |
| High | Orange |
| Urgent | Red |

Tasks can also carry a **due date**, shown as `Due YYYY-MM-DD` on the card.

- **Overdue highlighting** — if a task's due date is in the past, the due-date
  label is shown in **bold red** so it stands out.

> **Note:** Priority and due date are set through the underlying task data. The
> card always displays the current priority badge and, when present, the due
> date (highlighted when overdue).

---

## 6. Labels

Labels are colored tags scoped to the current board. They are managed in the
**Labels** section of the sidebar and applied to cards.

### Managing labels (sidebar)

- **Create label** — type a name in the *New label…* field, pick a color from
  the color dropdown, and click **+**.
- **Delete label** — select a label in the list and click **✕ Delete label**.

### Applying labels to a card

- **Assign label** — click the **🏷** button on a card to open a menu of the
  board's labels that are not yet applied, then choose one. The label appears as
  a colored **chip** on the card.
- **Remove label** — click a label chip on the card to remove it.

---

## 7. Sub-tasks

Each card can have a list of sub-tasks for breaking work into smaller steps.

- **Add sub-task** — type a title in the *Add subtask…* field on the card and
  press **Enter** or click **+**.
- **Toggle complete** — check or uncheck a sub-task's checkbox to mark it done
  or not done.
- **Delete sub-task** — click the **✕** button next to a sub-task.

---

## 8. Search & Filter

The bar at the top of the board lets you narrow which cards are visible. Any
combination of the following can be active at once:

- **Text search** — type in the *Search tasks…* field to match task titles.
- **Priority** — choose a specific priority (or *Any priority*).
- **Column** — choose a specific column (or *Any column*).
- **Label** — choose a specific label (or *Any label*).
- **Due date range** — tick the **Due** checkbox to enable the *from* and
  *until* date pickers, then set the range.

- **Clear filters** — click **Clear** to reset every filter and show all cards.
- Filters reset automatically whenever you switch boards.

---

## 9. Keyboard Shortcuts

| Shortcut | Action |
| --- | --- |
| **Ctrl+N** | Focus the *Add a column…* field. |
| **Ctrl+T** | Focus the first column's *Add a task…* field. |
| **Esc** | Clear the currently focused inline edit field. |
| **Ctrl+Z** | Undo the most recent task action (add / move / delete). |
| **Ctrl+Y** | Redo the most recently undone task action. |

---

## 10. Appearance (Dark Mode)

PeKanBan follows your **Windows system theme** automatically:

- If Windows is set to **Light**, PeKanBan uses a light appearance.
- If Windows is set to **Dark**, PeKanBan uses a dark appearance.

The theme is detected at startup, so you do not need to configure anything.
Change your Windows appearance setting and relaunch PeKanBan to see the change.

---

## 11. Data Storage & Backup

All of your data is stored locally in your user profile, in a hidden folder:

```
~/.kanban/
├── kanban.db          # SQLite database: boards, columns, tasks, labels, sub-tasks
└── attachments/       # (reserved for file attachments)
```

On Windows this resolves to something like:

```
C:\Users\<YourName>\.kanban\kanban.db
```

**Backing up:** to back up your data, simply copy the entire `.kanban` folder
to another location (for example, an external drive or cloud storage). To
restore, close PeKanBan and copy the folder back into place.

> **Tip:** Because the database is a single file, copying `kanban.db` while the
> app is closed is the safest way to back up.

---

## 12. Building the Windows Executable

If you are building PeKanBan from source, the standalone Windows executable is
produced with [PyInstaller](https://pyinstaller.org/). See the
[README](../README.md) for the full build instructions. In short:

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

```bash
# macOS / Linux (bash)
./scripts/build.sh
```

The build produces a one-directory layout under `dist/PeKanBan/` containing
`PeKanBan.exe` and its `_internal/` support files.

---

## Quick Reference

| I want to… | Do this |
| --- | --- |
| Create a board | Sidebar → *New board…* → **Enter** |
| Add a column | *Add a column…* → **Enter** |
| Add a task | Column's *Add a task…* → **Enter** |
| Move a task | Drag the card to a new column/position |
| Add a sub-task | Card's *Add subtask…* → **Enter** |
| Tag a task | Click **🏷** on the card, pick a label |
| Find tasks | Use the search & filter bar |
| Undo a change | **Ctrl+Z** |
| Back up data | Copy the `~/.kanban/` folder |
