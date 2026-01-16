# AuditCaseOS Workflow Testing Prompt

Give this prompt to another Claude instance to test the workflow automation system.

---

You are testing the AuditCaseOS Workflow Automation system. Your task is to create various workflow rules and test cases to verify the system works correctly.

## BASE CONFIGURATION

API Base URL: http://localhost:18000/api/v1
Authentication: Bearer token required (get via POST /api/v1/auth/login)

Default Admin Credentials:
- username: admin@example.com
- password: admin123

## STEP 1: GET AUTH TOKEN

```bash
# Get token
TOKEN=$(curl -s -X POST "http://localhost:18000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123" | jq -r '.access_token')

echo "Token: $TOKEN"
```

## WORKFLOW API ENDPOINTS

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /workflows/rules | List all rules |
| POST | /workflows/rules | Create a rule (admin) |
| GET | /workflows/rules/{id} | Get rule by ID |
| PATCH | /workflows/rules/{id} | Update rule (admin) |
| DELETE | /workflows/rules/{id} | Delete rule (admin) |
| POST | /workflows/rules/{id}/toggle | Enable/disable rule |
| GET | /workflows/rules/{id}/actions | Get rule actions |
| POST | /workflows/rules/{id}/actions | Add action to rule |
| DELETE | /workflows/actions/{id} | Delete action |
| GET | /workflows/history | Get all execution history |
| GET | /workflows/rules/{id}/history | Get rule execution history |
| POST | /workflows/rules/{id}/trigger/{case_id} | Manually trigger rule |

## TRIGGER TYPES

| Type | Description | trigger_config |
|------|-------------|----------------|
| STATUS_CHANGE | When case status changes | `{"from_status": "OPEN", "to_status": "IN_PROGRESS"}` |
| TIME_BASED | After X days in a status | `{"status": "OPEN", "days": 7}` |
| EVENT | When event occurs | `{"event_type": "case_created"}` |
| CONDITION | When conditions match | `{"conditions": [...]}` |

### EVENT TYPES (for EVENT trigger)
- case_created
- case_updated
- status_changed
- evidence_added
- evidence_deleted
- finding_added
- finding_updated
- timeline_added

### CONDITION OPERATORS
- eq (equal)
- neq (not equal)
- gt (greater than)
- gte (greater than or equal)
- lt (less than)
- lte (less than or equal)
- in (value in list)
- not_in (value not in list)
- contains (string contains)

## ACTION TYPES

| Type | Description | action_config |
|------|-------------|---------------|
| CHANGE_STATUS | Change case status | `{"new_status": "IN_PROGRESS"}` |
| ASSIGN_USER | Assign to user | `{"user_id": "uuid"}` or `{"assign_to_owner": true}` |
| ADD_TAG | Add tag to case | `{"tag": "escalated"}` |
| SEND_NOTIFICATION | Send in-app notification | `{"title": "...", "message": "...", "recipient_type": "owner", "priority": "HIGH"}` |
| CREATE_TIMELINE | Add timeline entry | `{"event_type": "workflow", "description_template": "Auto-action: {case_id}"}` |

### RECIPIENT TYPES (for SEND_NOTIFICATION)
- owner (case owner)
- assignee (assigned user)
- role (all users with role, use recipient_value: "admin")
- user (specific user, use recipient_value: "user-uuid")

### NOTIFICATION PRIORITIES
- LOW
- NORMAL
- HIGH
- URGENT

## CASE TYPES
- USB
- EMAIL
- WEB
- POLICY

## CASE STATUSES
- OPEN
- IN_PROGRESS
- PENDING_REVIEW
- CLOSED
- ARCHIVED

## SEVERITY LEVELS
- CRITICAL
- HIGH
- MEDIUM
- LOW
- INFO

## SCOPE CODES
- FIN, HR, IT, SEC, OPS, CORP, LEGAL, RND, PRO, MKT, QA, ENV, SAF, EXT, GOV, GEN

---

## CREATE TEST WORKFLOW RULES

### Rule 1: Alert on Critical Case Creation
```bash
curl -X POST "http://localhost:18000/api/v1/workflows/rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Critical Case Alert",
    "description": "Notify all admins when a critical case is created",
    "trigger_type": "EVENT",
    "trigger_config": {
      "event_type": "case_created"
    },
    "is_enabled": true,
    "priority": 10,
    "actions": [
      {
        "action_type": "SEND_NOTIFICATION",
        "action_config": {
          "title": "CRITICAL: New Case Created",
          "message": "A new critical case requires immediate attention",
          "recipient_type": "role",
          "recipient_value": "admin",
          "priority": "URGENT"
        },
        "sequence": 0
      },
      {
        "action_type": "ADD_TAG",
        "action_config": {
          "tag": "needs-review"
        },
        "sequence": 1
      }
    ]
  }'
```

