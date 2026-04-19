# pipewatch

A lightweight CLI to monitor and alert on data pipeline health metrics across multiple sources.

---

## Installation

```bash
pip install pipewatch
```

Or install from source:

```bash
git clone https://github.com/youruser/pipewatch.git && cd pipewatch && pip install -e .
```

---

## Usage

Define your pipeline sources in a config file (`pipewatch.yaml`), then run:

```bash
pipewatch monitor --config pipewatch.yaml
```

**Example config:**

```yaml
sources:
  - name: orders_pipeline
    type: postgres
    query: "SELECT COUNT(*) FROM orders WHERE created_at > NOW() - INTERVAL '1 hour'"
    threshold:
      min: 100
    alert: slack
```

**Run a one-time health check:**

```bash
pipewatch check --source orders_pipeline
```

**Watch continuously with a custom interval:**

```bash
pipewatch monitor --interval 60
```

Output:

```
[OK]   orders_pipeline   → 342 rows   (threshold: min 100)
[FAIL] payments_pipeline → 0 rows     (threshold: min 50) ⚠ Alert sent
```

---

## License

MIT © 2024 youruser