"""Chat endpoints for real-time streaming conversations."""

import json
import uuid
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from src.services.conversation_chain_service import ConversationChainService

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """Chat message request model."""

    message: str = Field(..., description="User's message to the AI")
    conversation_id: Optional[str] = Field(
        None, description="Conversation ID (UUID). If not provided, a new one is created."
    )


class ChatResponse(BaseModel):
    """Chat response model."""

    conversation_id: str = Field(..., description="Conversation UUID")
    response: str = Field(..., description="AI's complete response")


@router.websocket("/ws/{conversation_id}")
async def chat_websocket(websocket: WebSocket, conversation_id: str) -> None:
    """Websocket endpoint for streaming chat responses.

    Args:
        websocket: WebSocket connection
        conversation_id: UUID of the conversation

    Protocol:
        Client sends: {"message": "your message here"}
        Server sends: {"type": "token", "content": "token"} (multiple times)
        Server sends: {"type": "done"} (when complete)
        Server sends: {"type": "error", "message": "error description"} (on error)
    """
    await websocket.accept()

    try:
        # Validate conversation ID
        try:
            conv_uuid = uuid.UUID(conversation_id)
        except ValueError:
            await websocket.send_json(
                {"type": "error", "message": "Invalid conversation ID format"}
            )
            await websocket.close()
            return

        # Create conversation service
        service = ConversationChainService()

        # Listen for messages
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
                user_message = message_data.get("message")

                if not user_message:
                    await websocket.send_json(
                        {"type": "error", "message": "Message field is required"}
                    )
                    continue

                # Send streaming response
                await websocket.send_json({"type": "start"})

                async for token in service.stream_response(conv_uuid, user_message):
                    await websocket.send_json({"type": "token", "content": token})

                await websocket.send_json({"type": "done"})

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
            except Exception as e:
                await websocket.send_json(
                    {"type": "error", "message": f"Error processing message: {str(e)}"}
                )

    except WebSocketDisconnect:
        # Client disconnected
        pass
    except Exception as e:
        # Unexpected error
        try:
            await websocket.send_json({"type": "error", "message": f"Server error: {str(e)}"})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/history/{conversation_id}")
async def get_chat_history(conversation_id: str) -> dict:
    """Get conversation history.

    Args:
        conversation_id: UUID of the conversation

    Returns:
        List of messages with role and content
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        return {"error": "Invalid conversation ID format"}

    service = ConversationChainService()
    history = service.get_conversation_history(conv_uuid)

    return {"conversation_id": conversation_id, "messages": history}
