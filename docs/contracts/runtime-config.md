# Runtime Configuration Contract

Source issue: #16

## Purpose

Define the minimal configuration surface required to make the MVP runtime genuinely configurable without making the system uncontrolled or overly broad.

## Status

The current runtime accepts `workspace`, `session_id`, and arbitrary request metadata, but there is no documented MVP config surface yet.

## MVP configuration domains

The MVP config surface should cover only these areas:

- workspace root
- model/provider selection
- approval mode
- hook enablement/defaults
- client-visible session settings needed for resume

## Current code anchors

- `VoidCodeRuntime(workspace=...)`
- `RuntimeRequest(prompt, session_id, metadata)`
- `SessionState.metadata`
- persisted session metadata in the SQLite-backed session store

## Recommended precedence

For MVP, config should resolve in this order:

1. explicit session override
2. explicit client or CLI flag
3. repo-local config file
4. environment variables
5. built-in defaults

## Session-persisted settings

Resume-critical settings should persist with the session, including at minimum:

- workspace
- approval mode
- selected model/provider when relevant to deterministic resume behavior
- any runtime mode that changes how the client should interpret the session

## Invariants

- users can change runtime behavior without editing code
- precedence must be deterministic
- persisted sessions must carry enough config to replay or resume meaningfully
- the MVP config surface must stay single-agent focused

## Current limitations

- no formal repo config file exists yet
- no documented env var contract exists yet
- current request metadata is flexible but not a stable public schema

## Non-goals

- advanced multi-agent configuration
- provider-specific secret management details
- full policy DSLs

## Acceptance checks

- a config doc exists that later implementation can follow directly
- the persisted-session contract explicitly calls out which settings survive resume
- config precedence is documented once and reused by TUI/web implementation work
