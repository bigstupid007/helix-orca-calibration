# V1 combined independent review

The program uses one combined substantial review, with bounded correction
rechecks. A fresh-context independent Codex reviewer reviewed the
integrated change from accepted main `523bc5d` through `d7634bf`. The reviewer
read the initiating scope, governing program, shared contracts and implementation;
it did not implement the reviewed changes. Founder acceptance remains pending.

The review identified five material issues. All five were corrected in the
integration branch and independently rechecked:

| Finding | Correction and verification |
| --- | --- |
| P1: restarted native UI could remain locked behind an equal status sequence | Explicit read-only coordinator reconciliation validates the entire retained binding, durably advances the current sequence once, and retains strict stale/replay rejection. Actual Coordinator-derived Review, Confirmed and Complete fixtures exercise restart recovery. |
| P2: Orca current selection could be confused with the original job/result context | Separate current selection, immutable active-job original context and retained result original context. Profile switching cannot retarget a job or result. |
| P1: intent consumption and its durable outcome could be separated by a crash | Confirm outcome/consumption are atomic. Start persists its complete pending intent and consumption with `starting` before dispatch. Cancellation consumption/uncertain transition is likewise atomic. |
| P1: future physical qualification could overlook transitive start-macro behavior | Typed qualification binds exact machine/configuration and reviewed static transitive macro sources, arguments and independent safe bounds. Dynamic, unresolved or recursive macro closure fails closed. No operational qualification or deployment grant was made. |
| P1: crash after owned adapter dispatch could orphan the same job | Read-only recovery adopts only an exact durably owned post-dispatch job and never repeats upload or Start. Missing/ambiguous/pre-dispatch ownership remains locked. |

The reviewer independently ran the then-current 26 owned-job tests, 11 native
checks, four recovery cases, two real Coordinator/HTTP-fixture crash cases and
three companion checks. They passed. HTTP/job evidence is synthetic; it does not
qualify a physical printer. Source corrections do not replace exact target-native
UI captures or actual generator parity.

Later integrated deltas include nullable same-job monitoring, native product
review corrections, the stock YOLO recipe correction and actual native-engine
build/generation. Their bounded final recheck and evidence disposition remain
pending. This document does not claim the entire current head has received that
final recheck.
