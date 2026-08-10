**Root cause:** The cursor advances by `page_size - 1` instead of `page_size`, causing each page to overlap the previous one by one record. With `page_size=2` and 3 records, the slices are `[0:2]`, `[1:3]`, `[2:4]` → `["alpha","beta"]`, `["beta","gamma"]`, `["gamma"]`, producing duplicates.

**Smallest safe fix:** Change the cursor increment to `page_size`.

```python
# pagination_service.py, line 14
cursor += page_size  # was: cursor += page_size - 1
```
