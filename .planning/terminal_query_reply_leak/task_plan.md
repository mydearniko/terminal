# Task Plan: Eliminate terminal-query reply leakage without disabling functionality

## Goal
Identify and fix the actual Windows Terminal/ConPTY failure that turns VT query replies into apparent keyboard input in tmux, Codex, and other TUIs, while preserving standards-compliant query responses and unrelated input behavior.

## Current Phase
Complete

## Phases

### Phase 1: Reproduce and characterize every symptom
- [x] Read OpenAI Codex issue #31420 and linked evidence/comments
- [x] Record the complete byte streams corresponding to `11;rgb:...`, `52c`, and any other leaked fragments
- [x] Reproduce direct, tmux, and Codex-like startup query paths with timing/fragmentation instrumentation
- [x] Confirm the installed artifact contained the prior BEL change and determine why it was insufficient
- **Status:** complete

### Phase 2: Trace the full query/reply and input-delivery architecture
- [x] Inventory every VT query that can call `ReturnResponse`, not only OSC color queries
- [x] Trace serialization from parser dispatch through ConPTY/input records to the application
- [x] Determine whether loss, fragmentation, interleaving, timeout, or application parser behavior is the root cause
- [x] Compare behavior/spec expectations with other terminals and tmux passthrough
- **Status:** complete

### Phase 3: Choose a compatibility-preserving design
- [x] Evaluate fixes at the correct abstraction layer rather than per escape sequence
- [x] Preserve supported OSC/CSI/DCS replies, C1/S7 modes, keyboard protocols, clipboard, shell integration, and ordinary input
- [x] Define explicit byte-level and ordering invariants
- [x] Document the chosen design and rejected alternatives with regression risks
- **Status:** complete

### Phase 4: Implement focused source and regression-test changes
- [x] Implement the smallest root-cause fix
- [x] Add tests covering the exact OSC 11 and primary-DA reply shapes at every split point
- [x] Add an input-engine regression test proving one downstream input batch
- [x] Remove the prior BEL workaround and restore canonical ST replies
- **Status:** complete

### Phase 5: Validate behavior and functionality
- [x] Run local formatting and workflow/installer syntax checks
- [x] Run the Windows adapter/parser/input unit suites
- [x] Run live direct PTY, tmux, and Codex/TUI reproductions under adverse timing
- [x] Verify all query response contents and modes remain functional
- [x] Build and smoke-test the signed Windows package/installer if delivery is authorized
- **Status:** complete

### Phase 6: Delivery and handoff
- [x] Review the final diff and evidence against every acceptance criterion
- [x] Provide a replacement installer and round-trip checksum if delivery is in scope
- [x] Deactivate planning mode only after all required checks and delivery are complete
- **Status:** complete

## Acceptance Criteria
- ConPTY no longer manufactures a reply boundary between a cached sequence prefix and its completing parser run, so the observed `11;rgb:...`, `52c`, and stranded-Escape failure shapes are forwarded in one input-buffer transaction at the layer controlled by this fork.
- The fix applies across relevant VT query families rather than special-casing only OSC 11.
- Standards-compliant terminal queries still receive correct replies with correct ordering and mode-sensitive encoding.
- Ordinary keyboard/mouse/paste/clipboard/shell-integration behavior is unchanged.
- New tests fail on the old behavior and pass with the fix, including fragmented and interleaved delivery.
- Windows-native build and relevant full test suites pass before any replacement artifact is delivered.

The acceptance boundary is intentionally transport-correct rather than absolute: a PTY/SSH connection remains a byte stream, and an application can still abandon a partial reply before an arbitrarily delayed tail arrives. Preventing that Codex #31420 case under synthetic delays beyond its own 100 ms handoff requires a Codex-side incremental parser; suppressing or rewriting terminal replies would violate the no-functional-degradation requirement.

## Key Questions
1. What complete escape sequences produce the observed tails `11;rgb:...` and `52c`?
2. Are bytes fragmented, reordered, delayed past application timeouts, or intentionally reinterpreted as input?
3. Is the fault in Windows Terminal response generation, ConPTY input transport, tmux passthrough/parsing, or Codex's terminal-query parser?
4. What is the lowest shared layer where ordering/atomicity can be guaranteed without disabling replies?
5. Does the prior BEL terminator change improve, worsen, or merely move the symptom?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Do not add another per-sequence terminator workaround before byte-level reproduction | The previous OSC-only BEL change did not address `52c` or the cited Codex failure, so the shared transport/query path must be understood first. |
| Treat functionality preservation as an explicit test surface | Disabling color/device/status queries would hide the symptom while regressing terminal capabilities. |
| Reassemble cached and completing parser runs before pass-through | The old two-callback path created an avoidable ConPTY input-buffer wake boundary even though the terminal generated a complete response. Concatenation preserves identical bytes and order while reducing delivery to one transaction. |
| Restore 7-bit OSC replies to the existing ST encoding | BEL was a standards-valid but unnecessary response-byte change that did not address CSI replies or arbitrary splits. The shared fix makes the compatibility change unjustified. |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| Prior delivered fix changed only 7-bit OSC replies to BEL, but the user still sees OSC 11 and non-OSC `52c` fragments | Previous task | Reopen investigation at the shared query-response/input transport layer and require multi-family reproductions. |

## Notes
- Planning mode must remain enabled while work is incomplete.
- Re-read this plan before every major design or implementation decision.
- Log every failed reproduction or validation attempt rather than retrying unchanged.
