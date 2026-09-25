# Progress Log: Terminal query reply leakage

## Session: 2026-07-24

### Phase 1: Reproduce and characterize every symptom
- **Status:** complete
- **Started:** 2026-07-24
- Actions taken:
  - Activated explicit planning mode with `$planning`.
  - Read the planning and planning-with-files skills completely.
  - Ran session catch-up and reviewed repository-specific memory about the fork and installer.
  - Created this scoped plan with byte-level, multi-query, and no-regression acceptance criteria.
  - Read OpenAI Codex issue #31420 and all current comments via the GitHub API.
  - Mapped the observed `52c` tail to Windows Terminal's exact primary Device Attributes response.
  - Inventoried response producers and established that OSC-only termination cannot cover the affected query families.
  - Checked out tmux 3.5a and 3.6b sources for version-specific parser comparison.
  - Confirmed tmux itself solicits OSC 10/11 replies during startup and marked the earlier forced upgrade to 3.6b as a test-coverage gap.
  - Narrowed tmux 3.5a/3.6b source comparison to client-terminal reply parsing and confirmed both BEL and ST are recognized for OSC 10/11.
  - Traced response generation into `Terminal::ReturnResponse()`, which forwards a complete response through one write-input callback.
  - Completed the downstream trace through `ControlCore::_pendingResponses` and `ConptyConnection::WriteInput()`: one accumulated response batch, FIFO serialization, one UTF-8 `WriteFile`.
  - Read tmux 3.5a/3.6b timeout code and identified the 3.6 active-query minimum of 500 ms absent from 3.5a.
  - Found the exact upstream reports for the tmux symptom (Terminal #18004/#19282 and Win32-OpenSSH #2275) and the two transport fixes: 16→1024 input records (#771) and the `SIGWINCH` partial-write retry fix (#806).
  - Confirmed the current source already includes Terminal's response batching, raw reply pass-through, and ConPTY stdin waiter-race fixes.
  - Established the design boundary: a PTY is a byte stream and cannot preserve a terminal write as one application read; a universal Terminal-only workaround would suppress or alter valid functionality.
  - Re-ran the tmux matrix: tmux 3.5a with `escape-time 0` leaked a response split by 20 ms; tmux 3.5a at 50 ms and tmux 3.6b at 0 ms did not.
  - Re-ran Codex 0.145.0 with 50, 120, 350, and 550 ms synthetic DA delays. The 50 ms response completed during probing; the three post-deadline cases reproduced the status-0 trust-prompt exit.
- Files created/modified:
  - `.planning/.active_plan`
  - `.planning/terminal_query_reply_leak/task_plan.md`
  - `.planning/terminal_query_reply_leak/findings.md`
  - `.planning/terminal_query_reply_leak/progress.md`

### Phase 2: Trace architecture
- **Status:** complete
- Actions taken:
  - Traced response construction, TerminalCore callback batching, ControlCore flush ordering, ConPTY UTF-8 conversion, ticket-lock serialization, overlapped pipe write, input state-machine pass-through, and input-buffer insertion.
  - Compared the actual transport with Microsoft Terminal's #19282 maintainer analysis and Win32-OpenSSH's fixed read/write bugs.
  - Identified `StateMachine::FlushToTerminal()` as an additional concrete ConPTY boundary: cached prefix and completing run were passed into `InputBuffer::WriteString()` separately.
- Files created/modified:
  - None yet.

### Phase 3: Choose design
- **Status:** complete
- Actions taken:
  - Defined the invariant as exact byte/order preservation with one parser pass-through transaction for a completed split sequence.
  - Rejected response suppression, query disabling, synthetic terminator changes, global delays, and unsafe system-SSH replacement.

### Phase 4: Implement and test
- **Status:** complete
- Actions taken:
  - Reassembled cached and completing state-machine runs before `ActionPassThroughString()`.
  - Added exhaustive OSC 11 and primary-DA split-boundary coverage plus an actual input-engine batch-count test.
  - Restored canonical OSC ST response bytes and matching adapter expectations.
  - Added parser unit-test build/run steps to Windows CI.
  - Extended installer provenance while retaining its validated `Install.ps1` one-click flow.
  - Re-audited the full diff and moved concatenation into `_SafeExecute`, so allocation failure follows the parser's existing exception-safe path.
  - Removed incidental adapter-test renaming; relative to `origin/main`, canonical OSC response code and expectations are byte-for-byte restored.
  - Renamed the focused parser test to avoid claiming PTY/network atomicity; it asserts one ConPTY pass-through call.

### Phase 5: Validate
- **Status:** complete
- Actions taken:
  - Re-fetched `origin`; the task branch is exactly synchronized with its remote base and four commits ahead of `origin/main` before this fix.
  - Reconfirmed OpenAI Codex issue #31420 is still open as of 2026-07-24; no released terminal can override its application-owned 100 ms stdin handoff.
  - Reconfirmed Win32-OpenSSH fixes #771 and #806 are separate transport fixes; silently replacing system SSH remains outside this Terminal installer's authorized scope.
  - Passed CRLF-aware diff checks, `clang-format --dry-run --Werror`, Ruby YAML parsing, and PowerShell parsing of the embedded `Install.ps1`.
  - Prepared the focused changes for the Windows build and unit-test gate.
  - Repeated the adverse-timing matrix: tmux 3.5a at 0 ms leaked the deliberately split OSC reply, tmux 3.5a at 50 ms and tmux 3.6b at 0 ms did not; Codex 0.145.0 failed at 120/350 ms and normally at 550 ms, while a single 550 ms run survived before five consecutive reruns failed as expected.
  - Pushed the focused fix and CI coverage as `16927423d` and `4e70e5743` on `codex/osc-response-installer`.
  - GitHub Actions run 17 completed successfully at commit `4e70e57431e40175f2b77e44d1e4b9a79847560c`; package build, adapter tests, parser tests, installer validation, elevated installation smoke test, and artifact upload all passed.
  - Independently audited artifact `8586380938`: exact ten-file inventory, no traversal/duplicate/case-collision entries, clean ZIP CRC, and all nine payload hashes matched `SHA256SUMS.txt`.
  - Parsed `Install.ps1`, verified MSIX identity `WindowsTerminalDev` version `0.0.17.1` architecture `x64`, cryptographically checked the one-signer CMS signature, and confirmed the bundled certificate is byte-identical to the embedded signer certificate.
  - Verified the bundled Twemoji font identifies as `Twemoji Mozilla`; fresh downloads of the pinned v0.7.0 font and license matched the bundled files byte-for-byte.
  - Re-reviewed the focused source diff and exception path; no corrective follow-up was required.

### Phase 6: Delivery
- **Status:** complete
- Actions taken:
  - Renamed the unchanged GitHub artifact to `WindowsTerminal-Installer-x64-v0.0.17.1.zip` without recompression.
  - Uploaded it through `idoud` to `https://idoud.cc/1RbATt/WindowsTerminal-Installer-x64-v0.0.17.1.zip`.
  - Downloaded the public URL into a separate directory and verified exact size `14,645,934`, SHA-256 `6688c09ca44e7c6e544a97a7f926235f161ee09a6591017005cc8afaf5663c92`, byte-for-byte equality, ZIP CRC, and inventory.
  - Confirmed the branch is synchronized with `origin/codex/osc-response-installer`; only the preserved untracked `.planning/` records remain in the worktree.

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Planning activation | `planning-mode.sh on` | Marker enabled | `.planning/.pwf-enabled` present | Passed |
| Codex issue evidence mapping | Issue trace tail `2;23;24;28;32;42;52c` | Identify full response | Exact suffix of Terminal PDA payload `ESC[?61;4;6;7;14;21;22;23;24;28;32;42;52c` | Passed |
| Terminal response serialization audit | One generated response batch must not be split or interleaved by Terminal's own writer | One `_pendingResponses` flush and one locked `WriteFile` | Confirmed in current source | Passed |
| tmux parser compatibility audit | OSC 10/11 response accepted with BEL and ST | Both terminators recognized; partial reply timeout isolated | Confirmed in 3.5a and 3.6b; 3.6b adds 500 ms active-query floor | Passed |
| tmux adverse timing rerun | 3.5a/0 ms, 3.5a/50 ms, 3.6b/0 ms with a 20 ms response split | Only the short-timeout old parser leaks | leak / no leak / no leak | Passed |
| Codex adverse timing rerun | DA tail delays of 50, 120, 350, and 550 ms | Complete-before-deadline survives; post-deadline tails reproduce issue #31420 | survived / exited 0 / exited 0 / exited 0 | Passed |
| Formatting | Changed C++ parser/adapter sources and tests | Repository clang-format clean | `clang-format --dry-run --Werror` passed | Passed |
| Workflow and installer syntax | Updated build workflow and embedded `Install.ps1` | Valid YAML and PowerShell syntax | Ruby YAML parse and PowerShell ScriptBlock parse passed | Passed |
| Windows-native CI | Run 17 at `4e70e57431e4` | Package, adapter/parser suites, validation, and install smoke test pass | Every relevant GitHub Actions step completed successfully | Passed |
| Installer cryptographic audit | MSIX, certificate, dependency, font, and checksums | Exact identity, signer, pins, and complete payload inventory | All independent local checks passed | Passed |
| Public artifact round trip | idoud release URL | Served archive equals audited GitHub artifact | Exact byte comparison and SHA-256 match | Passed |

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-07-24 | Prior OSC BEL-only fix did not eliminate the installed-user symptom and did not cover `52c` | Previous task | Restarted from full query/reply transport investigation; no new code changes yet. |
| 2026-07-24 | Broad tmux/Terminal response-path output was truncated before all relevant functions | 1 | Switched to narrow function-level reads for the next investigation step. |
| 2026-07-24 | `gh` was not installed for issue searches | 1 | Used unauthenticated GitHub REST API queries with `curl`/`jq`. |
| 2026-07-24 | One Codex 550 ms synthetic-delay run survived while the surrounding delayed runs exited | Revalidation | Repeated 550 ms five times and 350 ms three times; all eight reproduced the issue, confirming timing sensitivity rather than a stable boundary. |

## 5-Question Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | Complete: audited installer delivered and round-trip verified |
| Where am I going? | User installation and real-environment confirmation |
| What's the goal? | Eliminate apparent query-reply typing without disabling terminal functions |
| What have I learned? | ConPTY had one avoidable two-callback boundary; arbitrary PTY/network delay and Codex's reader handoff remain application/transport concerns |
| What have I done? | Implemented one-transaction pass-through, restored exact reply bytes, exhaustively tested split points, passed Windows CI, and delivered a verified installer |
