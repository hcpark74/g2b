import httpx

from app.clients.g2b_bid_public_info_client import G2BBidPublicInfoClient


def test_fetch_bid_list_builds_request_and_normalizes_items(monkeypatch) -> None:
    captured_params: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_params.update(dict(request.url.params))
        payload = {
            "response": {
                "body": {
                    "items": {
                        "item": {
                            "bidNtceNo": "R26BK00000099",
                            "bidNtceOrd": "1",
                            "bidNtceNm": "테스트 공고",
                        }
                    }
                }
            }
        }
        return httpx.Response(200, json=payload)

    monkeypatch.setattr(
        "app.clients.g2b_bid_public_info_client.settings.g2b_api_service_key_decoded",
        "test-service-key",
    )
    http_client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://example.com")
    client = G2BBidPublicInfoClient(http_client=http_client)

    items = client.fetch_bid_list(
        "getBidPblancListInfoServc",
        inqry_div=1,
        inqry_bgn_dt="202603120000",
        inqry_end_dt="202603122359",
        num_of_rows=50,
    )

    assert items == [
        {
            "bidNtceNo": "R26BK00000099",
            "bidNtceOrd": "1",
            "bidNtceNm": "테스트 공고",
        }
    ]
    assert captured_params["serviceKey"] == "test-service-key"
    assert captured_params["inqryDiv"] == "1"
    assert captured_params["inqryBgnDt"] == "202603120000"
    assert captured_params["inqryEndDt"] == "202603122359"
    assert captured_params["numOfRows"] == "50"


def test_fetch_bid_list_requires_bid_number_for_inquiry_div_2(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.clients.g2b_bid_public_info_client.settings.g2b_api_service_key_decoded",
        "test-service-key",
    )
    client = G2BBidPublicInfoClient(http_client=httpx.Client(base_url="https://example.com"))

    try:
        client.fetch_bid_list("getBidPblancListInfoServc", inqry_div=2)
    except ValueError as exc:
        assert "bid_ntce_no is required" in str(exc)
    else:
        raise AssertionError("ValueError was not raised")
