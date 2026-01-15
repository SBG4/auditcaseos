# AuditCaseOS - Claude Code Instructions

## MANDATORY: Read PROJECT_SPEC.xml First

Before doing ANY work in this repository, you MUST:

1. **Read the PROJECT_SPEC.xml** at the repo root
2. **Check current version and phase** in `<metadata>`
3. **Review implementation guidelines** in `<implementation_guidelines>`
4. **Check feature status** to understand what's done vs pending

```bash
# The spec is at:
/Users/shiro/auditcaseos/PROJECT_SPEC.xml
```

## Key Sections to Reference

| Section | When to Use |
|---------|-------------|
| `<url_architecture>` | ANY work involving URLs, services, or Docker |
| `<onlyoffice_configuration>` | ONLYOFFICE or Nextcloud integration |
| `<failure_patterns>` | Before implementing new features |
| `<implementation_checklist>` | Before marking features complete |
| `<development_best_practices>` | Code style and patterns |
| `<ai_agent_guidelines>` | When using Task tool with agents |

## Mandatory Rules (from PROJECT_SPEC.xml)

1. **Git Commit Before Handover**: ALWAYS commit and push all changes before ending a session
2. **Update Spec on Completion**: Update PROJECT_SPEC.xml when features are completed
3. **URL Architecture**: Use INTERNAL URLs for server-to-server, EXTERNAL for browser

## Current Project State

- **Repo**: https://github.com/SBG4/auditcaseos
- **Stack**: FastAPI + React + PostgreSQL + MinIO + Ollama + Paperless + Nextcloud + ONLYOFFICE
- **Ports**: API:18000, Frontend:13000, Postgres:15432, MinIO:19000/19001, Paperless:18080, Nextcloud:18081, ONLYOFFICE:18082

## Verification

If the user asks "did you read the spec?", you should be able to answer:
- Current version number
- Current phase and status
- Number of completed vs pending features
- Recent changelog entries

## When Making Changes

1. Follow patterns in `<development_best_practices>`
2. Check `<failure_patterns>` to avoid known issues
3. Use `<implementation_checklist>` before completing features
4. Update `<changelog>` with your changes
5. Commit and push before session ends
