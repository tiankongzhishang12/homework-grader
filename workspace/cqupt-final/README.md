# CQUPT Final Exam Workspace

This workspace is reserved for the CQUPT final-exam scoring flow only.
Do not mix it with the legacy login-payment homework sample under `workspace/`.

## Layout

```text
workspace/cqupt-final/
|- raw/         # Student PDFs only
|- reference/   # Standard-answer materials, e.g. anwser.pdf
|- ir/          # Preprocessed IR JSON files
|- scores/      # Scoring JSON outputs
|- reports/     # Excel and statistics outputs
|- logs/        # Runtime logs created by scoring scripts
`- README.md
```

## Manual file placement

You said file migration stays manual. Use this layout:

- Put `text1.pdf`, `text2.pdf`, `text3.pdf` into `workspace/cqupt-final/raw/`
- If you want the standard answer inside the workspace, put `anwser.pdf` into `workspace/cqupt-final/reference/`
- Do not place `anwser.pdf` into `raw/`

## Dedicated rubric and config

- Rubric starter: `examples/cqupt-final-exam-rubric.yaml`
- Dedicated config: `grader-config.cqupt-final.yaml`

Before real scoring, update the rubric using the actual exam questions and the
standard answer in `reference/anwser.pdf`.

## Recommended commands

From the project root, with your local virtual environment:

```powershell
& ".\.venv\Scripts\python.exe" ".\scripts\preprocess.py" `
  ".\workspace\cqupt-final\raw" `
  --output ".\workspace\cqupt-final\ir" `
  --rubric ".\examples\cqupt-final-exam-rubric.yaml"
```

```powershell
& ".\.venv\Scripts\python.exe" ".\scripts\batch_score.py" `
  --config ".\grader-config.cqupt-final.yaml"
```

If you prefer explicit CLI arguments instead of the dedicated config file:

```powershell
& ".\.venv\Scripts\python.exe" ".\scripts\batch_score.py" `
  ".\workspace\cqupt-final" `
  --rubric ".\examples\cqupt-final-exam-rubric.yaml"
```

## Review checklist

- Confirm `raw/` contains only student papers
- Confirm `reference/` holds the standard answer only
- Inspect generated IR before scoring to catch OCR, pagination, formula, or table loss
- Compare each scored paper against the standard answer key points, not against the legacy homework rubric
