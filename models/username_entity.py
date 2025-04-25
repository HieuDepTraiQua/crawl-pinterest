from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class UsernameEntity(BaseModel):
    username: Optional[str] = Field(None, description="Username của profile Pinterest")
    isCrawl: Optional[bool] = Field(False, description="Trạng thái crawl profile")

    def to_dict(self):
        return self.model_dump(exclude_unset=True)
