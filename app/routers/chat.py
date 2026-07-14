from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from bson.errors import InvalidId

from app.database import conversations_collection, messages_collection
from app.schemas import ChatRequest, ChatResponse, MessageOut, ConversationOut
from app.auth import get_current_user
from app.services.ai_service import generate_reply

router = APIRouter(prefix="/chat", tags=["Chat"])

MAX_HISTORY_MESSAGES = 20  # how many prior turns to feed back to the model


async def _load_history(conversation_id: ObjectId) -> List[dict]:
    cursor = (
        messages_collection.find({"conversation_id": conversation_id})
        .sort("created_at", 1)
        .limit(MAX_HISTORY_MESSAGES)
    )
    return [doc async for doc in cursor]


@router.post("", response_model=ChatResponse)
async def send_message(payload: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["_id"]
    now = datetime.now(timezone.utc)

    # Resolve or create the conversation
    if payload.conversation_id:
        try:
            conversation_id = ObjectId(payload.conversation_id)
        except InvalidId:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation_id")

        conversation = await conversations_collection.find_one(
            {"_id": conversation_id, "user_id": user_id}
        )
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    else:
        new_conversation = {
            "user_id": user_id,
            "title": payload.message[:50],
            "created_at": now,
            "updated_at": now,
        }
        result = await conversations_collection.insert_one(new_conversation)
        conversation_id = result.inserted_id

    # Load prior context, then call the AI provider
    history_docs = await _load_history(conversation_id)
    history_for_model = [{"role": m["role"], "content": m["content"]} for m in history_docs]
    reply_text = await generate_reply(history_for_model, payload.message)

    # Persist both the user message and the assistant reply
    user_msg = {
        "conversation_id": conversation_id,
        "role": "user",
        "content": payload.message,
        "created_at": now,
    }
    assistant_msg = {
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": reply_text,
        "created_at": datetime.now(timezone.utc),
    }
    await messages_collection.insert_many([user_msg, assistant_msg])
    await conversations_collection.update_one(
        {"_id": conversation_id}, {"$set": {"updated_at": datetime.now(timezone.utc)}}
    )

    full_history = history_docs + [user_msg, assistant_msg]
    return ChatResponse(
        conversation_id=str(conversation_id),
        reply=reply_text,
        history=[MessageOut(**m) for m in full_history],
    )


@router.get("/conversations", response_model=List[ConversationOut])
async def list_conversations(current_user: dict = Depends(get_current_user)):
    cursor = conversations_collection.find({"user_id": current_user["_id"]}).sort("updated_at", -1)
    conversations = []
    async for c in cursor:
        conversations.append(
            ConversationOut(
                id=str(c["_id"]),
                title=c["title"],
                created_at=c["created_at"],
                updated_at=c["updated_at"],
            )
        )
    return conversations


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageOut])
async def get_conversation_messages(conversation_id: str, current_user: dict = Depends(get_current_user)):
    try:
        conv_obj_id = ObjectId(conversation_id)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation_id")

    conversation = await conversations_collection.find_one(
        {"_id": conv_obj_id, "user_id": current_user["_id"]}
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    docs = await _load_history(conv_obj_id)
    return [MessageOut(**m) for m in docs]


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    try:
        conv_obj_id = ObjectId(conversation_id)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation_id")

    result = await conversations_collection.delete_one(
        {"_id": conv_obj_id, "user_id": current_user["_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    await messages_collection.delete_many({"conversation_id": conv_obj_id})
