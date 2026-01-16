# Feature 3.12: Workflow Automation Implementation Plan

## Overview
Implement workflow automation system for AuditCaseOS with rule-based triggers, automatic actions, in-app notifications, and background scheduling.

## Database Schema (configs/postgres/init.sql)

### New Enums
```sql
CREATE TYPE workflow_trigger_type AS ENUM ('STATUS_CHANGE', 'TIME_BASED', 'EVENT', 'CONDITION');
CREATE TYPE workflow_action_type AS ENUM ('CHANGE_STATUS', 'ASSIGN_USER', 'ADD_TAG', 'SEND_NOTIFICATION', 'CREATE_TIMELINE');
CREATE TYPE notification_priority AS ENUM ('LOW', 'NORMAL', 'HIGH', 'URGENT');
```

### New Tables
1. **workflow_rules** - Rule definitions (name, trigger_type, trigger_config JSONB, is_enabled, priority, scope_codes[], case_types[])
2. **workflow_actions** - Actions per rule (rule_id, action_type, action_config JSONB, sequence)
3. **notifications** - User notifications (user_id, title, message, priority, entity_type, entity_id, link_url, is_read)
4. **workflow_history** - Execution log (rule_id, case_id, trigger_data, actions_executed, success, error_message)

---

## Backend Implementation

### New Files to Create

| File | Description |
|------|-------------|
| `api/app/schemas/workflow.py` | Pydantic schemas for rules, actions, notifications, history |
| `api/app/services/workflow_service.py` | Rule CRUD, matching, execution orchestration |
| `api/app/services/notification_service.py` | Notification CRUD, WebSocket broadcast |
| `api/app/services/workflow_executor.py` | Action execution handlers |
| `api/app/services/scheduler_service.py` | APScheduler for time-based rules |
| `api/app/routers/workflows.py` | Admin endpoints for rule management |
| `api/app/routers/notifications.py` | User notification endpoints |

### Files to Modify

| File | Changes |
|------|---------|
| `api/app/main.py` | Register new routers, start/stop scheduler in lifespan |
| `api/app/routers/cases.py` | Add workflow triggers on status change, case creation |
| `api/app/routers/evidence.py` | Add workflow trigger on evidence upload |
| `api/app/services/websocket_service.py` | Add `broadcast_notification()` method |
| `api/requirements.txt` | Add `apscheduler>=3.10.0` |

### API Endpoints

**Workflows (Admin only):**
- `GET /api/v1/workflows/rules` - List rules
- `POST /api/v1/workflows/rules` - Create rule
- `GET /api/v1/workflows/rules/{id}` - Get rule
- `PATCH /api/v1/workflows/rules/{id}` - Update rule
- `DELETE /api/v1/workflows/rules/{id}` - Delete rule
- `POST /api/v1/workflows/rules/{id}/toggle` - Enable/disable
- `POST /api/v1/workflows/rules/{id}/actions` - Add action
- `GET /api/v1/workflows/history` - Execution history

**Notifications:**
- `GET /api/v1/notifications` - Get user notifications
- `GET /api/v1/notifications/unread-count` - Unread count
- `PATCH /api/v1/notifications/{id}/read` - Mark as read
- `POST /api/v1/notifications/mark-all-read` - Mark all read

---

## Frontend Implementation

### New Files to Create

| File | Description |
|------|-------------|
| `frontend/src/types/workflow.ts` | TypeScript types for workflows/notifications |
| `frontend/src/services/workflowApi.ts` | API service for workflows |
| `frontend/src/hooks/useNotifications.ts` | Notification hook with WebSocket |
| `frontend/src/components/notifications/NotificationCenter.tsx` | Header dropdown |
| `frontend/src/components/notifications/NotificationItem.tsx` | Notification item |
| `frontend/src/pages/Workflows.tsx` | Admin workflow management page |

### Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/App.tsx` | Add `/workflows` route |
| `frontend/src/components/layout/Header.tsx` | Add NotificationCenter |
| `frontend/src/components/layout/Sidebar.tsx` | Add Workflows link (admin) |
| `frontend/src/services/websocket.ts` | Add notification message type |
| `frontend/src/types/index.ts` | Export workflow types |

---

## Implementation Order

### Step 1: Database Schema
- Add enums and tables to `configs/postgres/init.sql`
- Recreate database to apply schema

### Step 2: Backend Schemas
- Create `api/app/schemas/workflow.py`

### Step 3: Notification Service
- Create `api/app/services/notification_service.py`
- Create `api/app/routers/notifications.py`
- Update `main.py` to register router

### Step 4: Workflow Service & Router
- Create `api/app/services/workflow_service.py`
- Create `api/app/services/workflow_executor.py`
- Create `api/app/routers/workflows.py`
- Update `main.py`, `services/__init__.py`, `routers/__init__.py`

### Step 5: Event Triggers
- Modify `routers/cases.py` - trigger on status change, case create
- Modify `routers/evidence.py` - trigger on evidence upload

### Step 6: Background Scheduler
- Add `apscheduler` to requirements.txt
- Create `api/app/services/scheduler_service.py`
- Integrate with `main.py` lifespan

### Step 7: WebSocket Notifications
- Extend `websocket_service.py` for notification broadcast

### Step 8: Frontend Notifications
- Create types, API service, hook
- Create NotificationCenter component
- Update Header

### Step 9: Frontend Workflows Page
- Create Workflows.tsx admin page
- Add route and sidebar link

### Step 10: Testing & Documentation
- Test all trigger/action types
- Update PROJECT_SPEC.xml to v0.5.3
- Mark Feature 3.12 as COMPLETED

### Step 11: Git Commit & Push (MANDATORY - per PROJECT_SPEC.xml rule #1)
- `git add -A`
- `git commit -m "feat(workflows): Add workflow automation (Feature 3.12)"`
- `git push`
- Verify push succeeded

---

## Key Design Decisions

1. **APScheduler** over Celery - simpler, no extra infrastructure needed
2. **JSONB for configs** - flexible schema for different trigger/action types
3. **Async task triggering** - `asyncio.create_task()` for non-blocking execution
4. **Execution history** - full audit trail for debugging
5. **Priority-based rules** - lower number = higher priority, early exit on match

## Safety Mechanisms
- Max execution depth (3 levels) to prevent infinite loops
- Cooldown period per case-rule combination
- Whitelist template variables in notifications
