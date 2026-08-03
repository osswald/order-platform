## 1. Tests first

- [x] 1.1 Add failing tests: warm second `get_bundle_dict` does not re-`json.loads` SQLite body; cold miss loads once and populates cache
- [x] 1.2 Add failing tests: after `save_bundle` with mutated stock, next read sees updated sellable state; `invalidate` forces reload
- [x] 1.3 Add failing tests: strict helper still errors when unpaired; raw helper still returns `None` when empty; sync 304 / identical skip does not require cache clear

## 2. Cache implementation

- [x] 2.1 Implement process-memory cache in `bundle_cache.py` (`get`/`set`/`invalidate`) with deepcopy-on-read (or equivalent isolation) and preserve existing error/`None` semantics
- [x] 2.2 Wire `save_bundle` to update the in-process cache after durable write
- [x] 2.3 Wire sync `pull_bundle` (real body change) to set/invalidate cache; leave cache warm on 304 / identical-body skip
- [x] 2.4 Grep for other direct `SyncedBundle.json_body` writers and route them through cache update/invalidate

## 3. Verification

- [ ] 3.1 Run Pi backend tests (`cd pi/backend && uv run python -m pytest tests/ -v`)
- [ ] 3.2 Run `./scripts/lint.sh --staged` (or full) before commit
