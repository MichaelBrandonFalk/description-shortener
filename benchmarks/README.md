# Model screening

Screen models before downloading or packaging them. Use the same editing rules, cases and settings for each candidate.

1. Confirm the demo's exact model ID, including parameter size. Check its source when a community demo's title is ambiguous. Exclude altered/uncensored/fine-tuned variants unless that exact variant is the candidate.
2. Supply the app's editing rules as the system prompt. Run the cases in `cases.json` separately. Repeat the difficult cases in fresh chats to check consistency.
3. Save hosted answers as a JSON object of case IDs to output strings in ignored `build/qa/`. Run `scripts/model_eval.py --responses build/qa/answers.json` to measure length, punctuation, numeric preservation and specified details. Read every answer for grammar, complete meaning, close wording and causal relationships; the pattern checks are only screening aids.
4. Download only promising finalists. Run the same cases with `scripts/model_eval.py --model vendor/finalist.gguf`. Test the exact runtime, model checksum, quantization and settings that will ship. Measure cold startup and warm latency separately. Hosted latency does not predict Mac performance.
5. Add the actual reported failure as a private local regression case. It must pass before a replacement is released. Test the packaged helper, supported files and native views, then build the immutable version.

Online screening does not change the final app's fully local processing. Never submit confidential customer content to public demos. Use invented cases for online screening and keep actual inputs in local ignored QA files.

## Material facts and multipass guidance

The user clarified on October 12, 2026 that enjoyment may be omitted during shortening. Protect material facts, names, quantities, specifications, locations and the main action or intention. Incidental narrative sentiment is optional; product attributes are not. Keep the original tense and do not turn a proposed addition into a completed action.

Use a soft word target for drafting and measured character feedback for revision. The 110-character limit is a hard return/export gate. Never meet it by slicing text or forcing a sentence to stop midway. A valid result may exceed its soft word target if the complete sentence and material facts fit within 110 characters.
