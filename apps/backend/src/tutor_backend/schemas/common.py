"""Kiểu dùng chung cho schema API."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# Kiểm dạng email đơn giản (không cần thư viện email-validator); email lưu chữ thường
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
Email = Annotated[str, Field(pattern=EMAIL_PATTERN, max_length=254)]
Password = Annotated[str, Field(min_length=8, max_length=200)]
ExerciseCode = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")]
StepId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")]


class ApiModel(BaseModel):
    """Lớp gốc cho schema trả về: đọc được thẳng từ model ORM."""

    model_config = ConfigDict(from_attributes=True)


class PageQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=200)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
