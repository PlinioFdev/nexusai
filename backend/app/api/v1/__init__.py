from fastapi import APIRouter
from app.api.v1.endpoints import auth, documents, chat, widget

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(widget.router)
