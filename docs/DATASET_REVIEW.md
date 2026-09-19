# Dataset review — dental-xray-dataset (shreku, Roboflow v1)

Reviewer: manual visual check of 20 sampled train images containing periapical_lesion boxes.

## Train split stats
- images: 6826
- empty label files (negatives): 902
- total boxes: 10967 (pre-fix count; rises slightly after wrapped-line parser fix)
  - caries: 8456
  - periapical_lesion: 2511
- label files with wrapped/multi-box lines: 40 (now parsed correctly by our tools)

## Visual verification result: PARTIAL PASS — accepted as pass with known limitations
- ~15/20 sampled boxes correctly sit on periapical / apical radiolucent regions.
- ~5/20 boxes sit on cervical / interproximal dark bands (cervical burnout) or
  crown-adjacent tooth structure, not on periapical bone.

## Known limitations accepted for V1
- Training labels contain an estimated ~20-25% mislabeled periapical_lesion boxes.
- Expected effect: some false positives on cervical burnout / interproximal shadows.

## Mitigations (in order)
1. Confidence threshold tuning after validation.
2. Human-in-the-loop Confirm / Dismiss / Adjust in the demo.
3. Post-training error review; targeted curation only if validation shows the
   label noise dominates the error profile.

## Decision
Proceed to training. No upfront label curation. Revisit after first validation metrics.