### Rule 2: Auto-tag USB Cases
```bash
curl -X POST "http://localhost:18000/api/v1/workflows/rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Auto-tag USB Cases",
    "description": "Automatically tag USB cases for security review",
    "trigger_type": "EVENT",
    "trigger_config": {
      "event_type": "case_created"
    },
    "is_enabled": true,
    "priority": 50,
    "case_types": ["USB"],
    "actions": [
      {
        "action_type": "ADD_TAG",
        "action_config": {
          "tag": "security-review"
        },
        "sequence": 0
      },
      {
        "action_type": "CREATE_TIMELINE",
        "action_config": {
          "event_type": "workflow",
          "description_template": "Auto-tagged for security review (USB case)"
        },
        "sequence": 1
      }
    ]
  }'
```

### Rule 3: Status Change Notification
```bash
curl -X POST "http://localhost:18000/api/v1/workflows/rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Case Closed Notification",
    "description": "Notify owner when case is closed",
    "trigger_type": "STATUS_CHANGE",
    "trigger_config": {
      "to_status": "CLOSED"
    },
    "is_enabled": true,
    "priority": 100,
    "actions": [
      {
        "action_type": "SEND_NOTIFICATION",
        "action_config": {
          "title": "Case Closed",
          "message": "Your case has been closed. Please review the findings.",
          "recipient_type": "owner",
          "priority": "NORMAL"
        },
        "sequence": 0
      }
    ]
  }'
```

### Rule 4: Evidence Upload Alert
```bash
curl -X POST "http://localhost:18000/api/v1/workflows/rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Evidence Upload Alert",
    "description": "Alert case owner when new evidence is added",
    "trigger_type": "EVENT",
    "trigger_config": {
      "event_type": "evidence_added"
    },
    "is_enabled": true,
    "priority": 75,
    "actions": [
      {
        "action_type": "SEND_NOTIFICATION",
        "action_config": {
          "title": "New Evidence Added",
          "message": "New evidence has been uploaded to your case",
          "recipient_type": "owner",
          "priority": "NORMAL"
        },
        "sequence": 0
      },
      {
        "action_type": "CREATE_TIMELINE",
        "action_config": {
          "event_type": "evidence",
          "description_template": "Evidence uploaded - workflow triggered"
        },
        "sequence": 1
      }
    ]
  }'
```

### Rule 5: High Severity Escalation
```bash
curl -X POST "http://localhost:18000/api/v1/workflows/rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High Severity Escalation",
    "description": "Escalate high severity cases to admins",
    "trigger_type": "CONDITION",
    "trigger_config": {
      "conditions": [
        {"field": "severity", "operator": "in", "value": ["CRITICAL", "HIGH"]},
        {"field": "status", "operator": "eq", "value": "OPEN"}
      ]
    },
    "is_enabled": true,
    "priority": 5,
    "actions": [
      {
        "action_type": "SEND_NOTIFICATION",
        "action_config": {
          "title": "High Severity Case Needs Attention",
          "message": "A high severity case is waiting for review",
          "recipient_type": "role",
          "recipient_value": "admin",
          "priority": "HIGH"
        },
        "sequence": 0
      },
      {
        "action_type": "ADD_TAG",
        "action_config": {
          "tag": "escalated"
        },
        "sequence": 1
      }
    ]
  }'
```

### Rule 6: Stale Case Reminder (Time-Based)
```bash
curl -X POST "http://localhost:18000/api/v1/workflows/rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Stale Case Reminder",
    "description": "Remind assignee when case is open for 7 days",
    "trigger_type": "TIME_BASED",
    "trigger_config": {
      "status": "OPEN",
      "days": 7
    },
    "is_enabled": true,
    "priority": 80,
    "actions": [
      {
        "action_type": "SEND_NOTIFICATION",
        "action_config": {
          "title": "Stale Case Alert",
          "message": "This case has been open for 7 days without progress",
          "recipient_type": "assignee",
          "priority": "HIGH"
        },
        "sequence": 0
      },
      {
        "action_type": "ADD_TAG",
        "action_config": {
          "tag": "stale"
        },
        "sequence": 1
      }
    ]
  }'
```

