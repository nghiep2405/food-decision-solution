# MVP-06 — OCR Comparison

Both methods must run on the **same permitted menu images**. Manually annotate ground truth first. Do not report synthetic examples as real-world accuracy.

| Metric | Visual | Text Pipeline |
|---|---|---|
| Number of images | Not measured | Not measured |
| Dish-name F1 | Not measured | Not measured |
| Price accuracy (matched dishes) | Not measured | Not measured |
| JSON validity | Not measured | Not measured |
| Mean latency (ms) | Not measured | Not measured |

Evaluate with `python -m app.features.menu.evaluation.compare_ocr --ground-truth app/features/menu/evaluation/ground_truth.json --runs app/features/menu/evaluation/runs.json` from `backend`. The evaluation script expects `samples[].image_file/items[]` and `runs[].image_file/method/items/latency_ms`. `items` must be `null` when JSON is invalid. Price accuracy is conditional on matched dish names; report missing dishes separately through F1.

**Default/fallback decision:** Pending actual measurements. Prefer higher F1 and price accuracy with acceptable JSON validity and latency. Record the chosen method, rationale, dataset size, and date once measured.
