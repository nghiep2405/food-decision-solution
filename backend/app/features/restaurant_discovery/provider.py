import json
from functools import lru_cache
from pathlib import Path

from app.features.restaurant_discovery.schemas import RestaurantItem


DATA_FILE = Path(__file__).parent / "data" / "restaurants.json"


@lru_cache
def _load_restaurants() -> tuple[RestaurantItem, ...]:
    with DATA_FILE.open(encoding="utf-8") as data_file:
        raw_items = json.load(data_file)

    return tuple(RestaurantItem.model_validate(item) for item in raw_items)


class MockRestaurantProvider:
    def list_restaurants(self) -> list[RestaurantItem]:
        return list(_load_restaurants())
