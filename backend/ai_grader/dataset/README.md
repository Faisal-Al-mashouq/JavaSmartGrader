# JavaGrader Fine-Tuning Dataset

Dataset README and integration notes for the AI grader dataset stored in this
folder.

This README serves two purposes:

1. It records what changed in the repository to support this dataset format.
2. It documents the dataset itself in a dataset-card style, based on the
   attached `dataset_card_v4.docx`.

## 1. Change Summary

The repository changes around this dataset were made so the runtime
`ai_grader` worker can use the dataset contract without forcing the rest of the
backend to adopt the dataset schema directly.

### Codebase Changes Made

Repository change stats at the time of writing:

- `12` tracked files modified since the last commit
- `5` untracked files in this dataset area
- `784` lines inserted
- `187` lines deleted
- `20` passing tests in the latest `ai_grader` test run

Main changes made:

- `backend/ai_grader/llm_client.py`
  - aligned the system prompt wording with the dataset format

- `backend/ai_grader/prompt_builder.py`
  - replaced the old prose grading prompt with a dataset-style JSON user
    message
  - aligned the repair prompt with the dataset response contract

- `backend/ai_grader/main.py`
  - added logic to build dataset-style `evaluation` content from sandbox
    results
  - preserved the normalized runtime completion payload expected by the rest of
    the backend

- `backend/ai_grader/schemas.py`
  - added dataset-facing response models
  - added normalization into the existing runtime grading schema

- `backend/ai_grader/parser_validator.py`
  - updated validation to accept dataset-style responses and normalize them

- `backend/ai_grader/test.py`
  - updated tests to cover dataset prompt building, parsing, normalization, and
    evaluation construction

- `backend/core/job_queue.py`
  - re-enabled the final result stage

- `backend/core/process/grader.py`
  - removed direct success persistence from the grader stage

- `backend/core/process/final_result.py`
  - added final persistence logic for normalized AI grading results

- `backend/Dockerfile`
  - disabled the previous database-init entrypoint path for the backend image

These changes follow one design rule:

- use the dataset format at the model boundary
- normalize back into the existing runtime contract before persistence

That keeps the wider backend stable while still letting the fine-tuning dataset
drive the model-facing request and response structure.

## 2. Overview

This dataset fine-tunes a Java grading model for automated assessment of
student-written Java methods.

The dataset is designed to teach a model to:

- assess Java submissions against instructor-defined rubrics
- assign criterion-by-criterion scores
- justify grading decisions using code and execution evidence
- generate student-facing feedback
- classify error types such as OCR, compile, runtime, and logic failures
- estimate confidence based on evidence quality and availability

The attached dataset card describes this dataset as:

- version `4`
- dated `April 2025`
- intended for GPT-4.1 nano supervised fine-tuning
- distributed as `4` JSONL file variants

## 3. Files In This Folder

The dataset currently contains `4` JSONL files plus the source dataset card:

- `train_set.jsonl`
- `train_set_nodup.jsonl`
- `val_set.jsonl`
- `val_set_nodup.jsonl`
- `dataset_card_v4.docx`

Local file stats:

| File | Records | Size (bytes) | Recommended use |
|---|---:|---:|---|
| `train_set.jsonl` | 750 | 2,923,448 | standard supervised fine-tuning |
| `train_set_nodup.jsonl` | 750 | 2,959,587 | deduplication-sensitive training |
| `val_set.jsonl` | 150 | 585,926 | standard validation |
| `val_set_nodup.jsonl` | 150 | 591,130 | leakage-reduced validation |

High-level dataset totals:

- `1,800` JSONL records stored across all four files
- `900` records per variant family
- `750` train examples per training file
- `150` validation examples per validation file
- train:validation ratio of `5:1`

## 4. Dataset Variants

The dataset is split into two paired variants.

### Base Variant

Files:

- `train_set.jsonl`
- `val_set.jsonl`

Properties:

- code bodies may repeat across examples
- the same method body may appear under different rubric conditions, notes, or
  grading contexts
- suitable for standard fine-tuning when repeated code bodies are acceptable

### Deduplicated Variant

Files:

- `train_set_nodup.jsonl`
- `val_set_nodup.jsonl`

Properties:

- every code body is intended to be unique
- uniqueness is achieved using variant markers and local code perturbations


This variant is useful when you want to reduce code-body leakage and make the
model rely more on grading behavior than memorized code patterns.

## 5. Data Sources And Construction

