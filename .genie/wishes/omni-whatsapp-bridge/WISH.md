# Wish: Connect world-cup-specialist to Omni WhatsApp bridge

**Status:** APPROVED  
**Created:** 2026-06-14  
**Slug:** omni-whatsapp-bridge

## Summary

The `world-cup-specialist` agent needs to receive WhatsApp messages via the running Omni bridge, query the Football Stats API for head-to-head data, and respond with predictions — all automatically.

Omni is already running (`omni-api`, PID 67085) and receiving real messages from a WhatsApp group. The FastAPI backend is already built with `/football/head-to-head` and `/football/predict` endpoints. The missing piece is connecting the agent to Omni so it processes and answers messages.

## Acceptance Criteria

- [ ] The `world-cup-specialist` agent subscribes to incoming WhatsApp messages via the Omni/NATS bridge
- [ ] When a message mentions two national football teams, the agent calls the Football Stats API and returns a prediction
- [ ] When a message does NOT mention two teams, the agent asks for clarification (plain text, no markdown)
- [ ] Responses appear in the WhatsApp group within 30 seconds of the message arriving
- [ ] The agent runs autonomously (no manual intervention per message)

## Scope

### Group 1 — Omni message subscription

Wire the `world-cup-specialist` agent to receive messages from Omni via NATS.

**Files to create/modify:**
- `app/integrations/omni_client.py` — subscribe to `omni.message.*` on NATS, publish responses
- `main.py` — start the Omni listener on app startup (or as a separate service)

**Key details:**
- NATS is running at `localhost:4222`
- Incoming messages arrive on subjects like `omni.message.>` (see omni-api logs)
- Responses must be sent back via Omni's send API (plain text, no markdown)
- Message format from logs: `{"from": "<phone>", "chatId": "<group>", "externalId": "<id>"}`

### Group 2 — Football Stats API as agent tool

Expose the `HeadToHeadAnalyzer` as a tool the `world-cup-specialist` Claude agent can call directly (instead of via HTTP).

**Files to create/modify:**
- `app/tools/head_to_head_tool.py` — wrap `HeadToHeadAnalyzer.generate_summary()` as a Claude tool definition
- `agents/world-cup-specialist/SOUL.md` — add tool usage instructions

**Key details:**
- Tool name: `get_head_to_head`
- Input: `team_a` (string), `team_b` (string)
- Output: JSON with `historical_stats` and `recent_encounters`
- The agent must call this tool before making any prediction

### Group 3 — Agent HEARTBEAT validation

Validate that the HEARTBEAT loop correctly orchestrates both groups end-to-end.

**Steps:**
1. Send a test message to the WhatsApp group: "Predict Brazil vs Argentina"
2. Verify the agent receives it, calls `get_head_to_head`, and posts a response
3. Send a message without two teams: "What do you think about the World Cup?"
4. Verify the agent asks for clarification

## Non-goals

- No conversation memory in this wish (separate wish)
- No support for individual DMs (only group messages)
- No rate limiting / abuse protection (separate wish)

## Notes

- The Omni bridge uses NATS subjects. Subscribe to `omni.message.>` for all incoming messages.
- Responses should go through `genie agent send` or Omni's HTTP API — check which one the current setup supports.
- Keep responses under 3 paragraphs, plain text only (WhatsApp renders `*` and `#` literally).
