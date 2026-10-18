# Case study: AI-assisted character image edits for a production client

*Real paid work. Client, task IDs, images and names are withheld; this page describes only the process and what we learned.*

## The job

A client sends 3D-rendered character art, one character per task, with a written template and per-task notes. Each task needs a small set of derived images in a fixed house style: two expression variants, the character holding a requested object, a simplified "rough" version with blob-shaped hands, and an empty themed background. The client's project manager (PM) reviews every file and can ask for reworks.

## Pipeline

1. **Pin the inputs.** Original render, task notes, the client's style template and any PM reference images are hashed and recorded before any edit.
2. **Generate with the approved route.** New variants are produced with Google Gemini image editing (the client-approved "Flash image" route). The exact prompt, input and reference images are logged for every call.
3. **Sample, don't settle.** Three candidates are generated per file, and the best is selected at native resolution against the source and the PM reference. A single "good enough" draw is not accepted.
4. **Local, deterministic repairs.** Small fixes (eyebrow outlines, a contact edge, line clean-up) are made with masked, scripted edits rather than a full regeneration, so pixels that must not change stay byte-identical.
5. **Two separate review gates.**
   - *Semantic gate:* a person-style visual review at 1024 px beside the source and the PM reference, then zoomed checks of the face, hand/prop contact and edit boundaries.
   - *Technical gate:* protected-region masks, hashes, file count/size and the packaging check.
   - Passing the technical gate never implies passing the semantic one.
6. **Independent second review** by a separate agent before anything is delivered. A producer's "pass" is evidence, not the decision.

## What went wrong, and what changed

Several deliveries passed our internal checks but were still sent back by the client. We treated each rejection as data:

- **14 defect classes** were recorded with evidence, cause and corrective rule. Examples:
  - wrong anatomical side;
  - unnatural hand-prop contact or occlusion;
  - an incomplete or unrecognisable prop;
  - broken contours and texture noise;
  - expression geometry (outlined, curved brows; correct mouth fill);
  - excessive pattern detail;
  - not using the client's template or requested model;
  - repeated failed revisions on the same file.
- **33 logged iterations** in an append-only ledger: each records the failure, the old rule, the new rule and how it was verified.
- **Historical replay:** earlier rejected files were re-run through the new checklist to confirm the revised gates would now HOLD them. The old metric-heavy checks (finger counts, "zero pixels changed outside the mask") had let them through.
- **The checklist went through six versions.** The biggest lessons:
  - pixel-preservation metrics are necessary but say nothing about whether the image is *right*;
  - client-specific calibration (for example, a mechanical-hand prop that needs articulated fingers while the character's own hand stays a simple blob) must be written down per task and never generalised silently;
  - when no compliant candidate exists, the correct output is a documented HOLD, not a quiet scope expansion.

## Results we can state honestly

- Tasks were delivered and reworked through the client's PM process, and reworks were turned around the same day.
- The process artefacts (checklist, defect register, QA template, iteration ledger) exist and are versioned. Internal agreement on them **does not** prove future client acceptance, and we do not claim it does.

## Skills shown

AI image-editing workflows with prompt and reference logging · multi-candidate sampling and selection · masked deterministic repair · protected-pixel and hash verification · structured defect tracking with root-cause analysis · two-gate QA with independent review · honest HOLD/rework handling.
