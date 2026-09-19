# Software Design Requirements (SDR) — KanBan Task Manager

**Version:** 1.0  
**Date:** September 2025  
**Author:** User Request  

---

## 1. Executive Summary

A feature-rich, single-user Kanban task management application for Windows 10/11 that provides drag-and-drop task cards across customizable columns, multiple boards, due dates, priority levels, color-coded status indicators, search functionality, and data import/export capabilities. The app uses a professional visual style with dark mode following system settings, stores data locally in SQLite, and delivers as an executable installer for easy deployment across devices.

---

## 2. Feature Requirements

### 2.1 Core Kanban Features (MUST-HAVE)

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| F-01 | **Drag-and-Drop Task Cards** | Move tasks between columns by dragging; visual feedback during drag; drop zones highlight on hover | P0 |
| F-02 | **Custom Columns** | Create, rename, reorder, and delete custom column headers per board | P0 |
| F-03 | **Multiple Boards** | Switch between different Kanban boards; each board has its own set of columns and tasks | P0 |
| F-04 | **Due Dates** | Set due dates on tasks; visual indicators (warning colors, overdue highlighting) | P0 |
| F-05 | **Priority Levels** | Assign priority (Low/Medium/High/Urgent); color-coded by default but customizable | P0 |
| F-06 | **Color-Coded Status Indicators** | Visual status badges on cards; configurable colors per board or globally | P1 |
| F-07 | **Search & Filter** | Real-time search across all tasks; filter by column, priority, due date range, labels | P0 |

### 2.2 Enhanced Experience Features (SHOULD-HAVE)

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| F-08 | **Sub-tasks / Child Tasks** | Break down tasks into sub-tasks; drag sub-task cards within parent card or as separate items | P1 |
| F-09 | **Recurring Tasks** | Define recurrence patterns (daily, weekly, monthly, custom); auto-create on schedule | P2 |
| F-10 | **Task Templates** | Save task templates for quick creation; apply template to create new tasks with pre-filled data | P2 |
| F-11 | **Labels / Tags** | Color-coded labels beyond status; filter by label; unlimited custom labels per board | P1 |
| F-12 | **Time Tracking** | Built-in timer per task; start/stop/pause; reports on time spent per task/column | P2 |
| F-13 | **File Attachments** | Attach documents/images to cards; preview inline; drag-and-drop file upload | P1 |
| F-14 | **Comments & Mentions** | Discussion thread per card; @mentions for context; threaded replies | P2 |
| F-15 | **Calendar View** | Switch between Kanban and calendar views; see tasks by date alongside columns | P2 |
| F-16 | **Gantt Chart** | Timeline visualization of task dependencies, deadlines, and progress bars | P3 |
| F-17 | **Dashboard / Statistics** | Quick overview: overdue count, due this week, completion rate, time spent charts | P2 |
| F-18 | **Keyboard Shortcuts** | Power-user shortcuts (e.g., `Ctrl+N` new task, `Esc` cancel drag, custom bindings) | P1 |
| F-19 | **Custom Column Icons/Colors** | Personalize each board's look; assign icons and colors to columns | P2 |
| F-20 | **Task Dependencies** | Visual arrows showing "A blocks B"; auto-reorder on completion of dependencies | P3 |
| F-21 | **Quick-Add Gesture** | Click anywhere in empty space → type task name → card appears (Trello-style) | P2 |
| F-22 | **Bulk Operations** | Select multiple cards via Shift+click; move all at once; batch edit properties | P1 |
| F-23 | **Undo/Redo Stack** | `Ctrl+Z` / `Ctrl+Y` for undoing actions (moves, deletions, edits) with configurable history depth | P1 |
| F-24 | **Local Notifications** | Windows toast notifications for due dates; snooze tasks; custom notification sounds | P2 |
| F-25 | **Custom Filters / Saved Views** | Save filter combinations ("High Priority + Due This Week"); quick toggle between views | P2 |

### 2.3 Data Management Features (MUST-HAVE)

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| F-26 | **CSV Import/Export** | Export all data to CSV; import from CSV with mapping wizard | P0 |
| F-27 | **JSON Import/Export** | Full JSON backup/restore including relationships and attachments | P0 |

### 2.4 File Attachment Requirements (MUST-HAVE)

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| F-31 | **Attachment Size Limits** | Max 10MB per attachment; total storage limit of 500GB across all profiles | P0 |
| F-32 | **Storage Warning System** | Display warning when user data reaches 475MB (95% threshold); offer options: delete older attachments, delete all, or export to ZIP | P1 |

