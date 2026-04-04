# Stream Transport Contract

Source issue: #17

## Purpose

Define the MVP transport expectations for delivering runtime events and final output to CLI, TUI, and web clients.

## Status

The current code exposes ordered events and output through an in-process runtime response and CLI printing. A generalized streaming transport is still planned.

The current CLI is a replay/print consumer, not a live streaming transport in the richer TUI/web sense.

## Transport responsibilities

The transport layer must deliver:

- ordered runtime events
- final output
- enough session identity to associate the stream with persistence and resume

It must not:

- bypass runtime governance
- invent private client-only state that is not recoverable

## MVP delivery semantics

- streams are session-scoped
- event ordering follows `EventEnvelope.sequence`
- clients must be able to render partial progress before final output exists
- persisted replay must preserve the same observable ordering model as live delivery

## Client expectations

### CLI
- may consume a completed response and print events in order

### TUI
- should consume ordered events as an activity timeline for an active turn
- should be able to switch from live stream to persisted replay without semantic drift

### Web client
- should consume the same event semantics as the TUI
- should render event progression, tool activity, approvals, and final output from runtime-provided data

## Recommended transport abstraction

The runtime should expose a transport-neutral event stream contract that can later be bound to:

- in-process iteration for local clients
- HTTP chunked or SSE-style delivery
- WebSocket delivery

This document defines behavior, not the final wire protocol implementation.

## Invariants

- live delivery and replay share the same event vocabulary
- clients can show progress without parsing human-oriented text output
- final output does not replace the need for ordered event visibility

## Non-goals

- selecting one final wire protocol today
- post-MVP multi-agent multiplexing semantics
- token/cost telemetry transport requirements

## Acceptance checks

- the contract is sufficient to implement one live stream consumer and one replay consumer
- transport choices can change later without changing the event schema itself
- runtime persistence remains the source of truth for replay behavior
