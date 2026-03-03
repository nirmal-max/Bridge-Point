"""
Bridge Point — WebSocket Router
Real-time endpoint for notifications and WebRTC call signaling.
"""

import json
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import manager
from app.utils.security import decode_access_token
from app.database import SessionLocal
from app.models.call import CallLog, CallStatus
from app.models.user import User

router = APIRouter(tags=["WebSocket"])


def _get_db():
    """Create a database session for WebSocket handlers."""
    return SessionLocal()


@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    WebSocket connection endpoint.
    Authenticates via JWT token in the URL path.
    Handles:
    - Ping/pong keepalive
    - WebRTC call signaling (offer, answer, ICE, end, reject)
    - Real-time notifications
    """
    # Validate token
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = int(payload["sub"])

    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()

            # Simple ping/pong keepalive
            if data == "ping":
                await websocket.send_text("pong")
                continue

            # Parse JSON signaling messages
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            # ─── Call Offer ─────────────────────────────────
            if msg_type == "call:offer":
                await _handle_call_offer(user_id, msg)

            # ─── Call Answer ────────────────────────────────
            elif msg_type == "call:answer":
                await _handle_call_answer(user_id, msg)

            # ─── ICE Candidate ──────────────────────────────
            elif msg_type == "call:ice":
                to_user = msg.get("to_user_id")
                if to_user:
                    await manager.relay_to_user(user_id, int(to_user), {
                        "type": "call:ice",
                        "candidate": msg.get("candidate"),
                        "call_id": msg.get("call_id"),
                    })

            # ─── Call Reject ────────────────────────────────
            elif msg_type == "call:reject":
                await _handle_call_reject(user_id, msg)

            # ─── Call End ───────────────────────────────────
            elif msg_type == "call:end":
                await _handle_call_end(user_id, msg)

            # ─── Call Busy ──────────────────────────────────
            elif msg_type == "call:busy":
                to_user = msg.get("to_user_id")
                call_id = msg.get("call_id")
                if to_user:
                    await manager.send_to_user(int(to_user), {
                        "type": "call:busy",
                        "from_user_id": user_id,
                        "call_id": call_id,
                    })

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        # If user was in a call, handle cleanup
        active_call_id = manager.get_active_call_id(user_id)
        if active_call_id:
            manager.clear_call(user_id)
            db = _get_db()
            try:
                call = db.query(CallLog).filter(CallLog.id == active_call_id).first()
                if call:
                    now = datetime.now(timezone.utc)
                    if call.status == CallStatus.RINGING:
                        call.status = CallStatus.MISSED
                    elif call.status == CallStatus.ACTIVE:
                        call.status = CallStatus.COMPLETED
                        call.ended_at = now
                        if call.started_at:
                            call.duration_seconds = int((now - call.started_at).total_seconds())
                    db.commit()

                    # Notify the other participant
                    other_user_id = call.callee_id if call.caller_id == user_id else call.caller_id
                    manager.clear_call(other_user_id)
                    await manager.send_to_user(other_user_id, {
                        "type": "call:end",
                        "call_id": active_call_id,
                        "reason": "disconnected",
                        "from_user_id": user_id,
                    })
            finally:
                db.close()


# ─── Signaling Handlers ────────────────────────────────────


async def _handle_call_offer(caller_id: int, msg: dict):
    """Handle an outgoing call offer."""
    callee_id = int(msg.get("to_user_id", 0))
    job_id = msg.get("job_id")
    sdp = msg.get("sdp")
    caller_name = msg.get("caller_name", "Unknown")

    if not callee_id or not sdp:
        return

    # Check if callee is online
    if not manager.is_online(callee_id):
        await manager.send_to_user(caller_id, {
            "type": "call:user_offline",
            "user_id": callee_id,
        })
        return

    # Check if callee is already in a call
    if manager.is_in_call(callee_id):
        await manager.send_to_user(caller_id, {
            "type": "call:busy",
            "user_id": callee_id,
        })
        return

    # Create call log in database
    db = _get_db()
    try:
        call = CallLog(
            caller_id=caller_id,
            callee_id=callee_id,
            job_id=int(job_id) if job_id else None,
            status=CallStatus.RINGING,
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        call_id = call.id
    finally:
        db.close()

    # Mark both users as in a call (ringing state)
    manager.set_in_call(caller_id, call_id)
    manager.set_in_call(callee_id, call_id)

    # Send offer to callee
    await manager.send_to_user(callee_id, {
        "type": "call:offer",
        "call_id": call_id,
        "from_user_id": caller_id,
        "caller_name": caller_name,
        "job_id": job_id,
        "sdp": sdp,
    })

    # Confirm call created to caller
    await manager.send_to_user(caller_id, {
        "type": "call:ringing",
        "call_id": call_id,
        "to_user_id": callee_id,
    })


async def _handle_call_answer(callee_id: int, msg: dict):
    """Handle a call answer from the callee."""
    call_id = msg.get("call_id")
    caller_id = msg.get("to_user_id")
    sdp = msg.get("sdp")

    if not call_id or not caller_id or not sdp:
        return

    caller_id = int(caller_id)

    # Update call log to active
    db = _get_db()
    try:
        call = db.query(CallLog).filter(CallLog.id == int(call_id)).first()
        if call and call.status == CallStatus.RINGING:
            call.status = CallStatus.ACTIVE
            call.started_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()

    # Send answer to caller
    await manager.send_to_user(caller_id, {
        "type": "call:answer",
        "call_id": call_id,
        "from_user_id": callee_id,
        "sdp": sdp,
    })


async def _handle_call_reject(callee_id: int, msg: dict):
    """Handle a call rejection."""
    call_id = msg.get("call_id")
    caller_id = msg.get("to_user_id")

    if not call_id:
        return

    # Update call log
    db = _get_db()
    try:
        call = db.query(CallLog).filter(CallLog.id == int(call_id)).first()
        if call and call.status == CallStatus.RINGING:
            call.status = CallStatus.REJECTED
            call.ended_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()

    # Clear call state
    manager.clear_call(callee_id)
    if caller_id:
        caller_id = int(caller_id)
        manager.clear_call(caller_id)
        await manager.send_to_user(caller_id, {
            "type": "call:rejected",
            "call_id": call_id,
            "from_user_id": callee_id,
        })


async def _handle_call_end(user_id: int, msg: dict):
    """Handle ending an active or ringing call."""
    call_id = msg.get("call_id")
    if not call_id:
        return

    db = _get_db()
    try:
        call = db.query(CallLog).filter(CallLog.id == int(call_id)).first()
        if not call:
            return

        now = datetime.now(timezone.utc)

        if call.status == CallStatus.RINGING:
            # Caller cancelled before answer
            call.status = CallStatus.MISSED
            call.ended_at = now
        elif call.status == CallStatus.ACTIVE:
            call.status = CallStatus.COMPLETED
            call.ended_at = now
            if call.started_at:
                call.duration_seconds = int((now - call.started_at).total_seconds())

        db.commit()

        # Determine the other participant
        other_user_id = call.callee_id if call.caller_id == user_id else call.caller_id

        # Clear call state for both users
        manager.clear_call(user_id)
        manager.clear_call(other_user_id)

        # Notify the other participant
        await manager.send_to_user(other_user_id, {
            "type": "call:ended",
            "call_id": call_id,
            "from_user_id": user_id,
            "duration_seconds": call.duration_seconds or 0,
        })
    finally:
        db.close()
