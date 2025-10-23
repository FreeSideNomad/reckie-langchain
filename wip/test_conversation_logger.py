#!/usr/bin/env python3
"""Test script for ConversationLogger."""

from uuid import uuid4
from src.services.conversation_logger import ConversationLogger

def test_recording_and_replay():
    """Test basic recording and replay functionality."""
    print("🧪 Testing ConversationLogger\n")

    # Initialize logger
    logger = ConversationLogger(log_dir="conversation-logs-test")

    # Start recording
    conv_id = uuid4()
    user_id = uuid4()
    doc_type = "vision_document"

    log_id = logger.start_recording(
        conversation_id=conv_id,
        user_id=user_id,
        document_type=doc_type
    )
    print(f"✅ Started recording: {log_id}")

    # Log user input
    logger.log_user_input(
        "Create a vision document for a job search app",
        metadata={"step": "initial_input"}
    )
    print("✅ Logged user input 1")

    # Log system response
    logger.log_system_response(
        "Vision document created with sections...",
        metadata={"action": "create-document"}
    )
    print("✅ Logged system response 1")

    # Log user feedback
    logger.log_user_input(
        "Add more detail to the features section",
        metadata={"action": "provide_feedback"}
    )
    print("✅ Logged user input 2")

    # Log system response
    logger.log_system_response(
        "Updated vision document with detailed features...",
        metadata={"action": "update-document"}
    )
    print("✅ Logged system response 2")

    # Stop recording
    log_file = logger.stop_recording()
    print(f"✅ Saved log to: {log_file}\n")

    # List logs
    logs = logger.list_logs()
    print(f"📋 Found {len(logs)} log(s):")
    for log in logs:
        print(f"   - {log['log_id']} ({log['entry_count']} entries)")
    print()

    # Load log
    conversation_log = logger.load_log(log_file)
    print(f"✅ Loaded log: {conversation_log.log_id}")
    print(f"   Document type: {conversation_log.document_type}")
    print(f"   Total entries: {len(conversation_log.entries)}\n")

    # Extract user inputs
    user_inputs = logger.get_user_inputs(conversation_log)
    print(f"👤 Found {len(user_inputs)} user inputs:")
    for idx, (user_input, metadata) in enumerate(user_inputs, 1):
        print(f"   {idx}. {user_input[:60]}...")
        print(f"      Metadata: {metadata}")
    print()

    print("✅ All tests passed!")

if __name__ == "__main__":
    test_recording_and_replay()
