# Quickstart: Production Email Service

## Prerequisites

- **Resend API Key**: Obtain from [Resend Dashboard](https://resend.com/api-keys).
- **Python Dependencies**: `resend`, `tenacity`, `itsdangerous`.

## Configuration

Add the following to your `backend/.env` file:

```bash
# Email Service (Resend)
RESEND_API_KEY=re_123456789
EMAIL_SENDER=ScholarFlow <onboarding@resend.dev>  # Use your verified domain in production
```

## Usage

### Injecting the Service

The `EmailService` is available in the dependency injection container or can be instantiated directly in `core`.

```python
from app.core.mail import email_service
from fastapi import BackgroundTasks

@router.post("/invite")
async def invite_reviewer(
    email: str, 
    background_tasks: BackgroundTasks
):
    # 1. Generate Token
    token = email_service.create_token(email, salt="reviewer-invite")
    link = f"https://scholarflow.io/review/accept?token={token}"
    
    # 2. Enqueue Email
    background_tasks.add_task(
        email_service.send_template_email,
        to_email=email,
        subject="Invitation to Review",
        template_name="reviewer_invite.html",
        context={"link": link, "title": "My Paper"}
    )
    
    return {"message": "Invitation sent"}
```

### Creating Templates

Add new HTML templates to `backend/app/core/templates/`:

```html
<!-- reviewer_invite.html -->
<!DOCTYPE html>
<html>
<body>
    <h1>Hello!</h1>
    <p>You have been invited to review.</p>
    <a href="{{ link }}">Click here to accept</a>
</body>
</html>
```

## Testing

Run the integration tests to verify connectivity (mocks Resend by default):

```bash
pytest backend/tests/integration/test_email_service.py
```
