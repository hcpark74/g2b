from pydantic import BaseModel


class TimelineStageVM(BaseModel):
    stage: str
    status: str
    status_variant: str
    number: str
    date: str
    meta: str
