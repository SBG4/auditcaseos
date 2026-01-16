# AI Agent Usage Guidelines

Guidelines for using Claude Code Task agents effectively to improve accuracy, verify information, and parallelize work.

---

## When to Use Multi-Agents

### High Priority Scenarios

#### 1. Research from Multiple Sources
When gathering information that needs verification from official sources.

**Pattern**: Launch parallel agents, each researching from different authoritative sources.

**Example**: Research best practices:
- Agent 1 → official docs
- Agent 2 → RFC specs
- Agent 3 → security guidelines

#### 2. Cross-Verification of Facts
When accuracy is critical and information must be verified.

**Pattern**: Launch multiple agents researching the same topic from different angles, compare results.

**Example**: Verify API behavior:
- Agent 1 → read documentation
- Agent 2 → test actual endpoints

#### 3. Debugging Complex Issues
When root cause is unclear and multiple areas need investigation.

**Pattern**: Launch agents to investigate different potential causes simultaneously.

**Example**: ONLYOFFICE not working:
- Agent 1 → check server health
- Agent 2 → check Nextcloud config
- Agent 3 → check network

### Medium Priority Scenarios

#### 4. Large Codebase Exploration
When exploring unfamiliar code or searching across many files.

**Pattern**: Use Explore agent type for codebase searches instead of manual Glob/Grep.

**Example**: Finding error handling patterns across the codebase.

#### 5. Independent Parallel Tasks
When multiple tasks have no dependencies on each other.

**Pattern**: Launch all independent tasks as parallel agents, collect results.

**Example**: Testing multiple endpoints, checking multiple services.

---

## Agent Types

### Explore Agent
- **Type**: `subagent_type="Explore"`
- **Purpose**: Fast codebase exploration, file searches, understanding code structure

**Use When**:
- Searching for keywords, patterns, or files across the codebase
- Understanding how a feature is implemented
- Finding all usages of a function or class
- Answering questions about codebase structure

**Thoroughness**: Specify "quick", "medium", or "very thorough"

### Plan Agent
- **Type**: `subagent_type="Plan"`
- **Purpose**: Designing implementation strategies and architectural decisions

**Use When**:
- Planning a new feature implementation
- Designing system architecture
- Evaluating trade-offs between approaches

### General-Purpose Agent
- **Type**: `subagent_type="general-purpose"`
- **Purpose**: Complex multi-step tasks, web research, comprehensive analysis

**Use When**:
- Researching external documentation
- Web searches for best practices
- Multi-step investigations
- Tasks requiring multiple tool types

---

## Parallel Execution Patterns

### Pattern 1: Research Parallelization
Split research across multiple authoritative sources.

```
Launch in single message with multiple Task tool calls:
- Agent 1: "Research [topic] from [official-docs-1]. Only use authoritative sources."
- Agent 2: "Research [topic] from [official-docs-2]. Include source URLs."
- Agent 3: "Research [topic] from [standards-body]. Verify against specs."
```

**Benefit**: Faster research, cross-verified information, multiple perspectives

### Pattern 2: Verification Pattern
Verify critical information from multiple angles.

```
Launch agents that approach the same question differently:
- Agent 1: "Check official documentation for [behavior]"
- Agent 2: "Test [behavior] by making actual API calls"
- Agent 3: "Search codebase for how [behavior] is implemented"
```

**Benefit**: Catches documentation errors, implementation bugs, misunderstandings

### Pattern 3: Investigation Pattern
Debug issues by investigating multiple potential causes.

```
When issue root cause is unknown:
- Agent 1: "Check [component-1] health, logs, and configuration"
- Agent 2: "Check [component-2] connectivity and settings"
- Agent 3: "Check [component-3] for errors or misconfigurations"
```

**Benefit**: Faster debugging, no sequential bottleneck, comprehensive coverage

### Pattern 4: Source Validation Pattern
Ensure information comes from legitimate, authoritative sources.

```
When researching best practices:
1. Specify ONLY official sources in agent prompts
2. Require source URLs in responses
3. Cross-check with multiple agents
4. Reject information without verifiable sources
```

**Benefit**: Prevents misinformation, ensures accuracy

---

## Best Practices

| Rule | Severity | Description |
|------|----------|-------------|
| AGENT-BP-1 | HIGH | Always specify the `subagent_type` parameter when using Task tool |
| AGENT-BP-2 | HIGH | Launch multiple independent agents in a SINGLE message |
| AGENT-BP-3 | HIGH | For research tasks, require agents to return SOURCE URLs |
| AGENT-BP-4 | HIGH | Restrict research agents to official/authoritative domains only |
| AGENT-BP-5 | MEDIUM | Use `run_in_background=true` for long-running agents |
| AGENT-BP-6 | MEDIUM | Use `TaskOutput` with `block=true` only when you need results to proceed |
| AGENT-BP-7 | MEDIUM | Provide detailed prompts with clear instructions |
| AGENT-BP-8 | LOW | Use `haiku` model for quick, straightforward tasks |

---

## Anti-Patterns to Avoid

### 1. Sequential When Parallel Is Possible
**Problem**: Launching agents one at a time, waiting for each to complete.
**Solution**: Launch all independent agents in a single message.

### 2. Unverified Single-Source Research
**Problem**: Trusting information from a single agent without verification.
**Solution**: Use multiple agents researching same topic from different sources.

### 3. Unrestricted Web Research
**Problem**: Allowing agents to use any web source (blogs, forums, outdated articles).
**Solution**: Restrict to official documentation domains, require source URLs.

### 4. Vague Agent Prompts
**Problem**: Giving agents unclear instructions leading to irrelevant results.
**Solution**: Provide specific, detailed prompts with clear deliverables.

### 5. Blocking on Non-Critical Agents
**Problem**: Using `block=true` when you could continue working on other tasks.
**Solution**: Use `run_in_background=true`, continue working, check results when needed.

---

## Authoritative Sources by Domain

### Python/FastAPI
- fastapi.tiangolo.com
- docs.python.org
- docs.pydantic.dev
- docs.sqlalchemy.org

### React/TypeScript
- react.dev
- typescriptlang.org
- vitejs.dev
- tailwindcss.com

### Docker/DevOps
- docs.docker.com
- owasp.org
- opentelemetry.io

### API Standards
- rfc-editor.org
- spec.openapis.org
- jsonapi.org

### Database
- postgresql.org
- redis.io

### Integrations
- api.onlyoffice.com
- docs.nextcloud.com
- min.io/docs

---

## Example Workflows

### Research Best Practices
1. Identify topic areas needing research (backend, frontend, devops, etc.)
2. Launch parallel agents, each targeting different official documentation
3. Require each agent to include source URLs for every recommendation
4. Collect results, cross-reference for consistency
5. Compile verified information, discard unsourced claims

### Debug Production Issue
1. Identify all components that could cause the issue
2. Launch parallel investigation agents for each component
3. Each agent checks: health, logs, configuration, connectivity
4. Combine findings to identify root cause
5. Verify fix with test agent before deploying

### Implement New Feature
1. Use Explore agent to understand existing codebase patterns
2. Use Plan agent to design implementation approach
3. Research best practices with parallel agents (if needed)
4. Implement following established patterns
5. Use agents to verify: tests pass, no regressions, browser works
