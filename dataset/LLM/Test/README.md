# LLM Grader Evaluation

Benchmarks 17 LLM providers on their ability to accurately grade OCR'd handwritten Java student code using [promptfoo](https://promptfoo.dev/).

## Overview

The system prompt instructs each LLM to act as a Java programming instructor. Given a question and an OCR'd student submission, the LLM must:

1. Identify and mentally correct OCR artifacts (e.g., `pub1ic` -> `public`, `O` -> `0`)
2. Evaluate the corrected code for genuine logic bugs
3. Return a structured JSON grade (correctness, logic, style, edge cases, efficiency) out of 100

## Providers Under Test

| Provider   | Models                                         |
| ---------- | ---------------------------------------------- |
| Anthropic  | Claude Sonnet 4.5, Claude Opus 4.5             |
| OpenAI     | GPT-5.2, GPT-5.1                               |
| Google     | Gemini 3 Pro, Gemini 3 Flash, Gemini 2.5 Pro   |
| Groq       | Llama 3.3 70B, Llama 4 Scout 17B               |
| Mistral    | Mistral Large, Codestral                        |
| xAI        | Grok 4.1 Fast, Grok 4                          |
| DeepSeek   | DeepSeek Chat, DeepSeek Reasoner                |
| Alibaba    | Qwen3 Max, Qwen3 Coder Plus                    |

## Test Cases

12 test cases (TC001--TC012) cover a range of scenarios:

| ID    | Method           | Category                     | Expected Score |
| ----- | ---------------- | ---------------------------- | -------------- |
| TC001 | `isEven`         | Correct + OCR noise          | 90--100        |
| TC002 | `sumArray`       | Correct + OCR noise          | 95--100        |
| TC003 | `getLetterGrade` | Boundary bug (`>` vs `>=`)   | 65--80         |
| TC004 | `isPalindrome`   | Missing null check           | 80--95         |
| TC005 | `findMax`        | Init bug (`max = 0`)         | 50--70         |
| TC006 | `Rectangle`      | Formula error (`+` vs `*`)   | 55--75         |
| TC007 | `safeDivide`     | Correct + heavy OCR noise    | 95--100        |
| TC008 | `insertAtEnd`    | Correct linked list logic    | 95--100        |
| TC009 | `binarySearch`   | Off-by-one (`<` vs `<=`)     | 65--80         |
| TC010 | `fibonacci`      | Two critical bugs            | 25--45         |
| TC011 | `countVowels`    | Perfect code, no OCR noise   | 90--100        |
| TC012 | `reverseArray`   | Wrong swap index             | 30--55         |

## Evaluation Metrics

Each test case is judged by two LLM evaluators (GPT-4o and Claude Haiku 4.5) across three dimensions:

- **score_accuracy** -- Did the grader assign a score within the expected range?
- **ocr_recognition** -- Did the grader correctly distinguish OCR artifacts from real bugs?
- **bug_detection** -- Did the grader identify all genuine logic errors without false positives?

An additional `valid_json_output` metric verifies that every response is valid JSON.

## Setup

### 1. Install dependencies

```bash
npm install
```

```bash
npm install -g promptfoo
```

### 2. Set API keys

Set the API keys for the providers you want to evaluate:

```bash
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
GROQ_API_KEY=...
MISTRAL_API_KEY=...
XAI_API_KEY=...
DEEPSEEK_API_KEY=...
ALIBABA_API_KEY=...
```
Set it in .env in ./dataset/LLM/Test

### 3. Run the evaluation

If in directory ./dataset/LLM/Test :
```bash
promptfoo eval
```
or if in Root directory :

```bash
promptfoo eval -c dataset/LLM/Test/promptfooconfig.yaml --env-file dataset/LLM/Test/.env
```

Results are saved to `./results/grader_evaluation_final.json`.

### 4. View results

```bash
promptfoo view
```

## Directory Structure

```
Test/
├── promptfooconfig.yaml        # Provider, test case, and assertion definitions
├── system_prompt/
│   └── sys_prompt.json         # System + user prompt template
├── results/                    # Evaluation output (generated)
├── package.json                # promptfoo dependency
└── README.md
```
