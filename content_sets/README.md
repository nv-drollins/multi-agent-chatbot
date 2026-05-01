# Matching Demo Content Sets

Use one case file at a time: upload the image, video, and document from the same set, run each specialist, then click **Build Briefing Page**.

To create lightweight local sample assets:

```bash
./scripts/create_case_files.sh
```

The generated files are written under `content_sets/demo-case-files/`. Each set includes one PNG image, one MP4 video under 30 seconds, and one TXT document.

## Set 1: Autonomous Vehicle Shuttle

- Image: synthetic perception snapshot from an autonomous shuttle route.
- Video: 24 second event clip showing the shuttle slowing near a curb lane object.
- Document: safety review notes for the same route event.
- Story: local agents inspect the scene, summarize safety evidence, and produce an event-review briefing.
- Included sample set:
  - `content_sets/demo-case-files/autonomous-vehicle-shuttle/autonomous-vehicle-shuttle.png`
  - `content_sets/demo-case-files/autonomous-vehicle-shuttle/autonomous-vehicle-shuttle.mp4`
  - `content_sets/demo-case-files/autonomous-vehicle-shuttle/autonomous-vehicle-safety-notes.txt`

## Set 2: Manufacturing Quality Inspection

- Image: synthetic robotic inspection cell with one flagged part.
- Video: 24 second conveyor walkthrough with the same inspection issue.
- Document: quality checklist for the same line and defect.
- Story: local agents package visual inspection evidence and process notes into a quality handoff.
- Included sample set:
  - `content_sets/demo-case-files/manufacturing-quality-inspection/manufacturing-quality-inspection.png`
  - `content_sets/demo-case-files/manufacturing-quality-inspection/manufacturing-quality-inspection.mp4`
  - `content_sets/demo-case-files/manufacturing-quality-inspection/manufacturing-quality-checklist.txt`

## Set 3: Media And Entertainment Virtual Production

- Image: synthetic virtual production stage with LED wall, camera marker, and props.
- Video: 24 second camera pass across the same stage setup.
- Document: shot-review notes for the same sequence.
- Story: local agents summarize visual continuity, production notes, and next actions for a stage supervisor.
- Included sample set:
  - `content_sets/demo-case-files/media-entertainment-virtual-production/media-entertainment-virtual-production.png`
  - `content_sets/demo-case-files/media-entertainment-virtual-production/media-entertainment-virtual-production.mp4`
  - `content_sets/demo-case-files/media-entertainment-virtual-production/virtual-production-shot-notes.txt`

## Why This Works Well On Stage

- Every file in a set points to the same case, so the final briefing feels coherent.
- The audience sees image, video, document, supervisor, and coding agents contribute evidence.
- The generated briefing is local and portable: it embeds evidence, excerpts, timeline, GPU snapshot, suggested next actions, and links to the local inventory pages.
