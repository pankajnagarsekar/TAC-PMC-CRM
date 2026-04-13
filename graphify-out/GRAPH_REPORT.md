# Graph Report - Phase 2 Track A  (2026-04-13)

## Corpus Check
- 101 files · ~96,832 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 512 nodes · 694 edges · 95 communities detected
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 137 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Group 0|Group 0]]
- [[_COMMUNITY_Group 1|Group 1]]
- [[_COMMUNITY_Group 2|Group 2]]
- [[_COMMUNITY_Group 3|Group 3]]
- [[_COMMUNITY_Scheduler UI|Scheduler UI]]
- [[_COMMUNITY_API Client|API Client]]
- [[_COMMUNITY_Group 6|Group 6]]
- [[_COMMUNITY_Group 7|Group 7]]
- [[_COMMUNITY_API Client|API Client]]
- [[_COMMUNITY_Group 9|Group 9]]
- [[_COMMUNITY_API Client|API Client]]
- [[_COMMUNITY_Group 11|Group 11]]
- [[_COMMUNITY_Group 12|Group 12]]
- [[_COMMUNITY_API Client|API Client]]
- [[_COMMUNITY_API Client|API Client]]
- [[_COMMUNITY_Group 15|Group 15]]
- [[_COMMUNITY_API Client|API Client]]
- [[_COMMUNITY_API Client|API Client]]
- [[_COMMUNITY_Group 18|Group 18]]
- [[_COMMUNITY_Theme Context|Theme Context]]
- [[_COMMUNITY_Group 20|Group 20]]
- [[_COMMUNITY_Group 21|Group 21]]
- [[_COMMUNITY_API Client|API Client]]
- [[_COMMUNITY_Scheduler UI|Scheduler UI]]
- [[_COMMUNITY_Group 24|Group 24]]
- [[_COMMUNITY_Group 25|Group 25]]
- [[_COMMUNITY_Group 26|Group 26]]
- [[_COMMUNITY_Group 27|Group 27]]
- [[_COMMUNITY_Group 28|Group 28]]
- [[_COMMUNITY_Group 29|Group 29]]
- [[_COMMUNITY_Group 30|Group 30]]
- [[_COMMUNITY_Group 31|Group 31]]
- [[_COMMUNITY_Group 32|Group 32]]
- [[_COMMUNITY_Group 33|Group 33]]
- [[_COMMUNITY_Theme Context|Theme Context]]
- [[_COMMUNITY_Theme Context|Theme Context]]
- [[_COMMUNITY_Theme Context|Theme Context]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Scheduler UI|Scheduler UI]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Scheduler UI|Scheduler UI]]
- [[_COMMUNITY_Scheduler UI|Scheduler UI]]
- [[_COMMUNITY_Scheduler UI|Scheduler UI]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Components|Components]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Scheduler UI|Scheduler UI]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Scheduler UI|Scheduler UI]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Tests|Tests]]
- [[_COMMUNITY_Tests|Tests]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Scheduler UI|Scheduler UI]]
- [[_COMMUNITY_Scheduler UI|Scheduler UI]]
- [[_COMMUNITY_Scheduler UI|Scheduler UI]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Theme Context|Theme Context]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_API Client|API Client]]
- [[_COMMUNITY_Scheduler UI|Scheduler UI]]
- [[_COMMUNITY_Scheduler UI|Scheduler UI]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]
- [[_COMMUNITY_Utility|Utility]]

