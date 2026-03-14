from app.presentation.viewmodels.pages import SecondaryPageVM


def build_secondary_page_vm(title: str, description: str, active_nav: str, last_synced_at: str) -> SecondaryPageVM:
    return SecondaryPageVM(
        title=title,
        description=description,
        active_nav=active_nav,
        last_synced_at=last_synced_at,
        selected_bid=None,
    )
