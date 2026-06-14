---
name: AI World Cup Team
description: Football prediction team for the 2026 World Cup — analyzes historical head-to-head data and delivers match forecasts via WhatsApp.
---

# AI World Cup — Agent Team

This workspace orchestrates AI agents for real-time football match analysis and prediction during the 2026 FIFA World Cup.

## Team

### world-cup-specialist

**Role:** Lead analyst and user-facing forecaster.

**Capabilities:**
- Retrieves historical head-to-head data via the Football Stats API
- Analyzes win rates, goal averages, and recent form
- Delivers conversational predictions via WhatsApp (Omni bridge)
- Asks for clarification when a message doesn't clearly name two teams

**When to spawn:** Any prediction or analysis request from a WhatsApp user.

```bash
genie spawn world-cup-specialist
```

**Files:**
- `agents/world-cup-specialist/SOUL.md` — domain knowledge and persona
- `agents/world-cup-specialist/HEARTBEAT.md` — autonomous task loop
- `agents/world-cup-specialist/AGENTS.md` — identity and mission

## Pipeline

```
WhatsApp message → Omni bridge → world-cup-specialist → Football Stats API → response
```

## Genie Workflow

```
brainstorm → wish → work → review → ship
```

Use `/brainstorm` to explore improvements, `/wish` to plan a feature, `/work` to execute, and `/review` to validate before shipping.