## God Nodes (most connected - your core abstractions)
1. `ResourceCalendar` - 26 edges
2. `CalendarManager` - 21 edges
3. `CalendarException` - 20 edges
4. `ExceptionType` - 18 edges
5. `ResourceLeveler` - 18 edges
6. `ResourceLevelingService` - 17 edges
7. `LevelingStatus` - 15 edges
8. `ResourceCapacity` - 15 edges
9. `Conflict` - 15 edges
10. `ResourceLevelingContext` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Phase 2 Track A: Mobile Scheduler Integration (11 tasks, 40+ tests)` --participates_in--> `SchedulerScreen route entry point`  [INFERRED]
  MEMORY.md → apps/mobile/app/(admin)/scheduler/index.tsx
- `Phase 2 Track A: Mobile Scheduler Integration (11 tasks, 40+ tests)` --participates_in--> `SchedulerGantt - pan/pinch gesture canvas with FlashList virtualization`  [INFERRED]
  MEMORY.md → apps/mobile/components/scheduler/SchedulerGantt.tsx
- `Phase 2 Track A: Mobile Scheduler Integration (11 tasks, 40+ tests)` --participates_in--> `SchedulerList - virtualized task row list with critical-path highlighting`  [INFERRED]
  MEMORY.md → apps/mobile/components/scheduler/SchedulerList.tsx
- `ResourceCalendarService` --uses--> `ExceptionType`  [INFERRED]
  apps\api\app\modules\scheduler\resource_calendar_service.py → apps\api\app\modules\scheduler\resource_calendar.py
- `Resource Calendar Service  Manages resource calendars for scheduling calculation` --uses--> `ExceptionType`  [INFERRED]
  apps\api\app\modules\scheduler\resource_calendar_service.py → apps\api\app\modules\scheduler\resource_calendar.py

## Hyperedges (group relationships)
- **Mobile Scheduler UI Flow (SchedulerScreen -> Gantt/List view toggle)** — scheduler_screen_component, scheduler_gantt_component, scheduler_list_component, reanimated_gesture_patterns, flashlist_virtualization [INFERRED 0.85]
- **Data Pipeline (API -> Hook -> Components -> Render)** — scheduler_api_endpoint, use_scheduler_data_hook, scheduler_screen_component, scheduler_gantt_component, scheduler_list_component [EXTRACTED 0.95]
- **Rendering Optimization (Reanimated worklet + FlashList virtualization)** — gantt_bar_component, reanimated_gesture_patterns, flashlist_virtualization, scheduler_constants [INFERRED 0.80]
- **React Context Integration (Theme + Project selection)** — theme_context, project_context, scheduler_screen_component [EXTRACTED 0.90]
- **Complete Mobile Scheduler Module (Phase 2 Track A foundation)** — scheduler_screen_route, scheduler_screen_component, scheduler_gantt_component, scheduler_list_component, use_scheduler_data_hook, api_client_wrapper, scheduler_api_types, scheduler_constants, scheduler_utils, theme_context, project_context [INFERRED 0.85]

## Communities

### Community 0 - "Group 0"
Cohesion: 0.06
Nodes (40): CalendarException, CalendarManager, ExceptionType, from_dict(), Resource Calendar Module  Manages individual work calendars per resource with su, Check if exception contains date., Serialize to dictionary., Manages work calendar for a single resource.      Features:     - Standard worki (+32 more)

### Community 1 - "Group 1"
Cohesion: 0.1
Nodes (34): Conflict, LevelingResult, LevelingStatus, Resource Leveling Module  Implements leveling-by-free-slack algorithm to resolve, Initialize context with task data and resource definitions., Core leveling engine implementing leveling-by-free-slack algorithm.      Resolve, Main entry point for schedule leveling.          Args:             tasks: task_i, Build resource usage histogram.          For each task with an assignment, itera (+26 more)

### Community 2 - "Group 2"
Cohesion: 0.1
Nodes (21): BulkOperationExecutor, BulkOperationResult, BulkOperationService, Operation, OperationStatus, OperationType, Bulk Operations Module  Provides multi-task update operations with atomic transa, Types of bulk operations. (+13 more)

### Community 3 - "Group 3"
Cohesion: 0.1
Nodes (12): BaselineManager, Baseline Locking Manager for Scheduler  Implements immutability enforcement for, Unlock tasks from baseline to allow modifications.          Args:             pr, Check if a task is baseline-locked.          Args:             task: Task object, Validate that modifications don't violate baseline lock.          Args:, Sovereign manager for baseline lifecycle and immutability enforcement.      Resp, Create immutable snapshot of baseline state.          Args:             project_, Retrieve a baseline snapshot by version.          Args:             project_id: (+4 more)

### Community 4 - "Scheduler UI"
Cohesion: 0.1
Nodes (11): BulkOperationValidator, Validate start date update operation., Validate finish date update operation., Validate resource assignment update., Validate progress update (percentage complete)., Validate cost update., Validate task deletion., Validate task resume. (+3 more)

### Community 5 - "API Client"
Cohesion: 0.17
Nodes (20): request() function, token management, GenericResponse unwrapping, ApiError class, GenericResponse envelope unwrapping, 401 token refresh, FlashList 60fps virtualization with keyExtractor, GanttBar - row-level SVG bar with Reanimated animatedProps, GanttTimelineHeader - sticky timeline header synced via scrollX, Phase 2 Track A: Mobile Scheduler Integration (11 tasks, 40+ tests), ProjectContext - selectedProject state, persistence, auto-select logic, Gesture.Pan + Gesture.Pinch simultaneous handling (research pitfall 3) (+12 more)

### Community 6 - "Group 6"
Cohesion: 0.18
Nodes (10): addPhoto(), generatePDF(), getStatusColor(), handleApprove(), handleSave(), handleSaveWorkerLog(), handleSubmit(), onRefresh() (+2 more)

### Community 7 - "Group 7"
Cohesion: 0.18
Nodes (9): canSubmit(), getValidationMessage(), handleSubmit(), pickImage(), showAlert(), startRecording(), stopRecording(), takePhoto() (+1 more)

### Community 8 - "API Client"
Cohesion: 0.24
Nodes (6): apiRequest(), getToken(), handleSave(), openCreateModal(), resetForm(), showAlert()

### Community 9 - "Group 9"
Cohesion: 0.33
Nodes (10): addEntry(), getToken(), handleSave(), isEntryComplete(), loadVendors(), openVendorModal(), removeEntry(), selectVendor() (+2 more)

### Community 10 - "API Client"
Cohesion: 0.24
Nodes (4): ApiError, attemptTokenRefresh(), clearTokens(), request()

### Community 11 - "Group 11"
Cohesion: 0.2
Nodes (6): Initialize resource calendar.          Args:             resource_id: Unique res, Represents working hours for a single day., Initialize working hours.          Args:             start_hour: Start time (0-2, Serialize to dictionary., Initialize calendar exception.          Args:             start_date: Exception, WorkingHours

### Community 12 - "Group 12"
Cohesion: 0.22
Nodes (0): 

### Community 13 - "API Client"
Cohesion: 0.36
Nodes (6): apiRequest(), getToken(), handleSave(), openCreateModal(), resetForm(), showAlert()

### Community 14 - "API Client"
Cohesion: 0.42
Nodes (8): apiRequest(), getToken(), handleSave(), loadSettings(), pickLogo(), removeLogo(), showAlert(), updateField()

### Community 15 - "Group 15"
Cohesion: 0.33
Nodes (8): _apply_constraint(), _compute_es_from_predecessors(), _parse_date(), Core calculation logic. Implements the 8-step enhanced CPM pipeline., Apply constraint type to (es, ef) pair.     Returns adjusted (es, ef)., Compute ES for a task based on its predecessors using FS/SS/FF/SF + lag.     Ret, Parse a date string to datetime. Returns None if invalid., run_calculation()

### Community 16 - "API Client"
Cohesion: 0.39
Nodes (5): apiRequest(), getToken(), handleNotificationPress(), markAllAsRead(), markAsRead()

### Community 17 - "API Client"
Cohesion: 0.29
Nodes (2): apiRequest(), getToken()

### Community 18 - "Group 18"
Cohesion: 0.25
Nodes (1): getStatusColor()

### Community 19 - "Theme Context"
Cohesion: 0.29
Nodes (0): 

### Community 20 - "Group 20"
Cohesion: 0.62
Nodes (6): getCurrentLocation(), handleCheckIn(), handleCheckOut(), requestLocationPermission(), showAlert(), takeSelfie()

### Community 21 - "Group 21"
Cohesion: 0.33
Nodes (0): 

### Community 22 - "API Client"
Cohesion: 0.67
Nodes (5): apiRequest(), executeTransition(), fetchTransitions(), handleTransition(), showAlert()

### Community 23 - "Scheduler UI"
Cohesion: 0.6
Nodes (3): buildTimelineRange(), getBarLeft(), parseTaskDate()

### Community 24 - "Group 24"
Cohesion: 0.5
Nodes (0): 

### Community 25 - "Group 25"
Cohesion: 0.67
Nodes (2): handleProjectSelect(), loadProjects()

### Community 26 - "Group 26"
Cohesion: 1.0
Nodes (2): error(), handleLogin()

### Community 27 - "Group 27"
Cohesion: 0.67
Nodes (0): 

### Community 28 - "Group 28"
Cohesion: 0.67
Nodes (0): 

### Community 29 - "Group 29"
Cohesion: 0.67
Nodes (0): 

### Community 30 - "Group 30"
Cohesion: 0.67
Nodes (0): 

### Community 31 - "Group 31"
Cohesion: 0.67
Nodes (0): 

### Community 32 - "Group 32"
Cohesion: 1.0
Nodes (2): getToken(), handleChangePassword()

### Community 33 - "Group 33"
Cohesion: 0.67
Nodes (0): 

### Community 34 - "Theme Context"
Cohesion: 0.67
Nodes (0): 

### Community 35 - "Theme Context"
Cohesion: 0.67
Nodes (0): 

### Community 36 - "Theme Context"
Cohesion: 0.67
Nodes (0): 

### Community 37 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 39 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 40 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 41 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 42 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 43 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 44 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 46 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 47 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 48 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 49 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 50 - "Scheduler UI"
Cohesion: 1.0
Nodes (0): 

### Community 51 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 52 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 53 - "Scheduler UI"
Cohesion: 1.0
Nodes (0): 

### Community 54 - "Scheduler UI"
Cohesion: 1.0
Nodes (0): 

### Community 55 - "Scheduler UI"
Cohesion: 1.0
Nodes (0): 

### Community 56 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 57 - "Components"
Cohesion: 1.0
Nodes (0): 

### Community 58 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 59 - "Scheduler UI"
Cohesion: 1.0
Nodes (0): 

### Community 60 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 61 - "Scheduler UI"
Cohesion: 1.0
Nodes (0): 

### Community 62 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 63 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 64 - "Tests"
Cohesion: 1.0
Nodes (0): 

### Community 65 - "Tests"
Cohesion: 1.0
Nodes (0): 

### Community 66 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 67 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 68 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 69 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 70 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 71 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 72 - "Scheduler UI"
Cohesion: 1.0
Nodes (0): 

### Community 73 - "Scheduler UI"
Cohesion: 1.0
Nodes (0): 

### Community 74 - "Scheduler UI"
Cohesion: 1.0
Nodes (0): 

### Community 75 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 76 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 77 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 78 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 79 - "Theme Context"
Cohesion: 1.0
Nodes (0): 

### Community 80 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 81 - "API Client"
Cohesion: 1.0
Nodes (0): 

### Community 82 - "Scheduler UI"
Cohesion: 1.0
Nodes (0): 

### Community 83 - "Scheduler UI"
Cohesion: 1.0
Nodes (0): 

### Community 84 - "Utility"
Cohesion: 1.0
Nodes (1): All operations succeeded.

### Community 85 - "Utility"
Cohesion: 1.0
Nodes (1): Some operations succeeded.

### Community 86 - "Utility"
Cohesion: 1.0
Nodes (1): Calculate total working hours (excluding lunch).

### Community 87 - "Utility"
Cohesion: 1.0
Nodes (1): Deserialize from dictionary.

### Community 88 - "Utility"
Cohesion: 1.0
Nodes (1): Deserialize from dictionary.

### Community 89 - "Utility"
Cohesion: 1.0
Nodes (1): Deserialize from dictionary.

### Community 90 - "Utility"
Cohesion: 1.0
Nodes (1): Available capacity on this day.

### Community 91 - "Utility"
Cohesion: 1.0
Nodes (1): Check if this day is over-allocated.

### Community 92 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 93 - "Utility"
Cohesion: 1.0
Nodes (0): 

### Community 94 - "Utility"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **91 isolated node(s):** `Baseline Locking Manager for Scheduler  Implements immutability enforcement for`, `Sovereign manager for baseline lifecycle and immutability enforcement.      Resp`, `Initialize with database connection for snapshot storage.`, `Lock all tasks in the current schedule as a baseline.          Args:`, `Unlock tasks from baseline to allow modifications.          Args:             pr` (+86 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Utility`** (2 nodes): `+html.tsx`, `Root()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `+not-found.tsx`, `NotFoundScreen()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `index.tsx`, `Index()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `_layout.tsx`, `RootLayout()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `petty-cash.tsx`, `formatCurrency()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `_layout.tsx`, `DPRLayout()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `updateSetting()`, `appearance.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `currency.tsx`, `CurrencySettingsScreen()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `help.tsx`, `HelpScreen()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `notifications.tsx`, `NotificationsSettingsScreen()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `privacy.tsx`, `PrivacyScreen()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `terms.tsx`, `TermsScreen()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `_layout.tsx`, `SettingsLayout()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Scheduler UI`** (2 nodes): `_layout.tsx`, `TasksLayout()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `dashboard.tsx`, `onRefresh()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `_layout.tsx`, `ClientLayout()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Scheduler UI`** (2 nodes): `GanttBar.tsx`, `GanttBarComponent()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Scheduler UI`** (2 nodes): `GanttTimelineHeader.tsx`, `GanttTimelineHeader()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Scheduler UI`** (2 nodes): `SchedulerList.tsx`, `formatDate()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `Badge.tsx`, `Badge()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Components`** (2 nodes): `Card.tsx`, `Card()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `LoadingScreen.tsx`, `LoadingScreen()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Scheduler UI`** (2 nodes): `useSchedulerData.ts`, `useSchedulerData()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (2 nodes): `expo-global-setup.js`, `defineNonConfigurable()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Scheduler UI`** (2 nodes): `scheduler-utils.test.ts`, `makeTask()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `babel.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `eslint.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tests`** (1 nodes): `jest.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tests`** (1 nodes): `jest.setup.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `metro.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `_layout.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `index.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `voice-log.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `_layout.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `ScreenHeader.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Scheduler UI`** (1 nodes): `scheduler-constants.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Scheduler UI`** (1 nodes): `SchedulerGantt.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Scheduler UI`** (1 nodes): `SchedulerScreen.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `BlueprintGrid.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `Button.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `index.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `Input.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Theme Context`** (1 nodes): `theme.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `expo-winter-runtime.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `API Client`** (1 nodes): `api.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Scheduler UI`** (1 nodes): `SchedulerList.test.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Scheduler UI`** (1 nodes): `useSchedulerData.test.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `All operations succeeded.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `Some operations succeeded.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `Calculate total working hours (excluding lunch).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `Deserialize from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `Deserialize from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `Deserialize from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `Available capacity on this day.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `Check if this day is over-allocated.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `eslint.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Utility`** (1 nodes): `index.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BulkOperationValidator` connect `Scheduler UI` to `Group 2`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `ExceptionType` connect `Group 0` to `Group 2`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `ResourceCalendar` connect `Group 0` to `Group 11`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `ResourceCalendar` (e.g. with `ResourceCalendarService` and `Resource Calendar Service  Manages resource calendars for scheduling calculation`) actually correct?**
  _`ResourceCalendar` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `CalendarManager` (e.g. with `ResourceCalendarService` and `Resource Calendar Service  Manages resource calendars for scheduling calculation`) actually correct?**
  _`CalendarManager` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `CalendarException` (e.g. with `ResourceCalendarService` and `Resource Calendar Service  Manages resource calendars for scheduling calculation`) actually correct?**
  _`CalendarException` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `ExceptionType` (e.g. with `ResourceCalendarService` and `Resource Calendar Service  Manages resource calendars for scheduling calculation`) actually correct?**
  _`ExceptionType` has 13 INFERRED edges - model-reasoned connections that need verification._