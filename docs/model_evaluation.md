# Model evaluation for V1.1

V1.1 is not ready to release until a local model passes the regression that prompted the update. General chat benchmarks do not establish suitability for precise description shortening.

## Selection method

Use the same fictional screening cases in public demos and local tests. Measure character counts in code. Review names, quantities, negation, chronology, approximation, causal relationships, and intended versus completed actions. Reject incomplete sentences and invented details. Then test the actual private regression locally, including repeated runs, warm latency, and the distributed quantization. Keep private inputs and raw transcripts in ignored `build/qa`.

## Findings on October 9, 2026

| Candidate | Evidence | Status |
| --- | --- | --- |
| Qwen3 4B Instruct 2507 Q3_K_M | Existing V1.0 model fails the long narrative regression. | Replace for V1.1. |
| Qwen3.5 2B Q6_K and 4B Q4_K_M | Local tests failed the narrative. The 4B model also passed its own review of a draft that omitted enjoyment. | Not qualified. |
| Qwen3.5 9B Q4_K_M | Three initial narrative drafts measured 131, 125, and 130 characters. Additional compact prompts and thinking tests did not resolve the regression. Several product cases passed. | Comparison candidate; not qualified. |
| Mistral Small 3.2 24B UD-IQ3_XXS | Three initial local drafts measured 119, 125, and 135 characters. Further editing trials omitted or invented details. | Not qualified. |
| gpt-oss-20b | Exact-model hosted demo, low reasoning: fictional narrative drafts omitted approximation, enjoyment, or vacation/living details. Medium reasoning test could not run after the anonymous quota was exhausted. | No local download yet; medium reasoning untested. |
| Granite 4.2 30B | Official playground identifies this exact model for all three comparison modes. Fictional narrative: reasoning off 145 characters; light reasoning 116 characters and omitted approximation. Full reasoning: 109 characters, omitted approximation and the article before vacation home, and took 523.6 seconds. Hosted latency is not local latency. | No local download yet. |
| Gemma 4 12B official QAT Q4_0 | Official Apache 2.0 GGUF, approximately 7 GB; local evaluation completed. Its hosted demo uses ZeroGPU, whose anonymous quota was exhausted during earlier screening. | Local six-case screen: five product checks passed; narrative omitted enjoyment. Actual regression trials omitted details or invented a patio. Not qualified. |

These are screening observations, not claims that a model cannot succeed with any other prompt or configuration. One passed example is insufficient to qualify a model.

## Primary sources

- [Qwen3.5 9B](https://huggingface.co/Qwen/Qwen3.5-9B)
- [Mistral Small 3.2 24B](https://huggingface.co/mistralai/Mistral-Small-3.2-24B-Instruct-2506)
- [gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b) and [exact-model demo source](https://huggingface.co/spaces/merterbak/gpt-oss-20b-demo/blob/main/app.py)
- [Granite playground](https://www.ibm.com/granite/playground) and [Granite 4.2 documentation](https://www.ibm.com/granite/docs/models/granite4-2)
- [Gemma 4 12B model card and generation guidance](https://huggingface.co/google/gemma-4-12B-it), [official QAT GGUF](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf), and [hosted demo source](https://huggingface.co/spaces/huggingface-projects/gemma-4-12b-it/blob/main/app.py)

The final app must run fully locally. Online demos are development screening tools only.

## V1.1 selection, October 12, 2026

The user explicitly allowed incidental enjoyment to be omitted. The final engine protects the main meaning and material facts, including names, specifications, quantities, approximation, location, and original actions or intentions. This clarification changes how narrative candidates are judged; the earlier strict all-detail failures should not be treated as failures under the revised task.

Gemma 4 12B official QAT Q4_0 passed all eleven local benchmark cases using word-budget guidance, bounded revision with exact character feedback, conservative whole-phrase/unit compaction, and separate material-fact review. The actual private regression passed three times with the result cache cleared, each at 108 characters. Model load took 5.57 seconds; the first generation/review after load took 14.32 seconds, and warm repeats took 7.11 and 7.13 seconds on the 16 GB M3 Mac. These are observations, not universal latency promises.

The selected immutable GGUF revision is `29d097773436b69ff9feafd636ab4cf873786537`, file `gemma-4-12b-it-qat-q4_0.gguf`, SHA256 `93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b`. The exact word count is guidance; the 110-character count is a hard return/export gate. No partial sentence is cut off to meet it. Source inputs stay immutable.