### 2.5 Multi-User Support (MUST-HAVE)

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| F-33 | **Multiple User Profiles** | Each user has separate data store; switch profiles via login screen; profile-specific settings and preferences | P0 |

### 2.4 UI/UX Requirements (MUST-HAVE)

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| F-28 | **Professional Visual Style** | Clean, elegant interface; consistent spacing and typography; no clutter | P0 |
| F-29 | **Dark Mode (System-Aware)** | Automatically switch to dark/light mode based on Windows system setting | P0 |
| F-30 | **Responsive Layout** | Adapts to different screen sizes; minimum usable area for small screens | P1 |

---

## 3. Technical Architecture Requirements

### 3.1 Technology Stack (MUST-HAVE)

| Component | Requirement | Rationale |
|-----------|-------------|-----------|
| **Language** | Python 3.9+ | Cross-platform, mature ecosystem |
| **GUI Framework** | PySide6 (Qt 6) | Native Windows look, robust drag-and-drop, dark mode support |
| **Database** | SQLite with SQLAlchemy ORM | Zero-config local storage, ACID compliance, fast queries |
| **Package Manager** | uv | Fast dependency management, dev testing, linting/formatting |

### 3.2 Project Structure (MUST-HAVE)

```
kanban_app/
├── src/
│ ├── __init__.py
│ ├── app.py # Entry point
│ ├── main_window.py # Main QWindow
│ │ ├── board_view.py # Board display
│ │ ├── card_widget.py # Draggable task card
│ │ ├── column_widget.py # Kanban column
│ │ └── sidebar.py # Navigation & filters
│ ├── models/
│ │ ├── __init__.py
│ │ ├── task.py # Task model (ORM)
│ │ ├── board.py # Board/column model
│ │ ├── subtask.py # Sub-task model
│ │ ├── label.py # Label/tag model
│ │ └── attachment.py # File attachment model
│ ├── services/
│ │ ├── database.py # DB connection & migrations
│ │ ├── import_export.py # CSV/JSON handlers
│ │ ├── notifications.py # Windows toast integration
│ │ └── shortcuts.py # Global keyboard shortcuts
│ ├── utils/
│ │ ├── drag_drop.py # Drag-and-drop helpers
│ │ ├── filters.py # Search/filter logic
│ │ └── validators.py # Input validation
│ └── resources/
│ ├── icons/ # Icon set (SVG/PNG)
│ └── styles/ # QSS theme files
├── tests/ # Unit & integration tests
├── docs/ # User documentation
├── requirements.txt # Dependencies
├── setup.py # Installation script
└── README.md
```

### 3.3 Database Schema (MUST-HAVE)

**Core Tables:**

| Table | Columns | Purpose |
|-------|---------|---------|
| `boards` | id, name, icon, color, created_at, updated_at | User's Kanban boards |
| `columns` | id, board_id, title, icon, color, order_idx | Board columns (To Do, In Progress, Done) |
| `tasks` | id, column_id, title, description, priority, due_date, status_color, labels, created_at, updated_at | Task cards |
| `subtasks` | id, task_id, title, completed, order_idx | Child tasks within a parent |
| `labels` | id, name, color, board_id (nullable for global) | Color-coded tags |
| `task_labels` | task_id, label_id | Many-to-many relationship |
| `attachments` | id, task_id, filename, filepath, mime_type, size_bytes | File attachments |
| `comments` | id, task_id, user_name, content, created_at | Discussion threads |
| `recurrences` | id, task_id, pattern (daily/weekly/monthly/custom), next_run, disabled_until | Recurring tasks |

**Indexes:**
- `tasks(column_id)`, `tasks(due_date)`, `tasks(priority)`
- `task_labels(task_id)`, `labels(board_id)`
- Full-text search index on task titles and descriptions

### 3.4 Data Persistence Strategy (MUST-HAVE)

| Operation | Method | Notes |
|-----------|--------|-------|
| **Write** | SQLAlchemy ORM with session management | Transactional integrity |
| **Read** | Optimized queries with eager loading for related data | Avoid N+1 queries |
| **Backup** | JSON export of entire database state | Full restore capability |
| **Migration** | Alembic or manual schema evolution scripts | Version control on schema changes |

### 3.5 Performance Requirements (SHOULD-HAVE)

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Initial load time** | < 2 seconds | App should feel instant on startup |
| **Drag-and-drop latency** | < 100ms per drag operation | Smooth, responsive interaction |
| **Search response** | < 50ms for 10k tasks | Real-time search feedback |
| **Memory footprint** | < 200MB idle | Light on system resources |

---

## 4. User Experience Requirements

