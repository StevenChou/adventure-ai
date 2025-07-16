import uuid
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Cookie, Response, BackgroundTasks
from sqlalchemy.orm import Session

from db.database import get_db, SessionLocal
from models.story import Story, StoryNode
from models.job import StoryJob
from schemas.story import (
    CompleteStoryResponse,
    CompleteStoryNodeResponse,
    CreateStoryRequest,
)
from schemas.job import StoryJobResponse
from core.story_generator import StoryGenerator

# tages 定義：所有帶有 "stories" 標籤的端點會在文檔界面中被歸類到同一個分組下
router = APIRouter(prefix="/stories", tags=["stories"])


def get_session_id(session_id: Optional[str] = Cookie(None)):
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id


@router.post("/create", response_model=StoryJobResponse)
def create_story(
    request: CreateStoryRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    response.set_cookie(key="session_id", value=session_id, httponly=True)

    job_id = str(uuid.uuid4())

    job = StoryJob(
        job_id=job_id, session_id=session_id, theme=request.theme, status="pending"
    )
    db.add(job)
    db.commit()

    # 🌼 提高用戶體驗：由於故事生成可能需要一些時間（特別是如果涉及 AI 生成內容），
    # 這種方式允許立即返回一個 job ID 給用戶，而不需要等待整個故事生成完成。
    background_tasks.add_task(
        generate_story_task, job_id=job_id, theme=request.theme, session_id=session_id
    )

    return job


# 1. 背景任務的特殊性：generate_story_task 是一個背景任務，它在 HTTP 請求完成後獨立執行，
# 此時 FastAPI 的請求上下文已經結束。
# 2. 依賴注入的限制：Depends(get_db) 只能在 FastAPI 的路由函數（如 @router.post、@router.get 等裝飾的函數）中使用，
# 因為它依賴於 FastAPI 的請求生命週期。
def generate_story_task(job_id: str, theme: str, session_id: str):
    # 要建立新的 session
    db = SessionLocal()

    try:
        job = db.query(StoryJob).filter(StoryJob.job_id == job_id).first()

        if not job:
            return

        # 🤩 分段 commit 好酷~
        try:
            job.status = "processing"
            db.commit()

            story = StoryGenerator.generate_story(db, session_id, theme)

            job.story_id = story.id  # todo: update story id
            job.status = "completed"
            job.completed_at = datetime.now()
            db.commit()
        except Exception as e:
            job.status = "failed"
            job.completed_at = datetime.now()
            job.error = str(e)
            db.commit()
    finally:
        db.close()


@router.get("/{story_id}/complete", response_model=CompleteStoryResponse)
def get_complete_story(story_id: int, db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    complete_story = build_complete_story_tree(db, story)
    return complete_story


def build_complete_story_tree(db: Session, story: Story) -> CompleteStoryResponse:
    nodes = db.query(StoryNode).filter(StoryNode.story_id == story.id).all()

    node_dict = {}
    for node in nodes:
        node_response = CompleteStoryNodeResponse(
            id=node.id,
            content=node.content,
            is_ending=node.is_ending,
            is_winning_ending=node.is_winning_ending,
            options=node.options,
        )
        node_dict[node.id] = node_response

    # 1. (node for node in nodes if node.is_root) 是一個生成器表達式，
    # 它會遍歷  nodes 列表中的所有節點，並只保留  is_root 屬性為  True 的節點。
    # 2. next() 函數會從這個生成器中獲取第一個符合條件的節點（即第一個  is_root 為  True 的節點）。
    # 3. 如果沒有找到符合條件的節點（即沒有  is_root 為  True 的節點），則 next() 函數會返回第二個參數  None。
    root_node = next((node for node in nodes if node.is_root), None)
    if not root_node:
        raise HTTPException(status_code=500, detail="Story root node not found")

    return CompleteStoryResponse(
        id=story.id,
        title=story.title,
        session_id=story.session_id,
        created_at=story.created_at,
        root_node=node_dict[root_node.id],
        all_nodes=node_dict,
    )
