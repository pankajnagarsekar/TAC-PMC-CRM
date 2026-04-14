"""Track B: Voice log service tests — create, list, schema validation."""
import pytest


@pytest.mark.asyncio
async def test_voice_log_create(client, supervisor_token, test_project):
    payload = {
        "project_id": test_project["id"],
        "audio_url": "https://storage.example.com/audio/log1.mp3",
        "transcription": "Concrete work completed on grid B4",
        "duration_seconds": 45,
    }
    resp = await client.post(
        "/api/v1/voice-logs",
        json=payload,
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    assert data["transcription"] == "Concrete work completed on grid B4"


@pytest.mark.asyncio
async def test_voice_log_list_by_project(client, supervisor_token, test_project):
    await client.post(
        "/api/v1/voice-logs/",
        json={
            "project_id": test_project["id"],
            "audio_url": "https://storage.example.com/audio/log2.mp3",
            "transcription": "Steel reinforcement complete",
            "duration_seconds": 30,
        },
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )

    resp = await client.get(
        f"/api/v1/projects/{test_project['id']}/voice-logs",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert isinstance(items, list)
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_voice_log_schema_validation_missing_audio_url(client, supervisor_token, test_project):
    payload = {
        "project_id": test_project["id"],
        "transcription": "Missing audio URL",
        "duration_seconds": 10,
    }
    resp = await client.post(
        "/api/v1/voice-logs",
        json=payload,
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_voice_log_negative_duration_rejected(client, supervisor_token, test_project):
    payload = {
        "project_id": test_project["id"],
        "audio_url": "https://storage.example.com/x.mp3",
        "transcription": "Test",
        "duration_seconds": -5,
    }
    resp = await client.post(
        "/api/v1/voice-logs",
        json=payload,
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_voice_log_admin_can_list(client, admin_token, test_project):
    resp = await client.get(
        f"/api/v1/projects/{test_project['id']}/voice-logs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