### Rule 7: Auto-assign Legal Cases
```bash
curl -X POST "http://localhost:18000/api/v1/workflows/rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Auto-assign Legal Cases",
    "description": "Assign legal scope cases back to owner for review",
    "trigger_type": "EVENT",
    "trigger_config": {
      "event_type": "case_created"
    },
    "is_enabled": true,
    "priority": 60,
    "scope_codes": ["LEGAL"],
    "actions": [
      {
        "action_type": "ASSIGN_USER",
        "action_config": {
          "assign_to_owner": true
        },
        "sequence": 0
      },
      {
        "action_type": "ADD_TAG",
        "action_config": {
          "tag": "legal-review"
        },
        "sequence": 1
      },
      {
        "action_type": "CREATE_TIMELINE",
        "action_config": {
          "event_type": "workflow",
          "description_template": "Auto-assigned to owner for legal review"
        },
        "sequence": 2
      }
    ]
  }'
```

---

## TEST THE WORKFLOWS

### Create Test Cases to Trigger Workflows

#### Test Case 1: Critical USB Case (triggers Rules 1, 2, 5)
```bash
curl -X POST "http://localhost:18000/api/v1/cases" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Critical USB Policy Violation",
    "description": "Testing workflow automation with critical USB case",
    "case_type": "USB",
    "severity": "CRITICAL",
    "scope_code": "SEC"
  }'
```

#### Test Case 2: Legal Email Case (triggers Rules 1, 7)
```bash
curl -X POST "http://localhost:18000/api/v1/cases" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Legal Email Investigation",
    "description": "Testing legal scope workflow",
    "case_type": "EMAIL",
    "severity": "HIGH",
    "scope_code": "LEGAL"
  }'
```

#### Test Case 3: Low Priority Web Case
```bash
curl -X POST "http://localhost:18000/api/v1/cases" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Web Activity Review",
    "description": "Low priority web case for testing",
    "case_type": "WEB",
    "severity": "LOW",
    "scope_code": "IT"
  }'
```

### Test Status Change (triggers Rule 3)
```bash
# Get a case ID first
CASE_UUID=$(curl -s "http://localhost:18000/api/v1/cases" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.items[0].id')

# Change status to CLOSED
curl -X PATCH "http://localhost:18000/api/v1/cases/$CASE_UUID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "CLOSED"}'
```

### Test Evidence Upload (triggers Rule 4)
```bash
# Upload evidence to a case
curl -X POST "http://localhost:18000/api/v1/evidence/cases/$CASE_UUID/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/test/file.txt" \
  -F "description=Test evidence for workflow"
```

### Manually Trigger a Rule
```bash
# Get rule ID first
RULE_ID=$(curl -s "http://localhost:18000/api/v1/workflows/rules" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.items[0].id')

# Trigger manually
curl -X POST "http://localhost:18000/api/v1/workflows/rules/$RULE_ID/trigger/$CASE_UUID" \
  -H "Authorization: Bearer $TOKEN"
```

---

## VERIFY RESULTS

### Check Notifications
```bash
curl -s "http://localhost:18000/api/v1/notifications" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Check Unread Count
```bash
curl -s "http://localhost:18000/api/v1/notifications/unread-count" \
  -H "Authorization: Bearer $TOKEN"
```

### Check Workflow History
```bash
curl -s "http://localhost:18000/api/v1/workflows/history" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### List All Rules
```bash
curl -s "http://localhost:18000/api/v1/workflows/rules" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Toggle Rule On/Off
```bash
# Disable a rule
curl -X POST "http://localhost:18000/api/v1/workflows/rules/$RULE_ID/toggle" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Enable a rule
curl -X POST "http://localhost:18000/api/v1/workflows/rules/$RULE_ID/toggle" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### Delete a Rule
```bash
curl -X DELETE "http://localhost:18000/api/v1/workflows/rules/$RULE_ID" \
  -H "Authorization: Bearer $TOKEN"
```

---

## YOUR TASKS

1. Get an auth token
2. Create all 7 workflow rules above
3. Create test cases that trigger each rule
4. Verify notifications are created in the notification center
5. Check workflow history for execution logs
6. Test enable/disable functionality
7. Create at least 2 additional custom rules based on creative use cases

Report back the results of each test including:
- Rule IDs created
- Cases created to test
- Notifications generated
- Workflow history entries
- Any errors encountered
