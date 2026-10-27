from app.features.restaurant_discovery.algorithm import filter_and_sort_restaurants
from app.features.restaurant_discovery.provider import MockRestaurantProvider
from app.features.restaurant_discovery.schemas import (
    RestaurantSearchResponse,
    SearchCriteria,
)


class RestaurantDiscoveryService:
    def __init__(self, provider: MockRestaurantProvider | None = None):
        self._provider = provider or MockRestaurantProvider()

    def search(self, criteria: SearchCriteria) -> RestaurantSearchResponse:
        restaurants = self._provider.list_restaurants()
        items = filter_and_sort_restaurants(restaurants, criteria)
        warnings: list[str] = []

        if not items:
            warnings.append("Không tìm thấy quán phù hợp với các điều kiện hiện tại.")
        if any(item.price_per_person is None for item in items):
            warnings.append(
                "Một số quán chưa có giá đáng tin cậy nên chưa thể xác nhận phù hợp ngân sách."
            )
        if any(not item.menu_verified for item in items):
            warnings.append("Một số menu chưa được xác minh hoặc có thể đã cũ.")

        return RestaurantSearchResponse(
            items=items,
            total=len(items),
            criteria=criteria,
            warnings=warnings,
        )
