# PyPLECS story map

The long-term view: who needs what outcome, in what order. This is the North
Star and the shape of the journey toward it — nothing else.

## Rules of this file

Four rules. A change that breaks one of them does not belong here.

1. **Solution-neutral.** No component, topology, vendor, format, or protocol.
   A line that names a mechanism is a solution in disguise; the outcome it
   serves belongs here and the mechanism belongs in [`docs/adr/`](adr).
2. **No status.** Nothing here is "done", "planned", or "in progress". Status
   lives in the issue tracker and nowhere else.
3. **Survives the swap test.** Rewrite every ADR to choose the opposite option.
   If a line in this file changes, that line is duplicating an ADR — cut it.
4. **No stories.** Stories are issues. This file names the columns and the
   bands they sit in.

## North Star

> An engineer with a converter and a question gets a trustworthy answer for
> every case that matters — and never pays twice for the same one.

Two measures, both readable from stored state:

- **Repeat-work rate** — the share of requested cases answered without running
  the simulator again.
- **Answer traceability** — the share of delivered results whose exact
  producing inputs can be named after the fact.

A release that moves neither measure did not move the North Star.

## Who this is for

**The engineer with more cases than patience.** A power electronics engineer who
has a working converter model and a question that only has an answer across
tens or hundreds of operating conditions. They supply the circuit and the
judgment; they will not hand-drive a simulator that many times.

An automated caller driving PyPLECS on someone's behalf is real and secondary.
It hangs off this backbone; it does not define it.

## The backbone

The journey, left to right, in the order the engineer walks it.

| # | Column | The engineer's outcome |
|---|---|---|
| 1 | Bring a model | Points at a converter they already have and gets it running, without first learning how the tool wants to be driven |
| 2 | Say which cases matter | Names the conditions and parameter ranges worth exploring, in the terms they already use for them |
| 3 | Get answers at scale | Receives an answer for every case, at a cost that grows with the *new* cases rather than the total |
| 4 | Trust what came back | Can tell what produced any result, and whether it still applies to the model as it stands now |
| 5 | Read the meaning | Gets the quantities the design decision actually turns on, not raw traces to post-process |
| 6 | Work where they already work | Consumes results from their own environment, without adopting a new one |

## Bands

Depth, not dates. Each band deepens columns that already exist rather than
adding new ones to the right.

**Band 1 — the answer arrives.** Every column is walkable end to end for one
model and one set of cases. The engineer gets numbers back and can act on them.

**Band 2 — the answer is cheap.** Column 3 deepens until repeat work is the
exception. Column 4 deepens with it, because an answer reused is only as good
as the identity that justified reusing it.

**Band 3 — the answer is legible.** Column 5 deepens: results arrive as the
design quantities the engineer was actually asking about. Column 6 widens to
the environments they work in.

**Band 4 — the answer holds up.** Every column survives failure, scale, and a
model that changed underneath it. Nothing new appears; what exists stops
surprising anyone.
