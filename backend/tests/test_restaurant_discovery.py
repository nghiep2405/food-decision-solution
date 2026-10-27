import pytest
from pydantic import ValidationError

from app.features.restaurant_discovery.schemas import SearchCriteria
from app.features.restaurant_discovery.service import RestaurantDiscoveryService

service = RestaurantDiscoveryService()


def test_search_known_dish_returns_matching_restaurants() -> None:
    result = service.search(
        SearchCriteria(
            query="bún bò",
            radius_km=5,
            budget_per_person=120_000,
        )
    )

    assert result.total == 2
    assert [item.id for item in result.items] == [
        "quan-goc-hue",
        "bun-bo-ba-nam",
    ]


def test_area_and_budget_filters_are_applied() -> None:
    result = service.search(
        SearchCriteria(
            query="cơm",
            area="Quận 3",
            radius_km=5,
            budget_per_person=100_000,
        )
    )

    assert result.total == 1
    assert result.items[0].id == "com-tam-pho"


def test_missing_price_is_kept_with_warning() -> None:
    result = service.search(
        SearchCriteria(
            query="lẩu",
            radius_km=6,
            budget_per_person=50_000,
        )
    )

    assert result.total == 1
    assert result.items[0].price_per_person is None
    assert any("chưa có giá" in warning for warning in result.warnings)


def test_invalid_radius_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SearchCriteria(radius_km=50)
