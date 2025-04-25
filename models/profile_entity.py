from typing import Optional
from pydantic import BaseModel, Field


class ProfileEntity(BaseModel):
    id_profile: Optional[str] = Field(None, description="ID của profile Pinterest")
    username: Optional[str] = Field(
        None, description="Username của tài khoản Pinterest"
    )
    avatar_url: Optional[str] = Field(None, description="URL của ảnh đại diện")
    bio: Optional[str] = Field(None, description="Tiểu sử của người dùng")
    full_name: Optional[str] = Field(None, description="Tên đầy đủ của người dùng")
    following: Optional[int] = Field(None, description="Số người đang theo dõi")
    follower: Optional[int] = Field(None, description="Số người theo dõi")
    link: Optional[str] = Field(None, description="Link đến profile Pinterest")

    def to_dict(self):
        return self.model_dump(exclude_unset=True)
