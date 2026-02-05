# Quickstart: Post-Acceptance Workflow

## Backend: Advance Stage
Use the dedicated endpoint to move the manuscript forward. It automatically determines the next stage based on current status.

```bash
curl -X POST "/api/v1/editor/manuscripts/{id}/production/advance" 
     -H "Authorization: Bearer {token}"
```

## Backend: Revert Stage
Use the revert endpoint to go back one step.

```bash
curl -X POST "/api/v1/editor/manuscripts/{id}/production/revert" 
     -H "Authorization: Bearer {token}"
```

## Frontend: Production Actions Component
A simplified React component example.

```tsx
const ProductionActions = ({ status, onAdvance, onRevert }) => {
  const nextStage = getNextStage(status); // e.g., 'layout' -> 'English Editing'
  
  return (
    <div className="flex gap-2">
      <Button onClick={onRevert} variant="outline">Revert</Button>
      <Button onClick={onAdvance}>Start {nextStage}</Button>
    </div>
  );
};
```
