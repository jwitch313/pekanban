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
2. A starter board named **My Board** is created automatically with four
   columns: **To Do**, **In Progress**, **Completed**, and **Blocked**.
3. The **To Do** column contains a placeholder card titled **Your Task** with
   a short description explaining the basics of the app. It is there so the
   board is never empty — feel free to edit or delete it.
4. The board appears in the **Boards** list on the left, and its columns are
   shown in the main area.

The application remembers your data between sessions. Your data lives in a
hidden folder in your user profile (see [Data Storage & Backup](#12-data-storage--backup)).

### Layout overview

The window is divided into three regions:

| Region | Location | Purpose |
| --- | --- | --- |
| **Sidebar** | Left | Switch boards, create/rename/delete boards, and manage labels. |
| **Search & filter bar** | Top of the main area | Filter the visible cards by text, priority, column, label, or due date. |
| **Board view** | Main area | The columns and their task cards. |

> **Note:** Deleting a board, column, label, or sub-task is **permanent** and
> cannot be undone.

---

## 2. Boards

Boards are the top-level containers. They are managed from the **Boards**
section of the sidebar.

- **Switch board** — click a board name in the list. The main area reloads with
  that board's columns, and any active filters are cleared.
- **Create board** — type a name in the *New board…* field and press **Enter**
  or click the green **plus** icon button. The new board is created and
  selected immediately.
- **Rename board** — double-click a board name (or click the blue **pencil**
  icon button) to edit it inline, then press **Enter** to commit.
- **Delete board** — select a board and click the red **trash** icon button.
  If you delete the board you are currently viewing, PeKanBan switches to
  another board (or recreates a starter board if none remain).

> **Note:** Deleting a board removes its columns, tasks, labels, and sub-tasks.

---

## 3. Columns

Columns are the vertical lanes within a board (for example *To Do*, *Doing*,
*Done*).

- **Add column** — type a title in the *New column…* field in the **Columns**
  section of the sidebar and press **Enter**, or click the green **plus** icon
  button next to the field.
- **Rename column** — double-click the column title to edit it inline, then
  press **Enter**.
- **Move column** — use the teal **left arrow** and **right arrow** icon
  buttons in the column header to reorder it relative to its neighbors.
- **Delete column** — click the red **trash** icon button in the column
  header. This removes the column and all of its tasks.

---

## 4. Tasks (Cards)

Each card represents a single task.

- **Add task** — type a title in the *Add a task…* field at the bottom of a
  column and press **Enter** or click the green **plus** icon button.
- **Move task** — **drag and drop** a card into another column (or to a new
  position within the same column). Drop it where you want it to land.
- **Delete task** — click the red **trash** icon button on the card.

---

## 5. Archiving Tasks

Archiving is a non-destructive way to move a task off the board without
deleting it.

- **Archive a task** — click the teal **archive box** icon button on the card
  (immediately to the left of the red **trash** icon). The task disappears
  from the board and is stored in the board's archive.
- **View archived tasks** — click the teal **archive box** icon button on the
  right side of the search & filter bar. The board columns are replaced by the
  archive view, and the button appears pressed with a highlighted background
  and a white icon so you can see at a glance that you are in archive mode.
  Click it again (tooltip: *Back to board*) to return to the board.
- **Archive layout** — archived cards are shown in columns of up to **10**
  cards each, titled **Archived**, **Archived 2**, and so on. Additional
  columns are created automatically as the archive grows. If the board has no
  archived tasks, the view shows *No archived tasks.*
- **Restore a task** — on an archived card, the archive button is replaced by
  a green **circular arrow** (restore) icon button. Click it to put the task
  back on the board.
- **Delete a task** — the red **trash** icon button is still available on
  archived cards. Deleting is permanent and cannot be undone.

> **Note:** Archived cards cannot be dragged or moved while in the archive
> view. Switching boards (or creating/deleting a board) automatically returns
> you to the normal board view.

---

## 6. Priority & Due Dates

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

- **Change priority** — click the orange **flag** icon button on the card and
  choose a priority from the menu.
- **Set due date** — click the blue **calendar** icon button on the card to
  open the date picker, or clear the due date from the same popup.

---

## 7. Labels

Labels are colored tags scoped to the current board. They are managed in the
**Labels** section of the sidebar and applied to cards.

### Managing labels (sidebar)

- **Create label** — type a name in the *New label…* field, pick a color from
  the color dropdown, and click the green **plus** icon button.
- **Delete label** — select a label in the list and click the red **trash**
  icon button (Delete label).

### Applying labels to a card

- **Assign label** — click the purple **tag** icon button on a card to open a
  menu of the board's labels that are not yet applied, then choose one. The
  label appears as a colored **chip** on the card.
- **Remove label** — click a label chip on the card to remove it.

---

## 8. Sub-tasks

Each card can have a list of sub-tasks for breaking work into smaller steps.

- **Add sub-task** — type a title in the *Add subtask…* field on the card and
  press **Enter** or click the green **plus** icon button.
- **Toggle complete** — check or uncheck a sub-task's checkbox to mark it done
  or not done.
- **Delete sub-task** — click the red **trash** icon button next to a
  sub-task.

---

## 9. Search & Filter

The bar at the top of the board lets you narrow which cards are visible. Any
combination of the following can be active at once:

- **Text search** — type in the *Search tasks…* field to match task titles.
- **Priority** — choose a specific priority (or *Any priority*).
- **Column** — choose a specific column (or *Any column*).
- **Label** — choose a specific label (or *Any label*).
- **Due date range** — type a date (`yyyy-MM-dd`) in the *from* and/or *until*
  field, or click the blue **calendar** icon button next to a field to pick a
  date from a calendar popup. A field only filters while it holds a valid
  date.
- **Clear filters** — click the **Clear** button (slate **X** icon) to reset
  every filter and show all cards.
- **View archive** — click the teal **archive box** icon button (right side of
  the bar) to toggle the archived-tasks view. While active, the button appears
  pressed with a highlighted background.
- **Theme** — click the blue **monitor** icon button (far right of the bar) to
  choose **System**, **Light**, or **Dark** (see
  [Appearance](#11-appearance)).
- Filters reset automatically whenever you switch boards.

---

## 10. Keyboard Shortcuts

| Shortcut | Action |
| --- | --- |
| **Ctrl+N** | Focus the sidebar's *New column…* field. |
| **Ctrl+T** | Focus the first column's *Add a task…* field. |
| **Esc** | Clear the currently focused inline edit field. |
| **Ctrl+Z** | Undo the most recent task action (add / move / delete). |
| **Ctrl+Y** | Redo the most recently undone task action. |

---

## 11. Appearance (Dark Mode)

PeKanBan can follow your **Windows system theme** or use a fixed appearance.
Use the **Theme** button (blue **monitor** icon) at the right end of the
search & filter bar to choose:

- **System** (blue **monitor** icon) — follow the Windows theme. If Windows is
  set to **Light**, PeKanBan uses a light appearance; if **Dark**, a dark
  appearance.
- **Light** (amber **sun** icon) — always use the light appearance.
- **Dark** (indigo **moon** icon) — always use the dark appearance.

The choice is remembered between sessions.

---

## 12. Data Storage & Backup

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

## 13. Building the Windows Executable

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

## 14. License

PeKanBan is free and open-source software, licensed under the **GNU General
Public License v3 (GPLv3)**. You are free to use, study, modify, and share the
software, subject to the terms of the license. The full license text is
available in the [`LICENSE`](../LICENSE) file at the root of the repository and
at <https://www.gnu.org/licenses/gpl-3.0.html>.

---

## Quick Reference

| I want to… | Do this |
| --- | --- |
| Create a board | Sidebar → *New board…* → **Enter** |
| Add a column | Sidebar's *New column…* → **Enter** |
| Add a task | Column's *Add a task…* → **Enter** |
| Move a task | Drag the card to a new column/position |
| Add a sub-task | Card's *Add subtask…* → **Enter** |
| Tag a task | Click the purple **tag** icon on the card, pick a label |
| Find tasks | Use the search & filter bar |
| Archive a task | Click the teal **archive box** icon on the card |
| View archived tasks | Click the teal **archive box** icon in the filter bar |
| Undo a change | **Ctrl+Z** |
| Back up data | Copy the `~/.kanban/` folder |
