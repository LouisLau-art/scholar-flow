# Quickstart: Testing Reviewer Magic Link

## Prerequisites

1. **Backend**: Ensure `pyjwt` is installed (`pip install pyjwt`).
2. **Env**: Ensure `SECRET_KEY` is set in `backend/.env`.

## Testing the Flow (Manual)

1. **Invite**:
   - Log in as Editor.
   - Go to a manuscript.
   - Click "Invite Reviewer".
   - Check backend logs or Mailtrap (if configured) for the generated link.

2. **Access**:
   - Open the link in Incognito Mode.
   - Verify you land on the "Reviewer Workspace".
   - Verify you can see the manuscript title.

3. **Expiration (Simulation)**:
   - Manually call the verify endpoint with an old token.
   - Expect 401 Unauthorized.

## Running Tests

```bash
# Backend Logic
cd backend
pytest tests/unit/test_magic_link.py

# Frontend Middleware
cd frontend
npm run test tests/middleware.spec.ts
```
