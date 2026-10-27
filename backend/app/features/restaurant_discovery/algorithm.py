import unicodedata

from app.features.restaurant_discovery.schemas import (
    RestaurantItem,
    SearchCriteria,
    SortBy,
)


def normalize_text(value: str) -> str:
    lowered = value.strip().lower().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def _matches_dish(restaurant: RestaurantItem, query: str) -> bool:
    normalized_query = normalize_text(query)
    if not normalized_query:
        return True

    return any(normalized_query in normalize_text(dish) for dish in restaurant.dishes)


def _recommended_score(restaurant: RestaurantItem) -> float:
    verified_bonus = 0.6 if restaurant.menu_verified else 0
    return restaurant.rating * 2 + verified_bonus - restaurant.distance_km * 0.35


def filter_and_sort_restaurants(
    restaurants: list[RestaurantItem],
    criteria: SearchCriteria,
) -> list[RestaurantItem]:
    filtered = [
        restaurant
        for restaurant in restaurants
        if _matches_dish(restaurant, criteria.query)
        and (criteria.area == "all" or restaurant.area == criteria.area)
        and restaurant.distance_km <= criteria.radius_km
        and (
            restaurant.price_per_person is None
            or restaurant.price_per_person <= criteria.budget_per_person
        )
    ]

    if criteria.sort_by == SortBy.DISTANCE:
        return sorted(filtered, key=lambda restaurant: restaurant.distance_km)

    if criteria.sort_by == SortBy.RATING:
        return sorted(
            filtered,
            key=lambda restaurant: (-restaurant.rating, restaurant.distance_km),
        )

    return sorted(filtered, key=_recommended_score, reverse=True)
