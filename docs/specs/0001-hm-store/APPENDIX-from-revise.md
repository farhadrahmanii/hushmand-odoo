module=True`, `base.partially_updated_database` is **re-inserted** whenever any module is still `to upgrade`/`to install`/`to remove` (`modules/loading.py:599-607`). The flag is therefore not a restart witness.
- Prefork SIGHUP is a deliberately overlapping graceful reload: `PreforkServer.stop()` calls `fork_and_reload()` then `stop_workers_gracefully()` (`service/server.py:1174-1181`); `fork_and_reload()` forks, the parent `_reexec()`s and the child waits up to 60 s for the new master's ready signal with old workers still serving (`server.py:1105-1134`); the new master signals ready only **after** `preload_registries(preload)` (`server.py:1196-1209`); `stop_workers_gracefully()` then tells workers to "finish their current workload then stop" (`server.py:1136-1170`).
- Threaded mode runs `with Registry._lock: self.start(stop=stop); rc = preload_registries(preload)` before the request loop and before `process_limit` is ever called (`service/server.py:700-703`).
- `process_limit` applies `limit_time_real` to any non-daemon HTTP thread and to cron threads, in **every** mode; once `limit_reached_time` is set the main loop calls `self.reload()` (`server.py:503-524`, `732-751`), and `reload()` is `os.kill(self.pid, signal.SIGHUP)` (`server.py:764-765`).
- `nodb_routing_map` is built only from `[''] + config['server_wide_modules']` with `nodb_only=True` (`http.py:2758-2768`), so a module installed at runtime can never own a nodb route.
- `db_filter(dbs, host=None)` applies `dbfilter` against the request Host, else restricts to `config['db_name']` (`http.py:389+`).
- `list_dbs(force)` short-circuits to `sorted(config['db_name'])` when `dbfilter` is unset and `db_name` is set, and otherwise returns only databases whose owner is the connecting role (`service/db.py:434-453`).
- `check_identity` raises `UserError("This method can only be accessed over HTTP")` with no `request`, and otherwise returns an `res.users.identitycheck` action instead of calling the method when the last check is older than 10 minutes (`addons/base/models/res_users.py:87-126`).
- `pg_dump` is present in the `odoo:19` image at `/usr/bin/pg_dump`; the process runs as `uid=100(odoo) gid=101(odoo)`; `/var/lib/odoo/addons/19.0` is `dr-x------ odoo odoo`.
- `ir_config_parameter` has only `key` and `value` NOT NULL, `id` defaulting from `ir_config_parameter_id_seq`, and a UNIQUE constraint `ir_config_parameter_key_uniq` on `(key)` — so the `ON CONFLICT (key) DO UPDATE` in `neutralize.sql` is valid.

**Carried from the briefs (not re-read this pass):**
- `initialize_sys_path()` adds `tools.config.addons_data_dir` whatever `addons_path` says, before every `addons_path` entry (`modules/module.py:141-171`).
- `addons_data_dir` = `<data_dir>/addons/19.0`, created `0o500` "will need manual +w to activate it" (`tools/config.py:1005-1017`).
- `Manifest._get_manifest_from_addons` is an `lru_cache` that core never clears (`modules/module.py:279`); a cached miss strands a module in `to install`.
- `load_openerp_module` returns early when the module is already in `sys.modules` (`module.py:502`); there is no `importlib.reload` in core.
- `Registry.new` deletes `base.partially_updated_database` in its own committed transaction and loads with `update_module=True` (`orm/registry.py:160-176`); on failure it calls `reset_modules_state` (`modules/loading.py:611-631`).
- STEP 2 runs `update_list()` when updating (`loading.py:423-427`); `latest_version` is written on a successful load (`:269`).
- `button_upgrade` calls `update_list()`, marks installed dependents, and `button_install`s new dependencies (`base/models/ir_module.py:704-752`).
- `_button_immediate_function` sets `lock_timeout 3s`, refuses on pending module states, and locks `ir_module_module` + `ir_cron` (`ir_module.py:599-659`) — copied, not called.
- `assert_log_admin_access` requires `env.is_admin()` and logs ALLOW/DENY (`ir_module.py:55-73`); `is_admin()`/`is_system()` at `orm/environments.py:182-190`.
- `restart()` is SIGHUP to `server.pid` on POSIX (`service/server.py:1680-1687`); Odoo's own delayed-restart thread is `addons/iot_drivers/tools/helpers.py:50-61`.
- `cr.postcommit` callbacks (`sql_db.py:166`, run at 568).
- `database.uuid` is `uuid1`, regenerated on duplicate and on restore with `copy=True` (`base/models/ir_config_parameter.py:18-25`; `service/db.py:185-205, 372-374`).
- Neutralize runs `<module>/data/neutralize.sql` for installed modules (`modules/neutralize.py:18-33`).
- CSRF tokens are checked only for non-safe methods (`http.py:2493`); JSON-RPC accepts only `application/json` (`:2544-2554`); request cap 128 MiB (`:247`); `web.max_file_upload_size` (`web/models/ir_http.py:91-94`).
- Unknown `odoo.conf` keys are stored with a WARNING and readable via `config.get()` (`tools/config.py:164-168, 901-917`); `limit_time_real` default 120 (`:488`); `'reload' in config['dev_mode']` gates the file watcher (`service/server.py:1657`).
- `imported=True` modules are excluded from the load domain (`base_import_module/models/ir_module.py:38-52`); import extracts only xml/csv/sql, `static/`, `i18n/` and drops `.py`.
- Python 3.12 `zipfile._extract_member` has no symlink or `external_attr` handling — and hm_store never calls it.
- Migration scripts run only when `installed < script_version <= current` (`modules/migration.py:195-208`); there is no downgrade guard.
- Container libraries: `cryptography` 41.0.7, `requests` 2.31.0.

---

## Appendix B — UNVERIFIED, and the slice that settles each

Items marked UNVERIFIED in revision 1 that are now **settled** are listed first with their evidence, so nobody spends a probe on them again.

| Settled this pass | Evidence |
|---|---|
| `_register_hook` is called during registry load | `modules/loading.py:585-591` (container) — only "does the write commit in every boot shape" remains, S1(9) |
| `pg_dump` is present in the `odoo:19` image | `/usr/bin/pg_dump` (container) |
| `ir_config_parameter` column requirements for the raw insert in `neutralize.sql` | `\d ir_config_parameter` on the live database (container) |
| Whether `check_identity` refuses `/json/2` and XML-RPC API-key calls | `res_users.py:87-126` (container): XML-RPC has no `request` → `UserError`; `/json/2` gets a wizard action and the method never runs |
| What a prefork graceful reload does to a worker mid-upgrade | `server.py:1105-1134, 1174-1181, 1196-1209` (container): old generation serves for up to 60 s while the new master runs the whole upgrade. This is why `in_process` is refused in prefork |
| Whether a no-cookie `auth='none'` route can observe a restart | It cannot: `nodb_routing_map` is `server_wide_modules` only (`http.py:2758-2768`), and a db-bound route is itself the request that loads the registry (`http.py:2849-2852`, `2274-2277`; `orm/registry.py:92, 99-106`). The route is removed |
| Whether the `/web/dataset/call_button` path guard covers server actions | It does not (`web/controllers/action.py:53`). Allowlist widened and mutating entry points converted to `type="object"` |

| Still UNVERIFIED | Settled in |
|---|---|
| In-process placement + install works on the real target shapes; the stale-manifest negative case behaves as probed | **S1 (1,2,3)** |
| Each of the three restart methods works when Odoo is PID 1 in the `odoo:19` image, and `in_process` in threaded mode really has zero generation overlap | **S1 (4a-4c)**, enforced afterwards by preflight 11 and 13 |
| The measured size of the prefork SIGHUP overlap window (expected non-zero; recorded for the record) | **S1 (4d)** |
| That a write made in `_register_hook` is committed in every boot shape, so `hm_store.boot_seq` is a reliable witness | **S1 (9)** |
| That `os.access(W_OK)` returns True for uid 0 against a `0500` directory in this image (POSIX says yes; not run here) | **S1 (10)** |
| Exactly what a crash between swap and commit, and between commit and restart, leaves behind | **S1 (8)** |
| Whether a failed module load's database changes are rolled back (so whether a `pg_restore` is required) | **S8 (3)** |
| Whether OpenSSL 3.0+ (`pkeyutl -verify -rawin`) is available on both bootstrap targets; otherwise the fallback verifier is the documented path | **S10** |
| Whether the GitHub repositories are private, which decides D17 | **S2** |
| Production PHP, nginx and TLS on the licence VPS; PHP upload and body limits | **S2** |
| `display="always"` list-header buttons in 19 (avoided entirely; `type="object"` buttons used instead) | not needed |
| Odoo.sh runtime persistence (treated as unsupported) | never — out of scope |