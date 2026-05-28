# AGPL-3.0 notice — Forked PPTist in `web/`

`web/` will contain a fork of [PPTist](https://github.com/pipipi-pikachu/PPTist), licensed under AGPL-3.0.

## What the license requires

AGPL-3.0 §13 ("Remote Network Interaction"): when the modified software is made available to users **over a network**, the complete corresponding source — including our modifications — must be offered to those users.

This is stricter than GPL: it triggers on network use, not just distribution.

## What we accept for the confirmed pure-internal deployment

- The forked source, **with all our modifications**, MUST be kept in an internal repository accessible to every employee who can reach the service.
- A visible notice surfacing that source location MUST appear inside the PPT editor UI (e.g. a footer link "Source").
- `MODIFICATIONS.md` at `web/` must list what we changed (so source availability is meaningful, not just a tarball dump).
- We do NOT redistribute built binaries outside the organization without re-checking obligations.

> ⚠️ "Pure internal" is not an automatic AGPL exemption. The obligation runs to *users who interact with the software over a network*. Internal employees of a single legal entity are generally considered "the same user" in practice, but contractors, separate subsidiaries, or any external reachability changes the calculus. **Get one-line legal sign-off before merging the fork.**

## Swap-out plan if deployment ever turns external/commercial

1. AGPL §13 obligations would extend to all external users — we'd be forced either to publish the modified source publicly, or to obtain a commercial license from PPTist's author.
2. Cleaner option: replace `web/` with an in-house renderer that consumes the same `schema/slide_schema.json`. Because the Schema is the only interface between `web/` and the rest of the Skill, swapping it out does not require changes anywhere else.

## Files required at `web/` root when the fork lands

- `LICENSE.AGPL-3.0`
- `NOTICE` (PPTist copyright + our copyright)
- `MODIFICATIONS.md`
- `ALLOWED_HOSTS.txt` (any code we add must not pull in non-AGPL-compatible deps, since combined work stays AGPL)
