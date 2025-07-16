from typing import Optional
from datetime import datetime
from pydantic import BaseModel


# 在 FastAPI 應用程式中，這些模型用於：
# 請求驗證：確保傳入的資料符合預期的格式和類型
# 回應格式化：定義 API 回應的結構
# 資料轉換：在資料庫模型和 API 之間轉換資料


class StoryJobBase(BaseModel):
    theme: str


class StoryJobResponse(BaseModel):
    job_id: str
    status: str
    created_at: datetime
    story_id: Optional[int] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True


class StoryJobCreate(StoryJobBase):
    pass
