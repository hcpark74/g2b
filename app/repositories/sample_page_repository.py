from app.repositories.page_repository import PageRepository
from app.sample_data import get_sample_prespecs, get_sample_results


class SamplePageRepository(PageRepository):
    def list_prespecs(
        self,
        *,
        q: str | None = None,
        stage: str | None = None,
        business_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, str]]:
        items = get_sample_prespecs()
        if q:
            query = q.strip().lower()
            items = [
                item
                for item in items
                if query in item["title"].lower()
                or query in item["org"].lower()
                or query in item["demand_org"].lower()
            ]
        if stage:
            items = [item for item in items if item["stage"] == stage]
        if business_type:
            items = [item for item in items if item["business_type"] == business_type]
        if date_from:
            items = [item for item in items if item["date"] >= date_from]
        if date_to:
            items = [item for item in items if item["date"] <= date_to]
        return items

    def list_results(self) -> list[dict[str, str]]:
        return get_sample_results()