According to the attached dataset card, the dataset was shaped by four main
reference influences:

- code quality corpora from GitHub for realistic Java style and non-style
  patterns
- MIGATE rubric templates for rubric language and criterion vocabulary
- OCR transcription error studies for realistic handwritten-code corruption
- CSC111 Java exercise catalogs for task selection and expected algorithm families

The dataset card also states that examples were generated with a multi-pass
LLM-assisted process using GPT-4.1 and GPT-4.1 nano with explicit controls for:

- bug patterns such as:
  - `boundary_logic`
  - `syntax_compile`
  - `runtime_exception`
  - `multiple_logic`
  - `missing_return`
  - `wrong_algorithm`

- realistic sandbox logs with explicit input/output evidence
- criterion-specific rubric comments
- variable rubric sizes and point scales
- OCR noise injection
- instructor focus note injection

Reported generation controls from the dataset card:

- instructor focus notes appear in exactly `40%` of examples
- OCR corruption appears in exactly `30%` of examples
- rubric totals vary across `10`, `40`, `50`, and `100`
- rubric structures include `3`, `4`, and `5` criteria

## 6. Coverage

### Topic Coverage

The dataset card reports full coverage of `26` CSC111-level Java topics in both
train and validation.

Topic list:

- `average`
- `binarySearch`
- `bubbleSort`
- `countOccurrences`
- `countVowels`
- `factorial`
- `fibonacci`
- `findMax`
- `findMin`
- `gcd`
- `getLetterGrade`
- `isEven`
- `isPrime`
- `lcm`
- `linearSearch`
- `maxElement`
- `mergeSort`
- `palindrome`
- `power`
- `removeDuplicates`
- `reverseString`
- `safeDivide`
- `sum`
- `sumNegatives`
- `twoSum`
- `wordCount`

The card notes that each topic appears roughly `24-28` times in training and
`5-6` times in validation.

### Label And Scenario Coverage

Reported coverage highlights:

- OCR examples:
  - `225` training examples
  - `45` validation examples
  - exactly `30.0%` in both splits

- instructor focus examples:
  - `300` training examples
  - `60` validation examples
  - exactly `40.0%` in both splits

- rubric configurations:
  - `3` criteria present
  - `4` criteria present
  - `5` criteria present

- confidence range:
  - roughly `0.55` to `0.97`

The dataset card also notes that explicit error flags are not mutually
exclusive. A sample may simultaneously express multiple issues, such as:

- OCR plus logic
- OCR plus compile failure
- runtime plus logic

## 7. Uniqueness And Deduplication Stats

The attached dataset card reports the following unique-code counts:

| File family | Examples | Unique code bodies |
|---|---:|---:|
| base train | 750 | 271 |
| dedup train | 750 | 750 |
| base val | 150 | 104 |
| dedup val | 150 | 150 |

Interpretation:

- the base files intentionally reuse code bodies across multiple grading
  contexts
- the `nodup` files remove that reuse and are more appropriate when leakage is
  a concern

## 8. Score And Confidence Statistics

The dataset card reports the following file-level score and confidence summary:

| File | Score min/max | Mean normalized score | Mean confidence |
|---|---|---:|---:|
| `train_set.jsonl` | 0-100 | 68.9% | 0.783 |
| `train_set_nodup.jsonl` | 0-100 | 69.1% | 0.785 |
| `val_set.jsonl` | 1-100 | 69.4% | 0.782 |
| `val_set_nodup.jsonl` | 0-100 | 69.4% | 0.783 |

Important note from the dataset card:

- raw score is not directly comparable across all examples because examples use
  different `max_score` values
- normalized score is the correct cross-example metric

The dataset card also reports a deliberately balanced normalized score
distribution across these buckets:

- `0-40%`
- `41-60%`
- `61-75%`
- `76-90%`
- `91-100%`

That means the dataset is not heavily skewed toward only easy or only failed
submissions.

## 9. File Format

All four files use OpenAI fine-tuning JSONL format.

Each line is one JSON object with a `messages` array containing exactly `3`
turns:

- `system`
  - instructs the model to act as an expert Java grader and return only valid
    JSON

- `user`
  - contains the grading request serialized as a JSON string

- `assistant`
  - contains the grading response serialized as a JSON string

