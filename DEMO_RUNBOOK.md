# Volta Memory Demo Runbook

## Goal

Show one complete, verifiable correction lifecycle—not a dashboard tour.

## Preflight

- Use the deployed HTTPS app, an incognito window, and a desktop viewport.
- Close DevTools, terminal windows, bookmarks, and browser extensions that expose internal state.
- Confirm `/health` is green, the public runtime config names the API Gateway origin, and the showcase is read-only.
- Verify the selected demo memories have **real, verified source quotes**. Do not record a fallback message such as “source quote is not available.”
- Run the release smoke test after the final deployment. If an API request fails, do not switch to localhost or a seeded admin control on camera.

## Three-minute flow

1. **Problem (0:00-0:20):** “Long-lived agents fail when they replay stale history or keep every irrelevant detail. Volta remembers evidence, not assumptions.”
2. **Initial session (0:20-0:50):** confirm “My bill is R3,200; keeping lights on during load-shedding is my priority.”
3. **Correction (0:50-1:15):** say “Actually, my bill is R3,800.” End the consultation.
4. **Receipt (1:15-1:35):** show `R3,200 -> R3,800`, a verified quote and turn, and the statement that the earlier value is retained for accountability but is not eligible for advice.
5. **Memory Map (1:35-2:05):** inspect both nodes. The current fact must say **Replaces**; the predecessor must say **Replaced by**. Follow the accessible timeline as the non-canvas proof.
6. **Next-session answer (2:05-2:30):** ask for an energy recommendation. Open **Why this advice** and show R3,800 and the lights-on priority as used evidence. Show the older bill as not used because it is superseded.
7. **Close (2:30-3:00):** show the architecture and one honest benchmark slide. Say the database supersession result and selective-forgetting comparison, then state the recall/latency trade-off rather than hiding it.

## Recording acceptance checks

- No localhost URL, shell, evaluation route, reset control, or shared mutable seed account appears.
- Profile, receipt, Memory Map, timeline, and answer trace agree on the same current value and status.
- Every “used” tag is backed by the answer trace.
- No automated text-to-speech plays without an explicit user action.
- The public video is uploaded and opened in a logged-out browser before its URL is added to [SUBMISSION.md](SUBMISSION.md).
