from sqlmodel import Session, select

from app.models import Bid, ContractProcessIntegration
from app.repositories.page_repository import PageRepository


class SqlModelPageRepository(PageRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_prespecs(self) -> list[dict[str, str]]:
        return []

    def list_results(self) -> list[dict[str, str]]:
        bids = {bid.bid_id: bid for bid in self.session.exec(select(Bid)).all()}
        integrations = list(self.session.exec(select(ContractProcessIntegration)).all())

        items: list[dict[str, str]] = []
        for integration in integrations:
            bid = bids.get(integration.bid_id)
            if bid is None:
                continue
            award_amount = integration.award_amount or "-"
            contract_amount = integration.award_amount or "-"
            items.append(
                {
                    "bid_no": bid.bid_id,
                    "title": bid.title,
                    "business_type": bid.category or "미분류",
                    "winner": integration.award_company or "-",
                    "award_amount": award_amount,
                    "award_rate": "-",
                    "contract_amount": contract_amount,
                    "contract_date": integration.contract_date or "-",
                    "notice_org": bid.notice_org or "-",
                    "demand_org": bid.demand_org or "-",
                }
            )

        return items