### 4.1 Visual Design (MUST-HAVE)

- **Style:** Professional, clean, and elegant — no unnecessary decorations
- **Typography:** System fonts with consistent hierarchy; readable at small sizes
- **Color Palette:** Neutral base colors with semantic accent colors for priorities/status
- **Dark Mode:** Seamless transition following Windows system setting; high contrast ratios for accessibility

### 4.2 Interaction Patterns (MUST-HAVE)

| Pattern | Behavior |
|---------|----------|
| **Drag-and-Drop** | Visual feedback: card highlights, drop zone glow, smooth animations |
| **Keyboard Navigation** | Tab through cards; arrow keys to navigate within board; `Enter` to edit |
| **Context Menus** | Right-click on card for quick actions (edit, delete, move) |
| **Hover States** | Subtle hover effects on interactive elements; no jarring animations |

### 4.3 Accessibility (SHOULD-HAVE)

- Support Windows High Contrast mode
- Keyboard-only navigation with visible focus indicators
- Screen reader-friendly labels and ARIA attributes
- Minimum touch target size: 44x44 pixels for touch users

---

## 5. Implementation Phases & Timeline

### Phase 1: Foundation
**Goal:** Working prototype with core Kanban functionality

| Steps | Deliverables |
|------|--------------|
| **Step 1** | Project setup, database schema, basic window layout, task CRUD operations |
| **Step 2** | Drag-and-drop implementation, multiple columns, due dates & priority display |

### Phase 2: Core Features
**Goal:** Full-featured Kanban with search and data management

| Steps | Deliverables |
|------|--------------|
| **Step 3** | Multiple boards, custom columns, labels/tags, search & filtering |
| **Step 4** | Import/export CSV/JSON, dark mode, keyboard shortcuts, undo/redo |

### Phase 3: Enhanced Features
**Goal:** All "should-have" features implemented

| Steps | Deliverables |
|------|--------------|
| **Step 5** | Sub-tasks, recurring tasks, time tracking, file attachments, comments |
| **Step 6** | Calendar view, dashboard statistics, bulk operations, notifications |

### Phase 4: Polish & Distribution (Weeks 7-8)
**Goal:** Production-ready executable with documentation

| Steps | Deliverables |
|------|--------------|
| **Step 7** | Gantt chart, dependencies, saved views, final UI polish |
| **Step 8** | Executable packaging (PyInstaller), user manual, bug fixes, testing |

---

## 6. Risk Assessment & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Drag-and-drop performance with many cards** | Medium | Low | Use Qt's native drag delegate; batch updates; virtual scrolling for large boards |
| **SQLite file locking on concurrent access** | Low | Very Low | Single-user app; use WAL mode for better concurrency |
| **Large attachment files slowing UI** | Medium | Medium | Lazy loading of attachments; thumbnail previews only |
| **Complex query performance with 10k+ tasks** | Low | Low | Indexes on frequently queried columns; pagination in calendar view |

---

## 7. Success Criteria

The project is considered successful when:

- ✅ All MUST-HAVE features are implemented and working
- ✅ The app runs smoothly on Windows 10/11 with <2s startup time
- ✅ Data import/export works correctly for backup purposes
- ✅ Dark mode follows system settings automatically
- ✅ Drag-and-drop feels natural and responsive
- ✅ Search returns results in real-time as user types

---

## 8. Assumptions & Dependencies

| Item | Value |
|------|-------|
| **Target OS** | Windows 10/11 (64-bit) |
| **Python Version** | 3.9 or later |
| **Display Resolution** | Minimum 1280x720 for usable interface |
| **User Proficiency** | Intermediate computer literacy; familiar with drag-and-drop concepts |
| **Internet Required** | No — fully offline operation after initial installation |

---

## 9. Approval & Next Steps

This SDR document has been prepared for review and approval. Upon approval, the following steps will be taken:

1. **Repository Setup:** Initialize Git repository with project structure
2. **Database Design Finalization:** Create detailed ER diagrams and migration scripts
3. **UI Wireframes:** Produce low-fidelity wireframes for key screens
4. **Development Kickoff:** Begin Phase 1 implementation

**Questions to Address Before Proceeding:**

- [ ] Are all the suggested features (F-08 through F-25) acceptable, or should any be deprioritized?
- [ ] Should sub-tasks be implemented as separate cards within a parent card, or as inline items?
- [ ] For file attachments: what maximum file size per attachment and total storage limit?
- [ ] Should the app support multiple user profiles (e.g., family sharing) or remain single-user only?

---

**Document Control:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Sep 2025 | User Request | Initial SDR document |
