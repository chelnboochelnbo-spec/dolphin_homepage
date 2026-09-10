# DOLPHIN Publication Agent Contract

When the owner supplies a new event in ChatGPT, treat the message as a publication job unless they explicitly say it is only a draft or consultation.

## Job sequence

1. Normalize the event into the `automation/event-template.json` shape.
2. Validate required fields and classify `type` as LIVE, SESSION, or LIVE&SESSION.
3. Resolve the flyer branch:
   - `human`: use the supplied finished flyer unchanged except for file optimization/format conversion when needed.
   - `canva_ai`: use Canva to create the flyer from event information and supplied artist photos. Keep DOLPHIN visual consistency; do not invent performer names, prices, dates, or times.
4. Store the final flyer in GitHub using `flyer_YYYYMMDD.ext` or an unambiguous suffix for same-day multiple events.
5. Upsert the event into `data/events.json` and set `status` to `ready` only when the flyer is final.
6. Commit the website/data update and verify Vercel deployment status.
7. Generate Instagram and Facebook captions from the canonical event record.
8. Calculate posting times using `automation/social-policy.json`.
9. Schedule both platforms through the connected social scheduler.
10. Write publication state, scheduled timestamps, post IDs when available, website commit SHA, and Vercel result back into `data/events.json`.
11. After the event date, the website runtime automatically exposes the event in Archive; mark the record `completed` during the next maintenance run.

## Idempotency

Before every mutation, search by `event.id` and date/title. Re-running the same job must update the existing record rather than create a duplicate.

## Human approval boundaries

Approval is required only when an external connector explicitly requires it or when supplied event information is materially ambiguous. Routine GitHub updates, Vercel verification, caption generation, and already-authorized scheduling should proceed without asking repetitive questions.

## Failure handling

A failure in Canva or social scheduling must not roll back a successful website publication. Record partial state and continue independent steps. Report only the failed or blocked step with the exact missing dependency.
