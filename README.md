# 🏹 BoundSmith

**Boundary condition blind spot hunter** — automatically extracts every untested critical value from your Python branch logic and generates precise test cases.

## The Problem

Your code says `if retry_count > 3` but your tests only use `0` and `10`. Nobody ever tested `3` and `4` — the exact values where bugs hide. BoundSmith finds every such gap.

## Install

```bash
pip install -r requirements.txt
```

## Usage

### Scan source code for boundaries

```bash
python cli.py scan src/
```

### Cross-check against existing tests

```bash
python cli.py scan src/ --tests tests/
```

### Auto-generate missing boundary tests

```bash
python cli.py scan src/ --tests tests/ --generate test_boundaries.py
```

### JSON output for CI pipelines

```bash
python cli.py scan src/ --tests tests/ --json
```

### SARIF output for GitHub Code Scanning

```bash
python cli.py scan src/ --format sarif -o report.sarif
```

Upload to GitHub Code Scanning:

```bash
gzip report.sarif
gh api \
  -X POST \
  -H "Accept: application/vnd.github+json" \
  "/repos/{owner}/{repo}/code-scanning/sarifs" \
  -f "commit_sha=$(git rev-parse HEAD)" \
  -f "ref=$(git symbolic-ref HEAD)" \
  -f "sarif=@report.sarif.gz" \
  -f "tool_name=BoundSmith"
```


## What It Finds

| Source Code | Boundary Triplet | What To Test |
|---|---|---|
| `if x > 3` | `(2, 3, 4)` | Just below, at, just above |
| `if len(s) == 0` | `(-1, 0, 1)` | Empty and single-element |
| `if 0 < x < 100` | `(0), (100)` | Both ends of the range |
| `if temp <= -10` | `(-11, -10, -9)` | Negative boundary |

## Example Output

```
🏹 BoundSmith: found 12 boundaries, 5 uncovered

  ⚠  src/retry.py:42  retry_count > 3
     → test with: (2, 3, 4)

  ⚠  src/validate.py:17  len(items) == 0
     → test with: (-1, 0, 1)
```

## License

MIT
