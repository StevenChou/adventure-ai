from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel

# 在 FastAPI 應用程式中，這些模型用於：
# 請求驗證：確保傳入的資料符合預期的格式和類型
# 回應格式化：定義 API 回應的結構
# 資料轉換：在資料庫模型和 API 之間轉換資料


class StoryOptionsSchema(BaseModel):
    text: str
    node_id: Optional[int] = None


class StoryNodeBase(BaseModel):
    content: str
    is_ending: bool = False
    is_winning_ending: bool = False


class CompleteStoryNodeResponse(StoryNodeBase):
    id: int
    options: List[StoryOptionsSchema] = []

    class Config:
        from_attributes = True


class StoryBase(BaseModel):
    title: str
    session_id: Optional[str] = None

    class Config:
        from_attributes = True


class CreateStoryRequest(BaseModel):
    theme: str


# 還有繼承ㄝ
class CompleteStoryResponse(StoryBase):
    id: int
    created_at: datetime
    root_node: CompleteStoryNodeResponse
    all_nodes: Dict[int, CompleteStoryNodeResponse]

    class Config:
        from_attributes = True
