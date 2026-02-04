# Quickstart: Workflow and UI Standardization

## Core Workflow Implementation

### 1. Status Transition
To move a manuscript to the next stage, use the `editorial_service.update_status` method (Backend) or call the PATCH endpoint.

```python
# Example: Transition to Layout
await editorial_service.update_status(
    manuscript_id=uuid,
    to_status=ManuscriptStatus.LAYOUT,
    changed_by=editor_id
)
```

### 2. Frontend Table View
The main view is located at `/editor/manuscripts-process`. It uses the `ManuscriptTable` component which supports server-side filtering.

```typescript
// Filtering by Journal and Status
const { data } = useManuscriptsProcess({
  journalId: 'jcr-001',
  status: ['pre_check', 'under_review']
});
```

### 3. Invoice Info Editing
On the manuscript details page (`/editor/manuscript/[id]`), the `InvoiceInfoSection` allows editing metadata.

```typescript
const handleSave = async (metadata: InvoiceMetadata) => {
  await api.updateInvoiceInfo(manuscriptId, metadata);
  toast.success('Invoice info updated');
};
```
