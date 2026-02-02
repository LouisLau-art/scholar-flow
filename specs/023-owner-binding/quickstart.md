# Quickstart: Owner Binding Testing

## 1. Backend Integration Tests

Run the dedicated test suite for owner binding logic:

```bash
cd backend
pytest tests/integration/test_owner_binding.py -v
```

**Key Scenarios:**
- Binding valid editor -> Success
- Binding non-staff user -> 403 Forbidden
- Fetching details -> Owner metadata included

## 2. Frontend Manual Verification

1. Login as Editor (`editor@example.com`).
2. Open any manuscript in "Under Review".
3. Check right sidebar for "Owner" combobox.
4. Search for another editor (e.g., "admin").
5. Select and verify toast "Owner updated".
6. Refresh page -> Owner persists.
7. Go to Pipeline List -> Verify "Owner" column shows the name.
