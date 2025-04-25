from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class KeywordEntity(BaseModel):
    keyword: Optional[str] = Field(None, description="Từ khóa tìm kiếm")
    isCrawl: Optional[bool] = Field(False, description="Trạng thái đã crawl hay chưa")
    crawlDate: Optional[datetime] = Field(None, description="Ngày crawl")

    def to_dict(self):
        return self.model_dump(exclude_unset=True)
