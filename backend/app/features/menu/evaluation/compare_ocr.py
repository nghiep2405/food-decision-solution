def key(name):
return " ".join(unicodedata.normalize("NFC", str(name)).casefold().split())


def price_key(item):
    """Convert menu prices into comparable (min, max, currency) tuples."""

    def normalize_price(data, default_currency="VND"):
        currency = data.get("currency") or default_currency
        price = data.get("price")

        if price is not None:
            return (price, price, currency)

        price_range = data.get("priceRange") or data.get("price_range")
        if isinstance(price_range, dict):
            return (
                price_range.get("min"),
                price_range.get("max"),
                currency,
            )

        return (
            data.get("priceMin"),
            data.get("priceMax"),
            currency,
        )

variants = item.get("variants") or []

if variants:
        values = []
        for variant in variants:
            values.append((
                variant.get("price"),
                variant.get("priceMin"),
                variant.get("priceMax"),
                variant.get("currency", "VND")
            ))
        return sorted(values, key=str)

    price = item.get("price")
    price_min = item.get("priceMin", price)
    price_max = item.get("priceMax", price)

    return [(
        None,
        price_min,
        price_max,
        item.get("currency", "VND")
    )]
        return sorted(
            [normalize_price(variant, item.get("currency", "VND"))
             for variant in variants],
            key=str,
        )

    return [normalize_price(item)]

def evaluate(gt, runs):
truth = {s.get("image_file", s.get("image")): s for s in gt["samples"]}
output = {}
@@ -53,7 +65,13 @@ def evaluate(gt, runs):
continue
valid += 1
gt_items = {key(x["dishName"]): x for x in sample["items"]}
            pred_items = {key(x.get("dishName", x.get("name", ""))): x for x in items if x.get("dishName") or x.get("name")}
            
            pred_items = {
                key(x.get("dishName") or x.get("name") or x.get("normalizedName") or ""): x
                for x in items
                if x.get("dishName") or x.get("name") or x.get("normalizedName")
            }

shared = gt_items.keys() & pred_items.keys()
tp += len(shared); predicted += len(pred_items); actual += len(gt_items)
for dish in shared:
