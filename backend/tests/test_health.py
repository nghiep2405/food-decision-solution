from app.main import create_app


def test_health_route_and_openapi_are_registered() -> None:
    app = create_app()
    openapi = app.openapi()

    assert "/api/v1/health" in openapi["paths"]
    assert "/api/v1/restaurants/search" in openapi["paths"]
    assert "/api/v1/admin/restaurants" in openapi["paths"]
    assert "/api/v1/admin/ocr/config" in openapi["paths"]
    assert "/api/v1/menus/ocr" in openapi["paths"]
