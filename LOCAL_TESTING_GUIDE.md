# Zia Local Testing Guide

## Status ✅

**Backend:** Running on http://localhost:8000
**Database:** PostgreSQL running (migrations applied)
**Redis:** Running (session storage)

---

## Quick Start — Test Backend Endpoints

### 1️⃣ Test Health Check

```bash
curl -X GET http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-03-24T10:30:00Z"
}
```

---

### 2️⃣ Create or Get Profile (Phone-Based)

```bash
curl -X POST http://localhost:8000/candidate/profile/create-or-get \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+919876543210",
    "name": "Aditya Kumar"
  }'
```

**Expected Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "phone": "+919876543210",
  "name": "Aditya Kumar",
  "gender": "unknown",
  "current_role": null,
  "yoe": null,
  "tech_stack": null,
  "company": null,
  "company_type": null,
  "location": null,
  "comp_current": null,
  "comp_target": null,
  "goals": null,
  "relationship_stage": 1,
  "mixing_board_state": {"priyanka": 0.2, "sister": 0.8},
  "assessment_status": "not_started",
  "nudge_count": 0
}
```

**Save the phone number for next tests:** `+919876543210`

---

### 3️⃣ Send a Chat Message (Create Session)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "hi zia i want to talk about my career"
  }'
```

**Expected Response:**
```json
{
  "response": "Hey! I'm Zia, your AI career companion...",
  "session_id": "abc123def456",
  "active_skill": "career_guide",
  "turn_number": 1,
  "timestamp": "2026-03-24T10:31:00Z"
}
```

**Save the session_id:** `abc123def456`

---

### 4️⃣ Continue Conversation (Keep Session)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "my CTC is 18 lakhs",
    "session_id": "abc123def456"
  }'
```

**Expected Response:**
```json
{
  "response": "That's solid! Let's talk about...",
  "session_id": "abc123def456",
  "active_skill": "salary_navigator",
  "turn_number": 2,
  "timestamp": "2026-03-24T10:32:00Z"
}
```

---

### 5️⃣ Get Profile by Phone

```bash
curl -X GET http://localhost:8000/candidate/profile/+919876543210
```

**Expected Response:** Same as step 2 (unless fields were updated)

---

### 6️⃣ Update Profile

```bash
curl -X POST http://localhost:8000/candidate/profile/update \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+919876543210",
    "current_role": "Senior Backend Engineer",
    "yoe": 4.5,
    "tech_stack": "Python, FastAPI, PostgreSQL",
    "location": "Bangalore"
  }'
```

**Expected Response:** Updated profile with new fields populated

---

### 7️⃣ List All Conversations for User

```bash
curl -X GET http://localhost:8000/candidate/conversations/+919876543210
```

**Expected Response:**
```json
[
  {
    "id": "abc123def456",
    "candidate_id": "550e8400-e29b-41d4-a716-446655440000",
    "channel": "text",
    "started_at": "2026-03-24T10:31:00Z",
    "ended_at": null,
    "turn_count": 2,
    "relationship_stage_at_start": 1,
    "messages": [
      {
        "turn": 1,
        "user_message": "hi zia i want to talk about my career",
        "zia_response": "Hey! I'm Zia, your AI career companion...",
        "active_skill": "career_guide",
        "timestamp": "2026-03-24T10:31:00Z",
        "feedback": null
      },
      {
        "turn": 2,
        "user_message": "my CTC is 18 lakhs",
        "zia_response": "That's solid! Let's talk about...",
        "active_skill": "salary_navigator",
        "timestamp": "2026-03-24T10:32:00Z",
        "feedback": null
      }
    ],
    "created_at": "2026-03-24T10:31:00Z"
  }
]
```

---

### 8️⃣ Get Messages from Specific Conversation

```bash
curl -X GET http://localhost:8000/candidate/conversation/abc123def456/messages
```

**Expected Response:** Array of message objects (same as `messages` array above)

---

### 9️⃣ Submit Feedback on a Message

```bash
curl -X POST http://localhost:8000/candidate/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc123def456",
    "turn_number": 1,
    "rating": "up",
    "note": "Great response from Zia!"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Feedback recorded successfully."
}
```

**Then verify:** Run step 7 or 8 again — the `messages` array should now show `"feedback": "up"` for that turn.

---

### 🔟 Reset Session

```bash
curl -X POST http://localhost:8000/chat/reset
```

**Expected Response:**
```json
{
  "message": "Session cleared",
  "cleared_turns": 2
}
```

---

## What's Tested ✅

| Feature | Endpoint | Test Step |
|---------|----------|-----------|
| Health Check | `GET /health` | 1 |
| Create Profile | `POST /candidate/profile/create-or-get` | 2 |
| Send Message | `POST /chat` | 3 |
| Continue Conversation | `POST /chat` + session_id | 4 |
| Get Profile | `GET /candidate/profile/{phone}` | 5 |
| Update Profile | `POST /candidate/profile/update` | 6 |
| List Conversations | `GET /candidate/conversations/{phone}` | 7 |
| Get Message History | `GET /candidate/conversation/{session_id}/messages` | 8 |
| Submit Feedback | `POST /candidate/feedback` | 9 |
| Reset Session | `POST /chat/reset` | 10 |

---

## View Logs (Debugging)

**Backend logs:**
```bash
docker compose logs -f backend
```

**Database logs:**
```bash
docker compose logs -f postgres
```

**Redis logs:**
```bash
docker compose logs -f redis
```

---

## Stop Services

```bash
docker compose down
```

---

## What's Next 🚀

Once all 10 tests pass:

1. **Deploy to Render** — Apply migration on Render via Shell:
   ```bash
   cd /opt/render/project/src
   /root/.venv/bin/python -m alembic upgrade head
   ```

2. **Test on Production** — Replace `localhost:8000` with your Render URL

3. **Build Next.js Frontend** — Begin frontend implementation

---

## Troubleshooting

**"Connection refused" on localhost:8000?**
- Check if containers are running: `docker compose ps`
- If not running: `docker compose up -d`
- View logs: `docker compose logs backend`

**"Profile not found" error?**
- Make sure you used the exact phone number from step 2
- Phone numbers are stored with E.164 format: `+{country_code}{number}`

**"Conversation not found"?**
- Use the session_id from step 3's response
- Session IDs are UUIDs, not custom strings

**Database migrations failed?**
- Check Postgres is healthy: `docker compose ps`
- View logs: `docker compose logs postgres`
- Reset database (DESTRUCTIVE): `docker compose down && docker volume rm request_postgres_data`

