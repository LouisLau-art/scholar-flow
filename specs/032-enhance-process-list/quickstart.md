# Quickstart: Enhance Manuscripts Process List

## Frontend: Filter Hook
Using `useSearchParams` for state.

```tsx
// hooks/useProcessFilters.ts
const useProcessFilters = () => {
  const router = useRouter();
  const searchParams = useSearchParams();

  const setFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) params.set(key, value);
    else params.delete(key);
    router.replace(`?${params.toString()}`);
  };
  
  return { setFilter, filters: Object.fromEntries(searchParams) };
};
```

## Backend: Filtered Query
Building the query dynamically.

```python
# services/editor_service.py
query = client.table("manuscripts").select("*, journals(title)")

if filters.status:
    query = query.in_("status", filters.status)
if filters.q:
    query = query.or_(f"id.eq.{filters.q},title.ilike.%{filters.q}%")
```
