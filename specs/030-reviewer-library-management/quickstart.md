# Quickstart: Reviewer Library Management

## Backend: Adding to Library (Service Layer)

```python
# app/services/reviewer_service.py

def add_to_library(data: ReviewerCreateSchema):
    # 1. Check if user exists in auth.users
    # 2. Create if not, using supabase_admin (no password)
    # 3. Create/Update user_profiles with Title and Homepage
    # 4. Do NOT trigger email
    return profile
```

## Frontend: Assignment Workflow

```tsx
// components/editor/ReviewerAssignment.tsx

const handleAssign = async (reviewerId: string) => {
  // Call existing assignment endpoint which now supports 
  // choosing from the library.
  await api.post(`/api/v1/editor/manuscripts/${id}/assign`, { reviewer_id: reviewerId });
}
```