Example structure:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are an expert Java grader. Return ONLY valid JSON matching the required schema. Do not add markdown."
    },
    {
      "role": "user",
      "content": "{...}"
    },
    {
      "role": "assistant",
      "content": "{...}"
    }
  ]
}
```

## 10. Request Schema

The dataset-style request payload is centered around:

- `submission_id`
- `code`
- `evaluation`
- `rubric`
- sometimes `instructor_notes`

### `evaluation`

The `evaluation` object carries the evidence the model is expected to reason
over.

It typically contains:

- `test_results`
  - textual summary of compile/runtime/test evidence

- `test_stats`
  - counts for total, passed, and failed tests

- `edge_case_results`
  - compact edge-case evidence for cases such as:
    - `null_input`
    - `negative_numbers`
    - `zero_boundary`
    - `empty_input`

- `performance`
  - heuristic runtime and complexity metadata

### `rubric`

The rubric payload typically contains:

- `total_points`
- `criteria`
- optional `instructor_focus`

Rubric criteria vary across:

- `3` criterion configurations
- `4` criterion configurations
- `5` criterion configurations

## 11. Response Schema

The dataset-style assistant response typically contains:

- `submission_id`
- `total_score`
- `max_score`
- `rubric_breakdown`
- `feedback`
- `error_classification`
- `confidence`

### `rubric_breakdown`

Each item typically contains:

- `id`
- `max_points`
- `points_awarded`
- `comments`

### `feedback`

In the dataset, `feedback` is a single string rather than a nested object.

### `error_classification`

This object typically contains:

- `handwriting_ocr_suspected`
- `syntax_or_compile`
- `runtime`
- `logic`
- `issues`

## 12. Validation Status

The attached dataset card states that all four files passed programmatic checks
at the time of the v4 report.

Reported checks include:

- valid JSON on every line
- exactly `3` messages per example
- `total_score = sum(points_awarded)`
- confidence values in the expected range
- uniqueness guarantees for the `nodup` variants
- no pathological contradiction where low scores appear with no meaningful
  issue signal

The card also reports:

- `750/750` valid lines in each training file
- `150/150` valid lines in each validation file

## 13. Known Limitations

The dataset card explicitly calls out two important limitations.

### Missing No-Log Scenario

The report says there are `0` examples where sandbox execution evidence is
completely absent and grading is purely static-review based.

Impact:

- the model has weak training signal for confidence reduction when execution
  logs are unavailable

### Out-Of-Distribution Topics Not Evaluated

The dataset covers its chosen `26` topics thoroughly, but does not evaluate
generalization on truly unseen topic families such as entirely new method
categories.

Impact:

- the dataset is strong for in-scope grading behavior
- it is not a complete OOD benchmark

## 14. Why This Dataset Matters

This dataset does more than store examples. It defines a grading behavior.

It teaches the model to:

- interpret rubric structure
- grade against evidence
- separate OCR noise from genuine code bugs
- express criterion-by-criterion judgments
- produce student-facing feedback
- calibrate confidence rather than always sounding certain

That makes the dataset valuable for:

- supervised fine-tuning
- controlled validation
- prompt and schema design
- runtime grading standardization

## 15. Runtime Integration Notes

The runtime `ai_grader` worker now uses this dataset format as the
model-facing contract.

Current runtime strategy:

1. Build dataset-style `evaluation` content from live sandbox output.
2. Send a dataset-style JSON request to the model.
3. Accept dataset-style JSON output from the model.
4. Normalize that output back into the existing runtime grading schema.
5. Publish the normalized result for the rest of the backend.

Key normalization mappings:

- dataset `rubric_breakdown[].id`
  -> runtime `criterion_id_or_name`

- dataset `rubric_breakdown[].points_awarded`
  -> runtime `earned_points`

- dataset `rubric_breakdown[].comments`
  -> runtime `rationale`

- dataset `rubric_breakdown[].comments`
  -> runtime `evidence_from_code_or_logs`

- dataset `feedback`
  -> runtime structured `feedback.summary`, `feedback.suggestions`,
     `feedback.next_steps`

- dataset `error_classification.issues`
  -> runtime `error_classification.notes`

This keeps the rest of the backend stable while still making the model-facing
contract match the fine-tuning data.

## 16. Recommended Use

Recommended usage by file:

- `train_set.jsonl`
  - standard fine-tuning

- `train_set_nodup.jsonl`
  - ablations or training runs where code uniqueness matters

- `val_set.jsonl`
  - standard validation and early stopping

- `val_set_nodup.jsonl`
  - leakage-reduced validation