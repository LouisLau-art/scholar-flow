# Quickstart: Manuscript Details and Invoice Info Management

## Backend: Updating Invoice Metadata
Use the updated endpoint to persist changes. The backend will automatically handle the audit logging.

```bash
curl -X PUT "/api/v1/editor/manuscripts/{id}/invoice-info" 
     -H "Authorization: Bearer {token}" 
     -H "Content-Type: application/json" 
     -d '{
       "authors": "John Doe, Jane Smith",
       "affiliation": "University of Science",
       "apc_amount": 1000.00,
       "funding_info": "Grant #12345"
     }'
```

## Frontend: Displaying Organized Files
The `FileManagementSection` component accepts a grouped file object.

```tsx
<FileManagementSection 
  groups={{
    "Cover Letter": coverLetterFiles,
    "Original Manuscript": manuscriptFiles,
    "Peer Review Reports": reviewerFiles
  }} 
/>
```
