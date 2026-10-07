# Spec 0001 — hm_store: install Hushmand modules from inside Odoo

**Status:** Draft — **revision 3**, answering `REVIEW-odoo19.json` (4 blockers, 5 majors, 4 minors; all 13 addressed here) on top of **revision 2**, which answered `REVIEW-security.json` (3 blockers, 7 majors, 4 minors). Revision 2's security fixes are preserved unchanged except where Odoo 19 behaviour contradicted them, and those two places are called out by name in §2.4 (the status route) and §2.11 (the restart witness).
**Owner:** vendor (solo)
**Spec file:** `E:\web\hushmand-odoo\docs\specs\0001-hm-store\SPEC.md`
**Repos:** `E:\web\hushmand-odoo` (HEAD `88cca8f`), `E:\web\hushmand-license-server` (HEAD `4d226b9`)
**Target:** Odoo 19.0 (`19.0-20260817`), Python 3.12, self-hosted Linux only

**Evidence markers.** `(brief)` = stated in one of the four input briefs, which were read against the container source or the 19.0 branch. `(repo)` = re-read in the Hushmand repos during this pass. `(container r2)` = read in the running `hushmand-odoo` container during revision 2, at `/usr/lib/python3/dist-packages/odoo`. `(container r3)` = read in the same container during revision 3, at `19.0-20260817`. **UNVERIFIED** = not read anywhere; every one is listed in Appendix B with the slice that settles it. The Docker daemon was down when revision 1 was written; it was **up for revisions 2 and 3**, so every fact those revisions newly depend on was read in the container. Everything else is unchanged from revision 1 and slice S1 still re-confirms the load-bearing items before any code is written.

**Revision 2 changes, in one paragraph.** The root of trust is no longer replayable, no longer self-updatable, and no longer bootstrapped from a hash in an email: a persisted keyring-serial floor and a sticky revocation set (§2.8a), a root pin held outside the tree hm_store updates plus a K_root co-signature for any release that changes it (§2.10 rule 7, §4.2b), and a K_root signature over the bootstrap zip checked against a fingerprint the operator holds from a non-vendor channel (§1.5, §4.3). Key custody is fixed at the source (K_licence re-keyed, signing split off the networked build host, the `--yes` bypass removed: §4.1, §4.2a/b, S5a). Server-side, authorisation now reads the registered row rather than the presented payload, throttling keys on the verified `licence_id`, and the `licence` envelope field is gone (§3.3–3.6). Two availability gaps are closed: a hard ceiling on the catalogue response before it is parsed (§2.8 step 1) and a freshness warning on the online path (§2.7 step 0). Every control the review named as correct — verify-before-parse ordering, the §2.10 unpack rules, no TLS-verify switch, the release-serial floor, no free downgrade — is unchanged and is tightened, never relaxed.

---

## 0. Shape and invariants

The vendor wants: any customer, on any self-hosted Odoo 19 with internet, installs one bootstrap module by hand, pastes a licence key, and clicks Install/Update for anything their licence covers.

**Eleven invariants. Nothing in this spec may break them.**

1. **Code is authorised only by an offline key.** The licence server signs nothing that decides which code runs. A total compromise of *every online vendor system* — the licence server's database, `.env`, TLS cert, DNS and portal, the store host, the bootstrap download host, and vendor email — yields denial of service and data exposure, never remote code execution on a customer's Odoo. This holds **only from the moment the operator has checked the K_root fingerprint against a copy the vendor does not control end to end** (§1.5 step 1). That one human comparison, done once per customer, is the base of the whole chain; revision 1 replaced it with a SHA-256 in an email, which made the sentence above false for every new install. Everything after it is machine-checked.
2. **Verify before parse.** The signature and the SHA-256 are checked **before `zipfile` ever opens the archive**.
3. **One apply path: the process that applies never loads the new code.** v1 never installs or upgrades in-process: the worker that runs Apply swaps files, marks the database and exits the request; the upgrade runs in a *later* registry load. That removes the per-worker stale-manifest hazard (brief: T1) in the applying worker, at the cost of a restart on fresh installs.

   **What it does not remove, corrected in revision 3.** Revision 1 and 2 also claimed this removes the mixed-code hazard (brief: T3). It does not, and the claim was false as written for the default deployment shape. `odoo.service.server.restart()` is SIGHUP to `server.pid` (`service/server.py:1681-1688`), and in prefork SIGHUP is a **graceful, deliberately overlapping** reload: `PreforkServer.stop()` calls `fork_and_reload()` and only then `stop_workers_gracefully()` (`server.py:1175-1181`, container r3); `fork_and_reload()` forks, the parent `_reexec()`s into the new master while the forked child waits **up to 60 s** for the new master's ready signal (`server.py:1105-1134`); and the new master emits that signal only *after* `preload_registries(preload)` (`server.py:1195-1209`) — so with `-d <db>` set, the old workers keep serving **old Python against a schema that is being migrated under them** for the entire migration, and `stop_workers_gracefully()` then lets each of them finish its current request. The listening socket is handed to the new master through `ODOO_HTTP_SOCKET_FD` and never closes (`server.py:1087-1089`, `1107-1113`), so nothing outside the server can even see the changeover. Therefore: **T3 is reduced, not eliminated.** The true invariant is *new code is loaded only by a process that started after the swap*; whether an *old* process is still serving alongside it depends on the restart method, and §2.9 G gives the operator a method (`hard`) with no overlap. The residual window is bounded by the stale-worker guard of §2.9 I, measured by S1(4d), and named in the UI by §2.9 H.
4. **Swap files before marking the database.** Order is: swap → clear manifest cache → `button_install`/`button_upgrade` → set `base.partially_updated_database` → commit → restart after the response. Marking first is wrong: a worker recycled in the gap consumes the flag with the **old** code and leaves a silent, persistent inconsistency.
5. **Placed trees must stay movable.** Files `0640`, directories `0750`. A `0550` directory cannot be renamed into a new parent on Linux (`rename(2)` needs write permission on the directory itself to rewrite `..`), which would make the backup swap fail *after* the flag was committed. Where a tree must be moved, `chmod 0750` on its top-level directory runs first, unconditionally.
6. **hm_store never runs `chmod` on the addons data dir and never writes the opt-in.** Odoo creates `<data_dir>/addons/19.0` at mode `0500` deliberately, "will need manual +w to activate it" (brief: `tools/config.py:1005-1017`). The operator's one command is the opt-in. The Odoo process *could* chmod itself (brief: probe T1), which is exactly why we do not.
7. **Nothing the server sends is ever rendered as HTML, and the server's free text is never displayed.** Error codes map to local translated strings.
8. **No unattended installs.** The cron checks and notifies; a human with a re-entered password applies.
9. **Every mutating action runs as the real admin user, never `sudo`**, so Odoo's own `assert_log_admin_access` ALLOW/DENY lines land in the server log with login and IP (brief: `ir_module.py:55-73`).
10. **Trust only ratchets forward.** Every trust input carries a serial, every serial has a floor persisted outside the document it validates, and a floor never falls: release serials (§2.7), keyring serials (§2.8a), and the revocation set, which is a union over everything ever seen and is never narrowed by a later document. A key that was revoked once stays revoked on that installation until an operator re-bootstraps by hand. Revision 1 had the release floor and not the keyring floor, which made revoking a stolen K_release a suggestion rather than a fact.
11. **The root pin is not part of what the store updates.** `ROOT_KEYS`, `ROOT_THRESHOLD` and the domain prefixes live in a file written once at bootstrap under `<data_dir>/hm_store/trust/root.json`, outside the tree the store swaps. hm_store refuses to place an `hm_store` archive whose `lib/trust.py` disagrees with that pin, unless the release carries a K_root co-signature naming the change (§2.10 rule 7). K_release signs code; it must never be able to decide which key signs code.

**Silence is not success** is a consequence of 1 and 10 worth stating separately: the online path must be able to tell "nothing new" from "someone is holding my updates", so a verified index that is old, or a long gap since the last successful catalogue call, is surfaced to the operator (§2.7 step 0). Invariant 1's "denial of service" is only acceptable when it is *visible*.

**Grafts onto the minimal design** (named by the judge, folded in below): a root-signed **keyring** so release keys rotate without reinstalling hm_store (§1.2); a mandatory **Test restart** readiness check (§2.6 check 11); an append-only **`audit.log`** outside the database (§2.12); a **progress page that survives the restart** (§2.9 H — the judge asked for a no-cookie status *route*, and revision 3 replaced it with a registry-free static-asset probe plus one authenticated call, because Odoo 19 cannot serve that route the way the graft assumed: §2.4); **`pg_dump` backup before updates** (§2.8 step 4); the server verifying the **exact signed payload bytes** instead of re-canonicalising JSON in PHP (§3.3); **licence registration** on the server, behind a flag (§3.4); **auto-rollback** only through a post-boot reconcile that S9's probe has proven first (§2.11).

**Grafts added in revision 2**, all of them answers to `REVIEW-security.json`: a persisted **keyring-serial floor** and a sticky revocation set (§2.8a); the **root pin** outside the updatable tree plus a K_root **trust update** for any change to it (§2.10 rule 7, §4.2b); a **K_root-signed bootstrap** verified against an out-of-band fingerprint (§1.5 step 1, §4.3); **split build and signing hosts** with the `--yes` bypass removed (§4.2a/b); **row-based server authorisation** and throttling on the verified `licence_id` (§3.3, §3.4, §3.6); an **installation keypair** pinned on first use (§3.4 step 5); a **bounded catalogue response** (§2.8 step 1); and **freshness warnings on the online path** (§2.7 step 0).

**Revision 3 changes, in one paragraph.** `REVIEW-odoo19.json` found four load-bearing Odoo 19 claims that are false, and each one is now either corrected or demoted to a written assumption with the slice that settles it. (1) The guard's `/web/dataset/call_button` path test rejected the spec's own menu entries, because `ir.actions.server` dispatches over `/web/action/run` (`web/controllers/action.py:53`, container r3): every **mutating** entry point becomes a `type="object"` button, the guard takes an explicit **path allowlist plus a call-kind**, and the cron gets its own non-mutating door (§2.4, §2.5). (2) Invariant 3's "always restart, so no mixed code" is false in prefork, where SIGHUP is a deliberately *overlapping* graceful reload (`service/server.py:1105-1134`, `1175-1181`, `1195-1209`): the invariant now says what actually holds, the overlap is measured rather than denied, and a **stale-worker guard** (§2.9 I) makes the residual window fail closed. Prefork operators are offered a **hard restart** that has no overlap at all (§2.9 G, preflight 19). (3) The no-cookie status route cannot observe a restart — a db-bound request is itself what loads the registry (`http.py:2849-2852`, `2274-2277`; `orm/registry.py:92`, `99-106`), and a runtime-installed module can never own a nodb route (`http.py:2758-2768`). **The route is removed**; progress is observed by a static-asset liveness probe plus exactly one long-timeout authenticated call (§2.4, §2.5). (4) `base.partially_updated_database` is re-inserted at the end of a *successful* load whenever modules are still pending (`modules/loading.py:599-607`), so it is not a restart witness: reconcile now compares a **boot marker** written by `hm.store.boot._register_hook` (`modules/loading.py:588-594`) against `applied_at` (§2.11). The five majors and four minors are answered in §2.6 (checks 5, 12, 19, 20), §2.7 step 7, §2.12, §2.14 and §7.

---

## 1. Architecture

### 1.1 Components and where they live

| # | Component | Path | Trust |
|---|---|---|---|
| C1a | **Build/verify host** (vendor laptop, full-disk encrypted, online). Runs git, `gh`, a browser, pip. **Holds no private key.** | — | untrusted for signatures; trusted only to assemble candidate bytes |
| C1b | **Signer** (air-gapped: no NIC associated, no DHCP lease, Wi-Fi/Bluetooth off; either a second machine or C1a booted from a separate offline live-USB — D19). Holds K_root, K_release, K_licence. Its only inputs are a `SIGN-REQUEST.json` and its only outputs are `.sig` files, carried on a USB stick. | — | trusted |
| C2 | Release signer | `hushmand-odoo/tools/release_signing.py` (new) | runs on C1b only |
| C3 | Release builder (staging half) | `hushmand-odoo/tools/build_release.py` (new `stage`, `bootstrap`, `bundle`, `assemble` subcommands) | runs on C1a; produces no signature |
| C4 | Release ledger (committed) | `hushmand-odoo/releases/19.0/ledger.json` (new) | informational; C1b's copy is authoritative |
| C5 | Licence issuer (key re-keyed in S5a) | `hushmand-odoo/tools/issue_license.py` | runs on C1b only |
| C6 | hm_license (existing, two changes) | `hushmand-odoo/addons/hm_license/` | trusted |
| C7 | **hm_store** (new) | `hushmand-odoo/addons/hm_store/` | trusted; this is the attack surface |
| C8 | Store API | `hushmand-license-server/app/Http/Controllers/Api/Odoo/V1/OdooStoreController.php` + `app/Services/Odoo/*` (new) | **untrusted for code**; trusted only for access control and availability |
| C9 | Release mirror | `hushmand-license-server/storage/app/private/odoo-releases/19.0/<serial>/` | untrusted mirror |
| C10 | Addons data dir | `<data_dir>/addons/19.0/` — on the module search path ahead of every `addons_path` entry, with no config change (brief: `modules/module.py:141-171`) | operator opts in once with `chmod 700` |
| C11 | hm_store work dir | `<data_dir>/hm_store/` — same filesystem as C10, **not** on the import path, not watched by `--dev=reload` | created `0700` by hm_store |
| C12 | Offline bundle | `hushmand-<serial>-<licence8>.hmpkg` | untrusted transport |
| C13 | **Root pin** — the one copy of `ROOT_KEYS` hm_store actually verifies against | `<data_dir>/hm_store/trust/root.json`, mode `0400` inside the `0700` work dir, written once at bootstrap and thereafter only by a K_root-authorised trust update (§2.10 rule 7) | trusted; deliberately **outside** C10, the tree the store swaps |
| C14 | **Bootstrap host** — static HTTPS hosting for `hm_store-bootstrap-r<N>.zip` and its K_root signature | a separate domain, separate registrar account, separate hosting account, separate TLS key, no shared credential with C8/C9 (D16) | untrusted; the K_root signature is the control, host separation is containment only |

`<data_dir>` is `odoo.tools.config['data_dir']`; the addons dir is `odoo.tools.config.addons_data_dir` = `<data_dir>/addons/19.0` (brief: `tools/config.py:1005-1017`). hm_store always resolves it from config and never hard-codes `/var/lib/odoo`.

### 1.2 Trust chain: which key signs what

| Key | Alg | Custody | Signs (with domain prefix) | Pinned/listed in | hm_store accepts it for | Never |
|---|---|---|---|---|---|---|
| **K_root** | Ed25519 | offline: paper + two encrypted USBs, separate locations; loaded only on C1b | `hushmand-keyring-v1\n` + keyring bytes; `hushmand-bootstrap-v1\n` + bootstrap zip bytes; `hushmand-trust-update-v1\n` + trust-update bytes | the **root pin** C13, `<data_dir>/hm_store/trust/root.json`, seeded at bootstrap from `lib/trust.py` `ROOT_KEYS` | the keyring, the bootstrap zip, a trust update | code, licences |
| **K_release** (`rel-2026-10`) | Ed25519 | C1b, passphrase-encrypted PKCS8 `~/.hushmand/release_signing_key.pem` | `hushmand-release-v1\n` + `release.json` bytes | the keyring, role `release` | **all code, except a change to the root pin** (§2.10 rule 7) | licences, keyrings, bootstraps, trust updates |
| **K_licence** (re-keyed in S5a; the plaintext key `VENDOR_PUBLIC_KEY = "MnlbtFCv2OmZp61U/YaQ36vwm1WloZ97iQXDeDWEA5c="`, repo: `hm_license.py:56`, is retired there) | Ed25519 | C1b, **passphrase-encrypted** PKCS8 `~/.hushmand/licence_signing_key.pem` — revision 1 left it at `NoEncryption()` (repo: `tools/issue_license.py:74`), in the same directory as K_release | licence envelopes, existing format, unchanged | `hm_license.py` `VENDOR_PUBLIC_KEYS`; server `config/odoo_store.php` `licence_public_keys` | entitlement | code |
| MyERP `LICENSE_SIGNING_SECRET` | Ed25519/libsodium | server `.env` | MyERP JWTs | — | **nothing** | everything Odoo |
| Bootstrap zip | Ed25519 by **K_root** | published on C14; the signature travels with it | — | verified against the **K_root fingerprint the operator holds out of band** (contract, signed quote PDF, onboarding call, printed card) | trust on first use, once | anything after that |

Chain for code: **root pin C13** (seeded from `ROOT_KEYS`, itself established by the K_root-signed bootstrap) → `keyring.json` (K_root, threshold `root`, serial ≥ persisted keyring floor, no revoked key ever re-admitted) → release-role keys → `release.json` (K_release, threshold `release`, serial ≥ persisted release floor) → `archive.sha256` and `files[].sha256` → bytes on disk.
Chain for entitlement: `hm.license.key` → hm_license `_decode` + `_verify_signature` (K_licence) → `modules`, `expires` → decision. **Stored payload fields are never used** (audit L2). Server-side the same envelope is verified again and then checked against the **registered row**, which is what actually authorises (§3.4).

Rules: keys are never fetched from the network, never read from `ir.config_parameter`, never taken from `/api/v1/health`. Every signature input is `PREFIX + body_bytes`, and the body carries a matching `_type`, so one document kind can never be replayed as another — the four prefixes are `hushmand-keyring-v1\n`, `hushmand-release-v1\n`, `hushmand-bootstrap-v1\n`, `hushmand-trust-update-v1\n`. Thresholds are declared in the keyring from day one (`{"root":1,"release":1}`) and can be raised to 2-of-2 later without an hm_store change. `keyring_serial` only ever increases **and the floor it is compared against is persisted on the client** (§2.8a); revocation is a new keyring with a higher serial listing `revoked_key_ids`, and the client's revocation set is the **union of every `revoked_key_ids` it has ever verified**, so a later keyring can add revocations but can never withdraw one.

**Why the root pin is a separate file (C13).** `lib/trust.py` ships inside the `hm_store` archive, and hm_store updates itself through the store (§2.2 "always entitled"). In revision 1 that meant one release signed with a stolen K_release could ship a `trust.py` pinning the attacker's roots, after which K_root could never revoke anything on that customer again — the recovery path in §7 was decorative. Two changes close it: the pin lives outside the swapped tree, and §2.10 rule 7 refuses, **before the swap**, any staged `hm_store` whose `trust.py` disagrees with the pin unless the release carries a K_root-signed `trust_update` naming exactly that change. The builder guard at §4.2b step 3 stays, but it is a guard against vendor mistakes, not against someone holding the release key.

**What K_root is used for, and how often.** Signing a keyring (rotating or revoking K_release — rare, and the one recovery from release-key theft); signing a bootstrap zip (once per bootstrap publication, a few times a year); signing a trust update (rotating K_root itself or raising a threshold — expected zero to once in the product's life). Nothing else. This is a workload a solo vendor can run from a safe: K_root comes out, one or two signatures are produced on C1b, it goes back.

### 1.3 Install sequence (online, fresh module)

`[B]` browser (a `group_system` admin), `[O]` Odoo worker, `[S]` licence server.

1. `[B]` **Check for updates**. `[O]` runs preflight (§2.6); any blocking failure stops here with the operator's command.
2. `[O]` re-decodes and re-verifies **every** `hm.license.key` (`hm_license.py:159-207`). Entitlement = union of `modules` over licences whose signature verifies and whose `expires >= today`, plus `{hm_license, hm_store}`.
3. `[O]→[S]` `POST /api/v1/odoo/catalogue` with the exact signed payload bytes, the signature, `database.uuid` and the installation signature (§3.4). **No `licence` envelope field is sent** — it carried nothing authenticated and was the throttle key, which is why it is gone (§3.3). `[S]` verifies, checks the presented payload against the registered row, registers or upserts the activation, returns `keyring.json` + sig and `release.json` + sig (§3.5). `[O]` reads the response through a hard byte ceiling and never calls `response.json()` (§2.8 step 1).
4. `[O]` verifies, in this order and stopping at the first failure: the response size ceiling → the keyring's signature against the **root pin C13** → `json.loads` → strict schema → **`keyring_serial >= persisted keyring floor`**, and no release key in the persisted revocation set → persist the new keyring floor and the widened revocation set → only now the index against the keyring's release keys → strict schema → the release floor (`serial >= floor`) → freshness (§2.7 step 0). Verified bytes are cached to `<data_dir>/hm_store/releases/<serial>.{json,sig}` and re-verified on every use.
5. `[B]` **Install** on a module. `[O]` computes the plan (§2.7) and shows the wizard: modules to place/install/upgrade, total bytes, **the databases whose users a restart disconnects — enumerated from `pg_database`, with an explicit `unknown — could not check` row for any the Store cannot read (§2.7 step 7)** — the restart method (§2.9 G), and acknowledgements.
6. `[B]` **Download and verify**. Per module: stream to `ops/<op>/downloads/<m>.zip` capped at the signed size, hashing as it arrives → compare hash and size → **only then** open the zip → strict unpack into `ops/<op>/staging/<m>/` (§2.10). Operation becomes `verified`. **Nothing on the import path has changed.**
7. `[B]` **Apply and restart** (`@check_identity`). `[O]` runs §2.9: lock → re-hash staging → commit `applying` + write `ROLLBACK.txt` → swap → clear caches → `update_list` + `button_install` → set the flag, `applied_at`, `boot_seq_at_apply` and `tree_id_at_apply` → commit → postcommit runs the restart **method the operator chose** (§2.9 G: `graceful` 3 s later, `hard` as a detached command, or `operator`, which restarts nothing and shows the command).
8. The response is sent; the chosen restart method (§2.9 G) runs. Whichever it is, *something* loads a fresh registry: `Registry.new` sees `base.partially_updated_database`, deletes it in its own committed transaction and loads with `update_module=True` (brief: `orm/registry.py:160-176`). STEP 2 runs `update_list` against the new manifests (brief: `modules/loading.py:423-427`) and the marked modules install, writing `latest_version` (brief: `loading.py:269`). **Where that load happens is not the same in every shape:** with `-d <db>` it is `preload_registries` in the new master, before it serves anything; without `-d` it is the first request that resolves this database, inside an HTTP worker and under `limit_time_real` (`http.py:2849-2852` → `2274-2277` → `orm/registry.py:99-106`, container r3). §2.6 check 12 warns about the second shape in *every* worker mode, and §2.9 H tells the operator which one they are in.
   At the end of that load, `hm.store.boot._register_hook` stamps the **boot marker** (§2.11) — STEP 9 runs `_register_hook` on every model exactly once per registry load (`modules/loading.py:588-594`, container r3). The marker, not `base.partially_updated_database`, is what reconcile uses to know a restart happened.
9. `[B]` reopens the Store. **Reconcile** (§2.11) marks `done`, writes `state.json` (serial + floor + per-module hashes), deletes `downloads/` and `staging/`, posts to the licence chatter, appends to `audit.log`.

### 1.4 Update sequence

Steps 1–4 identical. Then:

5. **Update all** plans every installed store module whose `archive_sha256` differs from `state.json`, plus any store-catalogue module currently loaded from another addons path (a takeover, which needs an explicit acknowledgement). v1 has no per-module update to a different serial: the data dir always holds exactly one release serial, because those modules were tested together. **Exception, new in revision 2: hm_store updates itself alone.** If `hm_store` or `hm_license` is in the place set `P`, the plan contains only `{hm_store, hm_license}` and nothing else (§2.7 step 6a). The store restarts, the *new* hm_store code runs the reconcile and any authorised root-pin rewrite, and the catalogue modules go in a second operation. Mixing the installer's own replacement with the modules it is installing makes the crash windows in §2.9 unanalysable, and it is the one update where a refusal (§2.10 rule 7) must be able to leave everything else untouched.
6. Same download/verify. **Then a `pg_dump` backup** (§2.8 step 4) before anything is swapped.
7. Same apply, but `button_upgrade`, which calls `update_list()` itself, marks installed dependents `to upgrade`, and `button_install`s any dependency the new manifest adds (brief: `ir_module.py:704-752`).
8. Same restart. New Python is imported only in processes that **start after** the swap (brief: T2-A/B); `load_openerp_module` returns early for anything already in `sys.modules` and core has no `importlib.reload` (brief: `module.py:502`), so a process cannot pick up new code any other way. The database and the new code therefore change together — but in prefork, **old** processes are still serving old code beside them for the length of the graceful reload (invariant 3). Which of the three methods in §2.9 G was used decides whether that overlap exists at all, and §2.9 I is what keeps an old worker from acting on the new database.
9. Reconcile. For an upgrade, success means `state = installed` **and** `latest_version == index version` — which is why every content change must bump the manifest version (§4.4).

### 1.5 First-time setup (operator, once per server)

**Step 1 is the base of the entire trust chain. It is the only step a machine cannot do for the operator, and the runbook, the sales process and S10's acceptance all exist to make it unavoidable.**

1. **Verify the bootstrap against the K_root fingerprint you already have.** Download three files from the bootstrap host (C14): `hm_store-bootstrap-r<N>.zip`, `hm_store-bootstrap-r<N>.zip.rootsig`, and `verify_bootstrap.py` (stdlib + `cryptography` only, ~60 lines, printed in `docs/STORE-INSTALL.md` in full so it can be retyped). Run:

   ```
   python3 verify_bootstrap.py hm_store-bootstrap-r<N>.zip \
       --fingerprint 4F2A-9C11-...-<the 8 groups from your contract>
   ```

   The script derives the K_root public key from the `.rootsig` bundle, refuses unless `sha256(raw 32-byte public key)` matches the fingerprint **you typed**, then verifies the Ed25519 signature over `b"hushmand-bootstrap-v1\n" + zip bytes`. It prints `OK: signed by root-2026 (4F2A-9C11-…)` or a single-line refusal. It never trusts the key that came with the download; the fingerprint in your hand decides.

   **Where the fingerprint comes from — never from the download page.** It is printed in the signed sales contract, on the signed quote/invoice PDF, on a printed quick-start card sent with the invoice, and read aloud digit-group by digit-group on the onboarding call. Two of those four are on paper and none of them is the vendor's web host or the vendor's mailbox. If the operator has only the email, the correct action is to **phone Hushmand and read the fingerprint back** before unzipping anything. §9 S10's acceptance requires the runbook to fail closed here: an operator who cannot produce a fingerprint from a non-download channel is told to stop.

   An OpenSSL 3.0+ alternative (`openssl pkeyutl -verify -rawin -pubin -inkey root.pub.pem -sigfile …`) is documented for hosts without `cryptography`; whether OpenSSL 3.0+ is on both bootstrap targets is **UNVERIFIED** and is settled in S10, with `verify_bootstrap.py` as the documented path either way. `cryptography` 41.0.7 is present in the `odoo:19` image (container r2), so the Docker target is covered.

2. Run **one** command, **before placing any files** (§2.6 gives the exact text with resolved paths):
   `docker exec -u odoo <container> chmod 700 /var/lib/odoo/addons/19.0` — or `sudo -u odoo chmod 700 <addons_data_dir>` for the Debian package.

   *Revision 1 had this step after the unzip, which cannot work:* Odoo creates the directory `0500` and mode `0500` denies the owning uid the write, so the unzip fails with `EACCES` (container r2: as `uid=100(odoo)` against a `0500` directory, `os.access(W_OK)` is `False` and `open(..., "w")` raises `PermissionError` errno 13). The operators who hit that reach for `sudo unzip`, which leaves a root-owned tree the odoo user can never swap (breaking invariant 5), or `chmod 777`, which widens exactly the blast radius T23 exists to contain. Preflight check 17 fails on the first outcome.

3. As the **odoo user** — never with `sudo`, never as root — unzip `hm_license/` and `hm_store/` into the addons data dir:
   `docker exec -u odoo <container> sh -c 'cd /var/lib/odoo/addons/19.0 && unzip -q /tmp/hm_store-bootstrap-r<N>.zip'`
4. Add `hm_store_database = <dbname>` under `[options]` in `odoo.conf`. Unknown keys are stored as-is with one startup WARNING and are readable through `config.get()` because `options` is a ChainMap including `_file_options` (brief: `tools/config.py:164-168, 901-917`).
5. Restart Odoo once. Apps → Update Apps List → install **Hushmand Store**.
6. Settings → Licences → paste the key. Settings → Hushmand Store → **Status**. The Status page prints the **root pin fingerprint** it just wrote to C13; compare it once more against the contract. From here on hm_store refuses to run if the pin and the running `lib/trust.py` disagree (preflight check 18).
7. **Test restart** → Modules → Install.

On step 6 the preflight writes C13 (`<data_dir>/hm_store/trust/root.json`, mode `0400`) from the `ROOT_KEYS` compiled into the running `lib/trust.py`, **once**, if and only if the file does not exist. That write is trust-on-first-use, and step 1 is what makes it safe: the tree it reads from was signed by K_root and checked against an out-of-band fingerprint. There is exactly one other writer of C13 in the whole codebase — the K_root-authorised trust update of §2.10 rule 7 — and `tests/test_root_pin_immutable.py` greps `lib/`, `models/` and `wizard/` (hm_store has no `controllers/` package since revision 3) and fails on any third write path.

---

## 2. The hm_store module — `hushmand-odoo/addons/hm_store/`

### 2.1 File layout

```
addons/hm_store/
  __init__.py  __manifest__.py  README.md
  data/neutralize.sql
  data/ir_cron_data.xml                     # one cron: check + notify only; user_id = base.user_root (§2.14 item 6)
  lib/__init__.py
  lib/trust.py        ROOT_KEYS, ROOT_THRESHOLD, MIN_KEYRING_SERIAL, DOMAIN_* prefixes, DEFAULT_STORE_URL,
                      NAME_RE, PATH_RE, caps (incl. CATALOGUE_MAX), FRESH_WARN_DAYS, FRESH_STALE_DAYS
  lib/rootpin.py      read/seed/compare C13; the K_root trust-update check; the ONLY writer of root.json
  lib/verify.py       verify_keyring(), verify_release(), verify_trust_update(), keyring-floor and
                      revocation-union checks, strict schema; no odoo import
  lib/unpack.py       stage_module(zip_path, entry, staging_root), check_hm_store_trust(staged_dir, pin)
  lib/plan.py         compute_plan(index, entitled, installed, locations, state, floor) -> Plan
  lib/fsops.py        paths, same-device check, flock, swap/unswap, atomic state.json, ROLLBACK.txt, audit.log
  lib/client.py       requests calls, bounded response reader, error-code mapping, no redirects, no verify switch
  lib/instkey.py      installation keypair: generate, load, sign a request (§3.4)
  lib/rescue.py       CLI: status | rollback --op <id> | reset-states   (stdlib only, no odoo import)
  lib/test_verify.py lib/test_unpack.py lib/test_plan.py lib/test_rescue.py
  lib/test_rootpin.py lib/test_client.py                                    # tier0 unittest, ephemeral keys
  models/__init__.py
  models/hm_store_preflight.py              # AbstractModel hm.store.preflight
  models/hm_store_module.py                 # hm.store.module
  models/hm_store_operation.py              # hm.store.operation (+ .line), hm_store_progress()
  models/hm_store_boot.py                   # hm.store.boot: _register_hook stamps the boot marker (§2.11)
  models/hm_license.py                      # _inherit hm.license: store-facing verified helpers only
  wizard/hm_store_apply_wizard.py  wizard/hm_store_offline_wizard.py  wizard/hm_store_status.py
  wizard/hm_store_dashboard.py              # hm.store.dashboard: the Modules screen and its object buttons
  security/ir.model.access.csv
  views/hm_store_views.xml  views/hm_store_wizard_views.xml  views/hm_store_menus.xml
  static/src/js/store_progress.js  static/src/js/store_progress.xml   # @web/@odoo imports only
  static/description/icon.png  banner.png  index.html
  i18n/hm_store.pot
  tests/__init__.py tests/test_access.py tests/test_preflight.py tests/test_guard.py tests/test_no_chmod.py
  tests/test_menus.py                         # clicks every menu entry and every button end to end (§2.4 step 3)
  tests/test_root_pin_immutable.py            # exactly one writer of C13; exactly one writer of the keyring floor
  tools/verify_bootstrap.py                   # shipped in the bootstrap zip and printed in STORE-INSTALL.md
tools/store_e2e.py                           # outside the module: real install/update/restart against a fake server
```

`lib/` is pure Python: an AST test in `lib/test_verify.py` asserts no module under `lib/` imports `odoo`. That single property lets the same verifier run in tier0 CI, in `tools/store_e2e.py`, in `lib/rescue.py` on a broken server, and on a transfer machine.

### 2.2 Manifest, relation to hm_license, gating, CI obligations

```python
{
  "name": "Hushmand Store", "version": "19.0.1.0.0", "license": "OPL-1",
  "depends": ["hm_license"],
  "external_dependencies": {"python": ["cryptography", "requests"]},
  "data": ["security/ir.model.access.csv", "views/hm_store_views.xml",
           "views/hm_store_wizard_views.xml", "views/hm_store_menus.xml",
           "data/ir_cron_data.xml"],
  "assets": {"web.assets_backend": ["hm_store/static/src/js/store_progress.js",
                                    "hm_store/static/src/js/store_progress.xml"]},
  "application": False, "auto_install": False, "installable": True,
}
```

The container ships `cryptography` 41.0.7 and `requests` 2.31.0 (brief).

**It depends on hm_license**, for three reasons, and the dependency is not optional:
- it reuses `_decode` and `_verify_signature` rather than carrying a second copy of the verifier;
- `addons/hm_license/tests/test_gate.py:244-261` asserts every directory under `addons/` except hm_license lists `hm_license` in `depends` — it iterates `p.is_dir()`, not just folders with a manifest;
- `tools/tests/test_packaging.py:38-47` requires `hm_license` in every module's closure.

**It is UNGATED.** Add to `tools/build_release.py` `UNGATED` (repo: the dict at lines 53-58): `"hm_store": "is the installer; it verifies entitlement itself on every operation, and gating it would lock a lapsed customer out of licence recovery"`. If it inherited `hm.license.gate`, its own records would be refused, because no licence lists `hm_store`.

**Always entitled.** `hm_store` and `hm_license` are downloadable and installable for any valid, unrevoked licence, on both client and server. Security fixes to the installer are never paywalled.

**Always entitled means hm_store updates itself, which is a security problem in its own right and is handled in two places, not here.** Because `lib/trust.py` is an ordinary file inside this archive, a release signed with a stolen K_release would otherwise be able to replace the root of trust — see invariant 11. The controls are the root pin C13 (outside this tree) and §2.10 rule 7 (refuses the swap unless the trust constants are unchanged or a K_root `trust_update` authorises the change), plus §2.7 step 6a, which makes the installer update alone. Nothing in this section may be read as permitting an hm_store update that changes the pin.

**Repo changes needed for CI to go green** (all in `hushmand-odoo`):

| File | Change |
|---|---|
| `tools/build_release.py` | `UNGATED["hm_store"]`; `root=` parameter on `all_modules`/`read_manifest`/`files_for`/`write_archive`; deterministic-zip writer |
| `tools/pricing.py` | `MODULES["hm_store"] = None` (free; `quote.py --check` and `test_packaging.py:222-227` need the entry) |
| `tools/listings/hm_store.py` | new `LISTING` dict with `eyebrow`, `title`, `lede`, `footer`; then regenerate `addons/hm_store/static/description/index.html` with `build_listing.py` (it is compared byte for byte) |
| `tools/generate_icons.py` | `ICONS["hm_store"]` entry, then generate `icon.png` and `banner.png` — the tool returns 1 if any `addons/` dir lacks an entry |
| `addons/hm_store/README.md` | required by `ci.yml:76-90` for every directory in `addons/` |
| `.github/workflows/ci.yml` | add `hm_store` to the odoo job `-i`/`--test-tags` (177-178), the `.pot` export list (211-216); commit `i18n/hm_store.pot`; add a tier0 step `python -m unittest discover -s addons/hm_store/lib -p "test_*.py"`; add the `store-e2e` job (§9 S1, S6) |
| everywhere in hm_store | the literal string `AGPL` must never appear — `ci.yml:139-142` greps all of `addons/` case-sensitively |

No demo data, so the demo job's "every manifest's `demo` entries were loaded" check (315-328) is unaffected. `hm_store` is added to the odoo job's `-i` list, which also keeps the Dari export step (which loops over **every** `addons/*/`) from hitting `"No valid module has been provided"` (brief: `odoo/cli/i18n.py:198-209`).

### 2.3 Models

**`hm.store.module`** — cached catalogue, one row per module in the current verified index, written only through `sudo`.

| field | type | note |
|---|---|---|
| `name` | Char, unique | technical name |
| `display_title`, `summary` | Char | from the signed index; rendered only through escaped widgets |
| `release_serial`, `available_version` | Integer, Char | |
| `licensed` | Boolean | recomputed from re-verified keys, never stored payload fields |
| `installed_version` | Char, compute | `ir.module.module.latest_version` |
| `location` | Selection `data_dir`/`other_path`/`core`/`absent` | resolved with `os.path.isdir` over `odoo.addons.__path__`. **Never through the Manifest API**, which would poison its `lru_cache` (brief: `modules/module.py:279`, T1) |
| `store_state` | Selection `not_licensed`/`available`/`installed`/`update_available`/`takeover_needed`/`blocked` | |
| `blocked_reason` | Char | local translated text only |

**`hm.store.operation`** — the audit record and the state machine. No group has create/write/unlink; code writes through `sudo().with_context(hm_store_internal=True)`, which is the **only** way `write()` succeeds (§2.12). `sudo()` alone is not enough and never was: it sets `env.su`, which `check_access` reads (`orm/environments.py:178-190`), and does not bypass the model's own `write`.

`name` (`HMS-2026-0007`, `ir.sequence`), `user_id`, `login` (snapshot), `remote_addr`, `database_uuid`, `licence_ids` (Char, comma-separated `licence_id`s used), `source` (`online`/`offline`), `from_serial`, `to_serial`, **`keyring_serial` (Integer)**, **`root_pin_sha256` (Char, the pin in force when the operation ran)**, `state` (`draft`, `verified`, `backing_up`, `applying`, `awaiting_restart`, `done`, `failed`, `stalled`), `error_code`, `error_detail` (Text), `rollback_text` (Text), `backup_path`, `backup_sha256`, **`backup_pruned_at` (Datetime)**, `line_ids`, `verified_at`, `applied_at`, `completed_at`, and three fields new in revision 3: **`restart_method`** (Selection `graceful`/`hard`/`operator`, §2.9 G), **`boot_seq_at_apply`** (Integer, the boot counter read inside the applying transaction, §2.11), **`tree_id_at_apply`** (Char, the hm_store build id in force when Apply ran, §2.9 I).

`keyring_serial` is not decoration: it is half of the **database side of the keyring floor** (§2.8a), the mirror of what `to_serial` does for the release floor. **`status_token_hash` is gone** — revision 2's status route was removed in revision 3 (§2.4), and with it the token, the token compare and the clear-on-terminal rule.

`hm_store_progress(self)` — the single authenticated call the progress page makes (§2.4). It returns `{"state": <operation state>, "phase": <enum>, "boot_seen": <bool>, "elapsed_s": <int>}` computed from the boot marker and the operation row, nothing else: no free text, no traceback, no module names. It calls `_hm_store_guard('mutate')` because it runs reconcile, and it is deliberately the *only* method the page is allowed to call in a loop-shaped way — and it is called exactly once per apply.

**`hm.store.operation.line`**: `module`, `action` (`install`/`upgrade`/`takeover`), `from_version`, `to_version`, `archive_sha256`, `tree_sha256`, `result` (`pending`/`ok`/`failed`).

**`hm.store.apply.wizard`** (Transient): `mode`, `requested_module`, `plan_text` (Text, computed), `databases_affected` (Text), `backup_state` (Selection), `backup_path`, `ack_restart`, `ack_backup`, `ack_takeover`, `operation_id`; buttons `action_download_verify`, `action_backup`, `action_apply` (`@check_identity`).

**`hm.store.offline.wizard`** (Transient): `bundle` (Binary, `attachment=False`), `bundle_name`, `operation_id`.

**`hm.store.status`** (Transient): one Text per check plus `ok`, plus (new in revision 3) `euid`, `process_user`, `worker_mode` and `restart_method_available`, so the Status page states on its face which uid Odoo runs as (§2.6 check 5) and which restart methods §2.9 G can offer.

**`hm.store.dashboard`** (Transient, new in revision 3): the Modules screen. `module_ids` (one2many onto `hm.store.module`), `banner_text`, `freshness_state`; buttons `action_check_updates`, `action_update_all`, `action_check_status`, `action_open_status`, all `type="object"`. Its `default_get` runs the read-only reconcile. It exists because §2.4 step 3 refuses `/web/action/run`, and revision 2's `ir.actions.server` menu entries all dispatched there.

**`hm.store.boot`** (AbstractModel, new in revision 3): `_register_hook()` stamps the boot marker — `hm_store.boot_seq` (monotonic integer) and `hm_store.boot_at` (UTC ISO) in `ir.config_parameter`, plus the current hm_store build id — and, from S9 onward, runs the post-boot reconcile of §2.11. STEP 9 of `load_modules` calls `_register_hook` on every model **exactly once per registry load** (`modules/loading.py:588-594`, container r3), which is precisely the event reconcile needs to witness. That the write is *committed* in every boot shape is an assumption, not a fact: settled by **S1(9)**.

**`hm.store.preflight`** (AbstractModel): `run(blocking_only=False) -> list[Check]`.

**`hm.license` extension** (`models/hm_license.py`, `_inherit`): `_store_verified_payloads()` returns `[{payload, payload_bytes}]` for licences whose signature verifies and whose `expires >= today`; `_store_entitlements()` returns the module set. Both decode from `key` every time.

### 2.4 Security groups and the guard

**ACL** `security/ir.model.access.csv`: `base.group_system` read-only on `hm.store.module`, `hm.store.operation`, `hm.store.operation.line`; read/write/create on the four transient models (`hm.store.apply.wizard`, `hm.store.offline.wizard`, `hm.store.status`, `hm.store.dashboard`). `hm.store.boot` is an AbstractModel and has no ACL row. No other group, no `ir.rule`, **no new group** — any `group_system` user can grant a custom group, so it would add no barrier.

**Menus** all carry `groups="base.group_system"`.

`_hm_store_guard(kind)` runs first in every method that changes anything. **`kind` is one of three values and is written at every call site**, because revision 2's single path test refused the spec's own menu entries (see the box below):

| `kind` | What it may do | Who may call it |
|---|---|---|
| `apply` | swap files, mark `ir.module.module`, set the flag, restart | an interactive admin over an object button, with `@check_identity` |
| `mutate` | write `hm.store.*` rows, reach the network, write `state.json`, seed/prune the work dir | an interactive admin |
| `cron` | the same as `mutate`, **minus** everything that touches the import path, `ir.module.module`, `base.partially_updated_database` or `server.restart()` | the daily check cron, with no request at all |

1. `if self.env.su and kind != 'cron': raise AccessError` — an interactive call must be a real user, so Odoo's own `assert_log_admin_access` applies and logs (`ir_module.py:57-73`, container r3). The cron runs as a named user (§2.14 item 6), not as an anonymous superuser, and it never calls a method decorated with `assert_log_admin_access`.
2. For `apply` and `mutate`: `self.env.is_system() and self.env.is_admin()` (brief: `orm/environments.py:182-190`; `group_system` implies `group_erp_manager` per `base/security/base_groups.xml`). Both are checked because stock Odoo lets `group_erp_manager` install modules and that is not good enough here. For `cron`: `self.env.user == env.ref('base.user_root')` and `self.env.context.get('hm_store_cron')` is true.
3. **Call-path allowlist, corrected in revision 3.** For `apply` and `mutate`, `request` must exist and `request.httprequest.path`, after stripping a trailing `/<path:path>` segment, must be **exactly one of**:

   | Allowed path | Why it is on the list |
   |---|---|
   | `/web/dataset/call_button` | every `type="object"` button (`web/controllers/dataset.py:34`, container r3). This is the only path `apply` accepts. |
   | `/web/dataset/call_kw` | `default_get` / `web_read` on the transient models, which is how the Modules screen runs its read-only reconcile (`dataset.py:28`). `mutate` only. |

   `/web/action/run` is **not** on the list, and no mutating entry point is an `ir.actions.server` any more — see the box. For `cron`, step 3 is skipped and replaced by `if request: raise AccessError`: a cron door must never be reachable from a browser.

   > **Why revision 2's rule was wrong.** It required the path to *start with* `/web/dataset/call_button`, while §2.5 built "Check for updates", "Update all", "Status" and the reconcile-on-open as `ir.actions.server`. Server actions dispatch over `@route('/web/action/run', type='jsonrpc', auth="user")` → `request.env['ir.actions.server'].browse([action_id]).run()` (`web/controllers/action.py:53-59`, container r3), never over `call_button`; the only `call_button` route in core is `web/controllers/dataset.py:34`, reached solely by `<button type="object">`. Every one of those four entry points would have raised `AccessError` the first time a customer clicked it. The fix is **both** halves: a real allowlist *and* §2.5's conversion of every mutating entry point to an object button, so the strictest path (`call_button`) is the one the dangerous action actually uses. `tests/test_guard.py` asserts the allowlist is a closed set and S4's acceptance clicks **every menu entry and every button end to end**, because a path allowlist turns a working button into an `AccessError` silently.

4. `config.get("hm_store_database") == self.env.cr.dbname`.
5. `ir.config_parameter` `hm_store.neutralized` is not set.
6. For `apply` and `mutate`: the **stale-worker check** of §2.9 I. A process whose in-memory hm_store tree is no longer the tree on disk refuses before it does anything else.

`action_apply`, `action_backup`, `action_restart_resume` and the offline import additionally carry `@check_identity`, which raises `UserError` when there is no request and otherwise returns an `res.users.identitycheck` action *instead of calling the method* when the last check is older than 10 minutes (`res_users.py:87-127`, container r3). The replay runs from `res.users.identitycheck.run_check()` (`res_users.py:1430-1439`), which is itself a `type="object"` button — so the replayed `action_apply` arrives over `/web/dataset/call_button` and satisfies step 3. **`/jsonrpc` and `/xmlrpc` cannot reach these methods at all:** `dispatch_rpc` runs inside `with borrow_request():`, which *pops* the request off the stack (`http.py:444`, `1460-1466`, container r3), so both `check_identity` and guard step 3 see no request. That item leaves Appendix B.

**HTTP surface: hm_store adds no route at all.** Revisions 1 and 2 specified one, `controllers/status.py`, an `auth='none'` GET polled every 3 s with `X-Odoo-Database` and no cookie, whose whole purpose was to let the progress page watch a restart from outside a session. **Revision 3 deletes it.** It could not do that job, and trying made things worse:

- **A no-db route is impossible for a runtime-installed module.** `nodb_routing_map` is built from `[''] + config['server_wide_modules']` with `nodb_only=True` (`http.py:2758-2768`, container r3). hm_store is not server-wide and cannot be (`server_wide_modules` is startup-only, §8), so when a request resolves no database the route is simply not in the map and `_serve_nodb` answers with the fixed `NOT_FOUND_NODB` body (`http.py:2246-2253`).
- **A db-bound poll is the thing that causes the load it was meant to observe.** `if request.db: response = request._serve_db()` (`http.py:2849-2852`) → `registry = Registry(self.db)` (`http.py:2274-2277`) → `Registry.__new__` takes the **class-level** `_lock` and calls `Registry.new`, itself `@locked` (`orm/registry.py:92`, `99-106`, `115-117`). So in prefork without `-d` the *first status poll* runs the entire module upgrade inside a GET, under `limit_time_real`; and in threaded mode every other request thread — including the next poll — blocks on that class lock for the whole upgrade.
- **The 3-second cadence made a self-inflicted restart more likely, not less.** `process_limit` compares `time.time() - thread.start_time` against `limit_time_real` for every non-daemon HTTP thread *and* for cron threads, in **every** worker mode (`service/server.py:503-524`); once `limit_reached_time` is set the main loop calls `self.reload()` (`server.py:732-751`), which is `os.kill(self.pid, signal.SIGHUP)` (`server.py:764-765`). Queued polls accumulate runtime while they wait on the registry lock, so a fast poll is a way to SIGHUP the server *in the middle of its own upgrade*.

**What replaces it.** Progress is observed in two stages, neither of which is a new route:

1. **Liveness, unauthenticated and registry-free.** `store_progress.js` issues a conditional `GET /web/static/img/favicon.ico` with `credentials: 'omit'`. `Application.__call__` checks `self.get_static_file(httprequest.path)` **before** it looks at `request.db` (`http.py:2852-2854`), and `_serve_static` only opens a file (`http.py:2219-2238`) — no registry, no cursor, no lock. Cadence: 2 s for the first 30 s, then exponential backoff to 15 s, **one request in flight at a time**, and the whole probe stops after 15 minutes and hands over to the manual text. This answers "is an HTTP listener up", nothing more, and the UI says exactly that. In **threaded** mode the listener genuinely goes away during a reload (`ThreadedServer.stop` calls `self.httpd.shutdown()`, `server.py:657-670`), so the dip is real; in **prefork** it does not, because the listening socket is passed to the new master through `ODOO_HTTP_SOCKET_FD` and stays open across `_reexec()` (`server.py:1087-1089`, `1107-1113`) — so in prefork liveness never dips and the client must not treat a steady 200 as "nothing happened".
2. **One settled call, authenticated, long timeout, no repeat.** After liveness has been continuously good for 5 s, the client makes **exactly one** ordinary `call_kw` to `hm.store.operation.hm_store_progress([op_id])` with a 20-minute client timeout and no retry-on-timeout. That request is a normal authenticated JSON-RPC call over the user's own session; it is *allowed* to be the request that loads the registry and runs the upgrade, because that is unavoidable in any shape that does not set `-d` (§2.9 H says which shape the operator is in). If it returns, the page has the real phase from the boot marker and the operation row. If it errors, the client shows "Odoo is restarting — this can take several minutes" and offers a manual **Check status** button; it never starts a second one by itself.

**Consequences elsewhere, all of them simplifications:** `status_token_hash` and the whole token scheme are gone from §2.3, §2.9 F and §2.11; `controllers/` disappears from §2.1; preflight check 16 stays, because Odoo's "any request can name any database" behaviour is not about hm_store and is worth warning about regardless; and §5 T29's "only `auth='none'` surface" row becomes "hm_store adds no unauthenticated surface", which is strictly stronger than what revision 2 argued for. The three byte-identical-404 requirements in S1(6) and S4 are replaced by the probe in S1(6) below.

No `type='http'` route, no `auth='none'`, no `csrf=False`, no `cors=`. Every action is a JSON-RPC button, and JSON-RPC accepts only `application/json` bodies (brief: `http.py:2544-2554`), which a cross-site form cannot send. The offline upload is a Binary field on a wizard, not an upload route.

### 2.5 Views and menus

**Rule, new in revision 3 and load-bearing for §2.4 step 3: every entry point that changes anything is a `type="object"` button on a model.** `ir.actions.server` is used **only** for pure navigation — an action whose entire body is a returned `ir.actions.act_window` dict and which calls no hm_store method. The reason is mechanical: server actions dispatch over `/web/action/run` (`web/controllers/action.py:53-59`), which the guard's allowlist does not contain, and `check_identity`'s own docstring says the wrapped method is "called from a button type=object" (`res_users.py:88-89`, container r3).

- `menu_hm_store` "Hushmand Store", parent `base.menu_administration` (the top-level Settings menu in 19, brief: `base/views/base_menus.xml:5-9`), sequence 97, next to Licences (96).
  - **Modules** — an `ir.actions.act_window` on the transient **`hm.store.dashboard`**, form view, whose `default_get` runs the read-only half of reconcile (`_hm_store_guard('mutate')`, reached over `/web/dataset/call_kw`) and then embeds the `hm.store.module` list as a one2many: title, name, licensed, available/installed version, state; row button **Install** when `store_state == 'available'`, **Update** when `update_available`. Both row buttons are `type="object"`.
    The dashboard form's header carries **Check for updates**, **Update all** and **Check status** as `type="object"` buttons on `hm.store.dashboard`. Revision 2 reached for `ir.actions.server` here because list-header `display="always"` buttons in 19 were UNVERIFIED — and that workaround is what broke the guard. A form header needs no such attribute, so revision 3 does not settle the `display="always"` question; it **stops depending on the answer**, which is the better outcome for an item nobody had read the source for.
  - **Operations** — list/form of `hm.store.operation`, with **Check status** (reconcile), **Restart now** / **Resume** (visible in `awaiting_restart` / `stalled`), and `rollback_text` in a monospace readonly field. All `type="object"`; **Restart now** and **Resume** carry `@check_identity`.
  - **Status** — `ir.actions.act_window` on `hm.store.status` (transient, `target="new"`); the checklist is computed in `default_get`, each failing row with a copy-paste command. Pure navigation, so this one may be — and is — a plain act_window with no server action at all.
  - **Offline install** — the offline wizard, `target="new"`.
- Client action `hm_store.progress` (`static/src/js/store_progress.js`): after Apply it runs the two-stage observation of §2.4 — a `credentials: 'omit'` conditional GET on `/web/static/img/favicon.ico` with 2 s → 15 s backoff and one request in flight, then **exactly one** `hm.store.operation.hm_store_progress` call with a 20-minute timeout and no automatic retry. It shows elapsed time and, in prefork, the sentence "your users are still being served by the previous version until the upgrade finishes" (invariant 3). After 10 minutes it shows the recovery text and the path of `ROLLBACK.txt`. On `done` it offers **Reload Odoo**; on any error it offers **Check status**, which is a button the operator presses, never a timer.
- **No `fields.Html`, no `t-out`, no `Markup` anywhere in hm_store.** `tests/test_access.py` scans the view arch of store models for `t-out` and `widget="html"` and fails on a hit.

### 2.6 Preflight: finding the writable dir, and what the admin is told

`hm.store.preflight.run()` runs on every Store screen load and again immediately before Download and before Apply. Blocking checks stop both.

| # | Check | How | Blocking |
|---|---|---|---|
| 1 | Opt-in | `config.get("hm_store_database") == cr.dbname` | yes |
| 2 | Platform | `os.name == "posix"` | yes |
| 3 | Dev reload | `'reload' in (config['dev_mode'] or [])` (brief: `service/server.py:1657`) | yes — the watcher restarts the server as files are written |
| 4 | Data dir on path | `d = config.addons_data_dir`; `realpath(d)` in `[realpath(p) for p in odoo.addons.__path__]` (brief: `module.py:141-171`) | yes |
| 5 | **Data dir writable — mode bits, not `os.access`** | **(a)** `os.geteuid() != 0`, else **fail** with the "run Odoo as a non-root user" message below; **(b)** `st = os.stat(d)`; `st.st_uid == os.geteuid()`; **(c)** `stat.S_IMODE(st.st_mode) & 0o200` is set; **(d)** `os.access(d, os.W_OK)` as a last sanity check only. Report `oct(stat.S_IMODE(st.st_mode))`, `st.st_uid` and `os.geteuid()` in the message and on the Status page | yes — text below |
| 6 | Work dir, same filesystem, **modes re-asserted** | `w = <data_dir>/hm_store`, `mkdir 0700`; `os.stat(w).st_dev == os.stat(d).st_dev`; **and on every run** re-assert `0700` on `w`, `w/backups`, `w/trust` and `w/ops`, and `0400` on `w/trust/root.json`, `chmod`ping them back if they have drifted, logging a WARNING when they had. Revision 1 asserted `0700` only at creation and never again | yes |
| 7 | Nothing pending | no `ir.module.module` in `to install`/`to upgrade`/`to remove`; no `hm.store.operation` in `applying`/`awaiting_restart`; `base.partially_updated_database` unset | yes |
| 8 | No imported modules | if `ir.module.module.imported` exists (brief: `base_import_module/models/ir_module.py:39-52`): no `imported=True` row matching `^(hm\|af)_` — such modules are silently dropped from the graph | yes |
| 9 | Licence | at least one licence verifies and is unexpired | yes |
| 10 | Free disk | `shutil.disk_usage(w).free >= 3 × planned bytes` (+ backup estimate for updates) | yes |
| 11 | **Test restart** | `hm.store.installation`-equivalent fields on the operation model: `restart_test_requested_at` < `last_boot_at` | **yes, for the update path**; warning for a fresh install |
| 12 | **Time limit, in every worker mode** | `not config['db_name'] and config['limit_time_real'] and config['limit_time_real'] < 300` (default 120, brief: `tools/config.py:488`). **The `workers > 0` condition of revision 2 is removed**: `process_limit` applies `limit_time_real` to every non-daemon HTTP thread and to cron threads whatever `workers` is (`service/server.py:503-524`, container r3), and the *threaded* consequence is worse — `run()` calls `self.reload()` (`server.py:732-751`), i.e. `os.kill(self.pid, SIGHUP)` (`server.py:764-765`), re-execing the **whole server** mid-upgrade instead of killing one worker. The message says which of the two it is | warning — text below |
| 13 | Not neutralized | `hm_store.neutralized` unset | yes |
| 14 | Libraries | `cryptography` Ed25519 and `requests` import | yes |
| 15 | Backup tool | `odoo.tools.misc.find_pg_tool('pg_dump')` (brief: used by `service/db.py:282-288`) | warning — falls back to the acknowledgement checkbox |
| 16 | **Database exposure** | `config['db_name'] or config['dbfilter']` is set | warning — text below; without it any unauthenticated request can name an arbitrary database and make Odoo attempt a registry open (container r2: `http.py:402-425`, `2849-2871`) |
| 17 | **Ownership** | `os.stat(d).st_uid == os.geteuid()`, and the same for every `hm_*`/`af_*` child of `d` and for `w` and its children | yes — a root-owned tree (the `sudo unzip` outcome) can never be swapped, which would fail *after* the flag is committed (invariant 5). Message gives `chown -R odoo:odoo <path>` and the reason |
| 18 | **Root pin** | `<data_dir>/hm_store/trust/root.json` exists, is mode `0400`, is owned by the Odoo uid, parses, and its `root_keys`/`root_threshold`/`domain_prefixes` are **equal** to the running `lib/trust.py`. Absent → seed it once from `lib/trust.py` and show the fingerprint. Present and different → **refuse every operation** with `root_pin_mismatch` | yes — this is invariant 11's enforcement point |
| 19 | **Restart method** (new, r3) | Determine which of §2.9 G's three methods is available and which is the default: `graceful` always; `hard` only when `hm_store_restart_command` is set in `odoo.conf` and its argv[0] is an absolute path to an executable file; `operator` always. Record `config['workers']`, `config['db_name']` and the chosen default on the operation. **In prefork (`config['workers'] > 0`) the default is `operator`**, because `graceful` overlaps generations (invariant 3) and the spec will not pick an overlap for the operator silently | warning when the operator has not chosen a method for an update; blocking for nothing |
| 20 | **Boot marker works** (new, r3) | `hm_store.boot_seq` exists in `ir.config_parameter` and `hm_store.boot_at` parses. Absent on a freshly installed hm_store is normal and the check seeds nothing: it records "no boot observed yet" and the update path stays blocked by check 11 (Test restart) until one has been | yes, for the update path — reconcile's only restart witness is this marker (§2.11), and a marker that never appears would make every operation look `stalled` |

**Check 5 message, shown in full, with the real path and mode substituted:**

> The Odoo add-ons data folder **`/var/lib/odoo/addons/19.0`** is read-only (mode **0500**). Odoo creates this folder read-only on purpose. A server administrator must allow add-on installs once, **before placing any files in it** — at mode 0500 even the `odoo` user cannot write there (container r2: `PermissionError` errno 13 as `uid=100(odoo)`):
>
> - **Docker (official `odoo:19` image):** `docker exec -u odoo <odoo-container> chmod 700 /var/lib/odoo/addons/19.0`
> - **Debian/Ubuntu package:** `sudo -u odoo chmod 700 /var/lib/odoo/addons/19.0`
>
> Run the unzip **as the odoo user afterwards**, not with `sudo`: files owned by root in this folder cannot be replaced by later updates.
>
> This folder must be on persistent storage (the Docker `/var/lib/odoo` volume), or installed modules will disappear on the next image rebuild. No restart is needed. Then click **Check again**.

**Check 5(a) message, when Odoo runs as root** — this is why check 5 no longer trusts `os.access`:

> **Odoo is running as `root` (euid 0).** Hushmand Store will not install anything on this server. `os.access(..., W_OK)` is evaluated with the *real* uid and a root process bypasses directory mode bits entirely, so this check would pass against the untouched read-only folder and the one deliberate human step — a server administrator allowing add-on installs once — would be skipped without anyone noticing. That step is the whole opt-in (invariant 6). Run Odoo as a non-root user: add `--user odoo` to `docker run` (or `user: odoo` in compose), or `User=odoo` to the systemd unit, restart, and click **Check again**. The running euid is also shown on the Status page and written to `audit.log` on every operation.

*Why revision 2 was wrong here:* it checked only `os.access(d, os.W_OK)`, which returns `True` for uid 0 whatever the mode says. The container this spec was written against happens to run `uid=100(odoo)` (container r2/r3), so the failure was invisible locally; a `docker run` without `--user`, a hand-rolled compose file or a systemd unit without `User=` all produce it. That root bypasses DAC mode checks follows from POSIX `access(2)` and is **not** re-run in this container — it is listed in Appendix B and settled by **S1(10)**. Check 5(a)'s refusal does not depend on the answer: hm_store refuses to run as root either way, which is the correct posture for a process that writes importable Python.

**Check 12 message**, one of two, depending on `config['workers']`:

> *(prefork, `workers > 0`)* This Odoo starts `N` worker processes and gives each request `limit_time_real = 120` seconds. Because no `db_name` is set in `odoo.conf`, the module upgrade will run **inside the first request that reaches this database after the restart**, and a worker that exceeds the limit is killed in the middle of it. Set `db_name = prod` (so the upgrade runs at startup instead), or raise `limit_time_real` to 600 for the duration of the update.

> *(threaded, `workers = 0`)* This Odoo runs threaded and gives every request `limit_time_real = 120` seconds. Because no `db_name` is set in `odoo.conf`, the module upgrade will run **inside the first request that reaches this database after the restart**. If it exceeds the limit, Odoo does not kill that one request — it **restarts the entire server** while the upgrade is running, which is how a half-upgraded database happens. Set `db_name = prod`, or raise `limit_time_real` to 600 for the duration of the update.

**Check 16 message:**

> This Odoo does not set `db_name` or `dbfilter`, so any request from the internet can name any database and make Odoo try to open it. Add `db_filter = ^prod$` (or `db_name = prod`) under `[options]` in `odoo.conf` and restart. This is not specific to Hushmand Store, but the Store adds one small public page and this setting is what keeps it cheap to serve.

**Check 18 message when the pin and the code disagree:**

> **SECURITY: the Hushmand Store's root key pin does not match the installed code.** The Store will not run. This means either the `hm_store` folder was replaced outside the Store, or an update changed the root key without authorisation. Do not "fix" it by deleting `<data_dir>/hm_store/trust/root.json`. Contact Hushmand, quote operation `<last op>`, and re-install from a bootstrap zip you have verified against your contract fingerprint (§1.5 step 1).

**Check 11, Test restart**, is its own button: it stamps `restart_test_requested_at`, restarts **by the method check 19 chose**, and the boot marker of §2.11 supplies `last_boot_at`. The update path is refused until `last_boot_at > restart_test_requested_at`, because whether `odoo.service.server.restart()` works when Odoo is PID 1 in the `odoo:19` image is **UNVERIFIED** (the probes ran separate server processes) and the wrong time to find out is after the flag is committed. Revision 3 makes the check stronger in one way: it now proves the *whole* chain the update path depends on — restart happens **and** `hm.store.boot._register_hook` writes a committed marker (check 20) — rather than only that the process came back. A Test restart that restarts but leaves no marker is a **failure**, and the message says the update path will stay blocked until it is fixed, because reconcile has no other way to tell a restart from a stall.

`tests/test_no_chmod.py` greps `lib/`, `models/` and `wizard/` for any `chmod` whose target is not textually under the hm_store **work** dir, and for any write to the opt-in, and fails on a hit. Invariant 6 is about the addons data dir C10, which hm_store still never touches; check 6 re-asserting `0700` on hm_store's own C11 work dir and `0400` on C13 is not the same thing, and the test is written so the distinction is enforced rather than trusted.

### 2.7 Entitlement, dependency closure, plan

`lib/plan.py` is a pure function. Inputs: verified index `I` (serial `S`, signed `created_at`), entitled set `E`, installed set `N`, location map `L`, `state.json` `J`, release floor `F = max(J.floor, max to_serial over done operations)`, and `now`.

0. **Freshness** (new in revision 2; the online path had none). Let `age = now - I.created_at` and `gap = now - J.last_successful_catalogue_at`. `age > FRESH_WARN_DAYS` (45) **or** `gap > FRESH_WARN_DAYS` → a yellow banner on the Store screen and a line in the cron notice (D13): "Hushmand has not published a release in N days, and the Store last reached Hushmand M days ago. If that seems wrong, your connection to Hushmand may be intercepted — call Hushmand." `age > FRESH_STALE_DAYS` (180) → the same text in red. **Never a block**: clocks in the field are wrong, and a genuinely quiet quarter is normal. The comparison uses `max(now, J.newest_created_at_seen)` so a clock set backwards cannot suppress the warning, and `J.newest_created_at_seen` only ever rises. This is the same rule §6 step 5 already applied to offline media; revision 1 applied it to the fallback path and not to the default one, so a held store could report "up to date" forever while security fixes never arrived (invariant 1's DoS allowance is about *visible* denial).
1. `S < F` → refuse, `downgrade_refused` ("the store offered an older release than the one installed; possible replay"). `S == J.serial` and nothing requested → up to date **plus the step 0 banner if it applies** — "up to date" is never shown alone when the index is stale.
2. `R` = `{m}` for Install, `∅` for Update all.
3. Closure `C = R ∪ transitive(depends ∩ names(I))`. Core names in `depends` are left to Odoo.
4. `T_install = {m ∈ C : state(m) ≠ installed}`.
5. `P` (files to place) `= T_install ∪ {m ∈ N : J.modules[m].archive_sha256 ≠ I.modules[m].archive.sha256 or L(m) ≠ data_dir}`.
6. `T_upgrade = P ∩ N`.
6a. **The installer updates alone.** If `P ∩ {hm_store, hm_license} ≠ ∅` then `P ← P ∩ {hm_store, hm_license}` and `C`, `T_install`, `T_upgrade` are recomputed from it. The wizard says so: "Hushmand Store must update itself first. This is one restart; your other modules follow in a second step." A second operation is offered as soon as reconcile marks the first `done`. See §1.4 step 5 for why.
7. Blocks:
   - `P \ E ≠ ∅` → `not_licensed`, listing the modules ("uninstall it, or ask Hushmand to reissue your licence to include X").
   - `L(m) == core` (a folder of that name under the Odoo package's `addons`) → `core_name_conflict`.
   - `L(m) == other_path` → needs `ack_takeover`; the message names the path and says the data-dir copy takes priority from now on, because the data dir precedes every `addons_path` entry (brief: probe log order).
   - any `I.modules[m].external_python` not importable (`importlib.util.find_spec`) → `python_dependency_missing`. hm_store never installs pip packages.
   - a non-catalogue `depends` name with no `ir.module.module` row, or state `uninstallable` → `odoo_dependency_unavailable`.
   - **another database on this server uses a module in `T_upgrade`** → `used_by_other_database`. **The enumeration is a direct `pg_database` query, not `list_dbs`** (corrected in revision 3):

     ```sql
     SELECT datname FROM pg_database
     WHERE NOT datistemplate AND datallowconn AND datname NOT IN ('postgres', <db_template>)
     ORDER BY datname
     ```

     run over `odoo.sql_db.db_connect('postgres')`, then for each name a read-only `SELECT name FROM ir_module_module WHERE state IN ('installed','to upgrade') AND name = ANY(%s)` over `odoo.sql_db.db_connect(name)`. Message names the database and gives `odoo -c <conf> -d training -u hm_payroll --stop-after-init`.

     *Why not `list_dbs`.* `odoo.service.db.list_dbs(force=True)` does **not** enumerate every database on the server (`service/db.py:434-453`, container r3). It short-circuits to `sorted(config['db_name'])` whenever `dbfilter` is unset and `db_name` is set — which is the shape §1.5 step 4 and preflight 16 both push operators towards — and otherwise restricts to `datdba = (SELECT usesysid FROM pg_user WHERE usename = current_user)`, i.e. only databases owned by the connecting role. On a server running `prod` with `-d prod`, or one where `training` is owned by a different role, revision 2's rule reported **zero** other databases. `used_by_other_database` and the restart confirmation that "names the databases whose users a restart disconnects" are the T10 blast-radius control, so under-reporting there is the failure mode that control exists to prevent.

     **Three outcomes, not two.** Each enumerated database becomes a row in the wizard: `affected` (connected, `ir_module_module` read, a module matched), `not affected` (connected, read, nothing matched), or **`unknown — could not check`** (could not connect, no `ir_module_module` table, or the read raised) with the reason shown. An `unknown` row is **never** silently treated as `not affected`; if any `unknown` row exists, the restart acknowledgement changes to "This server has N databases the Store could not inspect (listed below). Restarting Odoo disconnects the users of all of them." A `pg_database` read that itself fails turns the whole list into one `unknown` row naming the error, and the acknowledgement says the Store could not enumerate the databases at all. Nothing here is blocking — it is an acknowledgement, and an honest one is the point.
8. Modules installed in Odoo but absent from `I` are left alone with a warning.

### 2.8 Download, verify, backup

Caps in `lib/trust.py`: **catalogue HTTP response body ≤ `CATALOGUE_MAX` = 4 MiB**, **any error response body ≤ 64 KiB**, `keyring.json` ≤ 64 KiB, `release.json` ≤ 2 MiB, archive ≤ 20 MiB, ≤ 5,000 files per module, ≤ 100 MiB uncompressed per module, `.hmpkg` ≤ 64 MiB.

1. **Transport** (`lib/client.py`): `requests.post(url, json=body, timeout=(10,60), stream=True, allow_redirects=False, verify=True, headers={"User-Agent": "hm_store/<ver>", "X-Request-Id": op_uuid, "Accept-Encoding": "identity"})`. There is **no option to disable TLS verification, ever**; on `SSLError` the UI points at the offline bundle. `DEFAULT_STORE_URL = "https://store.hushmand.tech"` is a code constant; the operator-level `odoo.conf` key `hm_store_url` may override it and must be `https://` except for a loopback host in dev. It is never an `ir.config_parameter`, because a `group_system` user could otherwise redirect the licence blob.

   **The response body is bounded before anything parses it** (revision 1 capped the *documents* and left the envelope that carries them unbounded, which let a MITM or a held store exhaust a worker before a single signature was checked — reachable by T4, for whom "integrity comes from signature and hash" is true and says nothing about availability):
   - refuse when `Content-Length` is present and `> CATALOGUE_MAX`, before reading a byte;
   - read with `iter_content(65536)` into a bounded `bytearray`, aborting and closing the connection the moment the accumulated length passes `CATALOGUE_MAX` — this covers a chunked response with no `Content-Length`;
   - the ceiling counts **decompressed** bytes, so a gzip bomb is caught even if a proxy ignores `Accept-Encoding: identity`. Verified (container r2): `requests.Response.iter_content` yields from `self.raw.stream(chunk_size, decode_content=True)` (`/usr/lib/python3/dist-packages/requests/models.py:816`, requests 2.31.0 / urllib3 2.0.7), so the bytes the caller counts are post-decompression;
   - `lib/client.py` **never calls** `response.json()`, `response.text` or `response.content` on a store response — each of those reads the whole body into memory. `lib/test_client.py` greps `lib/client.py` for those three attributes and fails on a hit;
   - only after the bounded read does `json.loads` run, and only on the bytes that were counted.
2. **Keyring then index** (`lib/verify.py`), in this order, before any parse: unknown `key_id` → refuse; `Ed25519PublicKey.from_public_bytes(pinned).verify(b64decode(sig), PREFIX + body)` where `pinned` comes from the **root pin C13**, not from `lib/trust.py` directly (preflight 18 has already proved they agree); only then `json.loads`; then the strict schema — `schema == 1`, `product == "hushmand-odoo"`, `series == "19.0"`, `serial` int ≥ 1, module names match `^(hm|af)_[a-z0-9_]{1,60}$`, versions start with `19.0.`, hashes are 64 lowercase hex, sizes are ints ≥ 0, every file path matches `PATH_RE = ^<module>/[A-Za-z0-9_.@+\-]+(/[A-Za-z0-9_.@+\-]+)*$` with no `.`/`..` component and length ≤ 255; **then §2.8a, which must pass before the release index is looked at at all**.
3. **Archive**: refuse when `Content-Length` exceeds the signed `archive.size`; stream to `downloads/<m>.zip.part`, abort past `archive.size`, hash while streaming, compare hash **and** size, `os.rename` to `.zip`. Only now does §2.10 open it.
4. **Backup (updates only).** `lib/backup.py` launches `pg_dump --format=custom --no-owner` through `odoo.tools.misc.find_pg_tool` and `exec_pg_environ()` (brief: `service/db.py:282-288`) as a **detached** subprocess (`start_new_session=True`), so it survives worker recycling, writing `<store_dir>/backups/<db>-<op>.dump` plus a `.done` JSON with returncode, size and sha256. It requires free space ≥ 2 × `pg_database_size`. The wizard polls until done. The filestore is **not** included and the wizard says so. If `pg_dump` is absent, `ack_backup` — "I have a backup made today" — becomes mandatory.

   **The dump's mode is explicit, not inherited.** Revision 1 left it to the process umask — commonly `0644` — for a file holding every payroll, HR and financial record in the database, which for a ministry customer is the most sensitive object on the box. The target is opened by hm_store, not by `pg_dump`: `fd = os.open(path, O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW, 0o600)` and the fd is passed as the child's `stdout`; the `.done` JSON is written the same way. `backups/` is `0700` and preflight check 6 re-asserts it on every run.

   **Someone owns the deletion.** Reconcile (§2.11) is the pruner, and it prunes on the `done`, `failed` **and** `stalled` paths, not only on success — revision 1 stated a retention intent and named no actor, so the failure paths in §7 left dumps behind for ever. The rule is: keep the last 2 operations' `backup/` trees and the last 2 dumps, **or** everything newer than `hm_store.backup_retention_days` (default 14), whichever keeps more; delete the rest and stamp `backup_pruned_at` on the operation so the record survives the file. A dump that cannot be deleted logs a WARNING and raises a Status row rather than being silently retried for ever.

   **The wizard says what it is making, before it makes it:** "A complete, unencrypted copy of database **prod** — every HR, payroll and financial record — will be written to `/var/lib/odoo/hm_store/backups/prod-HMS-2026-0007.dump` (about 480 MB). It is readable by the `odoo` user only. Hushmand Store deletes it after 2 more operations or 14 days. **Include this folder in your own backup and deletion policy**, or move the file somewhere you control once the update has succeeded."

### 2.8a The keyring floor and the sticky revocation set

Revision 1 verified the keyring against pinned roots and nothing else. An old keyring satisfies pinned roots just as well as a new one, so a compromised store, a MITM, or anyone who could bind the loopback override host could serve the **pre-revocation** keyring and make a revoked or stolen `K_release` trusted again. That destroyed the only stated recovery from release-key theft (§7 "K_release compromised") — the single control between a stolen signing key and permanent RCE on every customer. The fix is the same shape as the release floor, which revision 1 already had right.

**The floor.** `KF = max(trust.MIN_KEYRING_SERIAL, J.keyring_serial, max(keyring_serial over hm.store.operation rows in state done / awaiting_restart / stalled))` — two independent stores, highest wins, exactly as `F` is computed for release serials in §2.7. `MIN_KEYRING_SERIAL` is a constant in `lib/trust.py` set to the serial of the keyring shipped in that bootstrap, so a **fresh install has a floor from its first byte**, before `state.json` or any operation row exists. §4.2b step 3's builder guard refuses a release whose `trust.py` `MIN_KEYRING_SERIAL` is greater than the keyring being shipped, or lower than the previous release's.

**The revocation set.** `RV = union of every revoked_key_ids array in every keyring this installation has ever verified`, persisted in `state.json` and mirrored on the operation rows. It is a **union, never an assignment**: a later keyring can add ids, and no keyring can remove one. Without this, an attacker who could get *any* validly-signed keyring (for instance an old one whose serial happens to be high, or a legitimately re-signed keyring where the vendor mistyped) could narrow the revocation list. A key can only leave `RV` by re-bootstrapping the installation by hand.

**Ordered steps, inserted into §2.8 step 2 after the strict schema and before the release index is touched:**

1. `keyring.serial` is an int ≥ 1 → else `keyring_invalid`.
2. `keyring.serial < KF` → **refuse**, `keyring_replayed`, WARNING log, operation `failed`. The release index in the same response is **not parsed** — it is not read, not schema-checked, not looked at. Message: "SECURITY: Hushmand's key list is older than the one this server already trusts (offered N, have M). This can mean someone is replaying an old key list to re-enable a key Hushmand has withdrawn. Nothing was changed. Do not retry — contact Hushmand and quote `<request_id>`."
3. Any key in `keyring.keys` whose `key_id` ∈ `RV` → refuse, `revoked_key_readmitted`, same treatment. A keyring that tries to un-revoke is as hostile as a replayed one.
4. Compute `RV' = RV ∪ keyring.revoked_key_ids`. **Persist `keyring.serial` and `RV'` durably now, before anything else in the response is trusted**: `state.json` written temp → `fsync` → `rename`, and `keyring_serial` stamped on the operation row in its own committed cursor. The floor only ever rises, so persist-then-use is safe; use-then-persist would lose the bump on a crash and reopen the replay window for the next call.
5. Only now: select release-role keys from the keyring, excluding every id in `RV'`, and verify `release.json` against them (§2.8 step 2 continues as written).

**Everywhere the floor applies.** The online catalogue path; the offline `.hmpkg` keyring (§6 step 4) — an old bundle is the easiest keyring replay of all, and it is the same check on the same value; and `lib/rescue.py`, which reads the floor read-only and prints it. `tests/test_root_pin_immutable.py` also asserts exactly one writer of the floor.

**Recovering from a genuinely lost floor.** If an operator restores an old `state.json` from a backup, the operation-row half of `KF` still holds the real value; if the whole database *and* the data dir are restored to an older point, the floor drops to whatever that backup held, which is the same trust state that backup had, and the next legitimate keyring raises it again. There is no operator-facing "lower the floor" button, and `rescue.py` has no subcommand for it.

### 2.9 Apply: swap, mark, restart

`hm.store.apply.wizard.action_apply`, after `_hm_store_guard('apply')` (§2.4 — the strictest kind: `/web/dataset/call_button` only) and `@check_identity`:

**A. Lock and re-check.** `SET LOCAL lock_timeout = '3s'`; `LOCK ir_module_module IN EXCLUSIVE MODE`; `SELECT FROM ir_cron FOR UPDATE`. This mirrors `_button_immediate_function` (brief: `ir_module.py:599-626`) so the restart never kills a cron mid-transaction. Then `fcntl.flock(<w>/lock, LOCK_EX|LOCK_NB)`; blocking preflight again; operation must be `verified`; **re-hash every staged file against the signed index**, closing the verify→apply gap.

**B. Record the intent durably.** In a separate cursor (`self.env.registry.cursor()`), committed: operation `applying`; `ops/<op>/plan.json`; `ops/<op>/ROLLBACK.txt` (paths `shlex.quote`d, template in §7); an `audit.log` line.

**C. Swap.** For each `m ∈ P`: `chmod 0750` the existing top-level directory, `os.rename(<d>/m, ops/<op>/backup/m)` if it exists, then `os.rename(staging/m, <d>/m)`. On any `OSError`, reverse the renames already done, mark `failed`, raise.

**D. Clear caches.** `odoo.modules.module.Manifest._get_manifest_from_addons.cache_clear()` and `importlib.invalidate_caches()`. Without this, a cached "manifest not found" makes the install silently skip and strand the module in `to install` (brief: probe T1).

**E. Mark, as the calling user.** `Module.update_list()`; `Module.search([('name','in',T_install)]).button_install()`; `Module.search([('name','in',T_upgrade)]).button_upgrade()`. Not the `immediate` variants: v1 never loads a registry inside the request. On any exception: roll back the transaction, reverse C, mark `failed`, surface the message.

**F. Flag, then commit.** `ir.config_parameter.sudo().set_param('base.partially_updated_database','1')`; lines `pending`; operation `awaiting_restart` + `applied_at` + `restart_method` + **`boot_seq_at_apply` (the current value of `hm_store.boot_seq`, read in this same transaction)** + **`tree_id_at_apply`**; `state.json.pending = {op, target_serial: S}` written temp→fsync→rename; `self.env.cr.postcommit.add(_schedule_restart)` (brief: `sql_db.py:166`, run at 568 — it fires only if the commit succeeds). Reading `boot_seq` *inside* the applying transaction is what makes §2.11's comparison sound: any marker written later is necessarily a boot that started after this commit.

**G. Restart — three methods, and the operator picks, because they are not equivalent.** Preflight 19 decides which are available and what the default is.

| Method | What it does | Generation overlap | Default for |
|---|---|---|---|
| `graceful` | `_schedule_restart` starts a `threading.Thread(daemon=True)` that sleeps 3 s and calls `odoo.service.server.restart()` = SIGHUP to `server.pid` (`service/server.py:1681-1688`, container r3). Odoo's own pattern, `addons/iot_drivers/tools/helpers.py:50-61` | **threaded: none** — `ThreadedServer.stop()` shuts the HTTP server down and joins non-daemon threads before `_reexec` (`server.py:657-691`). **prefork: yes, and deliberately so** — `fork_and_reload()` + `stop_workers_gracefully()` (`server.py:1175-1181`), child waits up to 60 s for the new master (`server.py:1105-1134`), new master signals ready only after `preload_registries` (`server.py:1195-1209`) | threaded servers |
| `hard` | run the argv in the `odoo.conf` key `hm_store_restart_command` (for example `/usr/bin/docker restart hushmand-odoo`, or `/usr/bin/systemctl restart odoo`) detached, after the response, via `subprocess.Popen(..., start_new_session=True)`. The key is an **operator-level** `odoo.conf` key exactly like `hm_store_database` — never an `ir.config_parameter`, never editable from the UI, and preflight 19 refuses anything whose argv[0] is not an absolute path to an executable file | none: the process is torn down before the new one starts | — |
| `operator` | hm_store does not restart anything. It commits, shows the exact command for this host, and waits. Reconcile picks the operation up whenever the restart happens | none | **prefork servers** |

The reason prefork does not default to `graceful` is invariant 3: a graceful reload in prefork serves **old Python against a migrating schema** for the whole migration, and that is not a choice the Store should make for a production server without saying so. The wizard says so (H), and the `hard`/`operator` rows are what an operator who cannot accept the overlap uses.

**H. Response.** The wizard returns the `hm_store.progress` client action with `{op_id, restart_method, worker_mode}` and one of three notices — revision 2's single sentence ("Users of **prod** will be disconnected for about a minute") is wrong for prefork, where nobody is disconnected and the upgrade is invisible:

- *threaded + `graceful`*: "Odoo is restarting. Users of **prod**, **training** will be disconnected for about a minute while the upgrade runs."
- *prefork + `graceful`*: "Odoo is reloading. Your users are **not** disconnected — Odoo keeps the old version serving them while the new one upgrades the database, usually for under a minute but for up to 60 seconds by design. During that time some users may see errors from the old version. If that is not acceptable on this server, cancel and use a full restart instead."
- *`operator`*: "Everything is staged and the database is marked. **Nothing further happens until you restart Odoo.** Run: `<the resolved command>`. Then come back and press Check status." — plus, when other databases exist or could not be inspected, the §2.7 step 7 sentence naming them.

**I. The stale-worker guard (new in revision 3, and this is what makes the prefork overlap safe rather than merely disclosed).** The unpacker writes `<addons_data_dir>/hm_store/.hm_build_id` — the `tree_sha256` the signed index gives for `hm_store` — as part of every hm_store placement, and the bootstrap zip ships one. `hm_store/__init__.py` reads that file **once, at import time**, into a module global `_TREE_ID_AT_IMPORT`. Guard step 6 (§2.4) re-reads the file and refuses when the two differ:

> "This Odoo worker is still running the previous version of Hushmand Store. Reload the page. If this keeps happening, restart Odoo."

A process that imported hm_store before the swap holds the **old** id while the file on disk holds the **new** one, so exactly the workers of the old generation fail closed, and they fail closed on hm_store's own surface only — they keep serving the rest of Odoo, which is the point of a graceful reload. A missing file is "unknown": it logs a WARNING and does not refuse, because a hand-unzipped bootstrap may predate the first placement, and preflight seeds it. This does **not** make the overlap disappear — old code is still serving the rest of Odoo against a migrating schema, and no in-Odoo mechanism can change that — it only guarantees the Store itself never acts on a database it no longer matches. S1(4d) measures the window; S8(2) asserts the refusal fires.

**Crash windows, and what each leaves behind:**

| Window | On-disk | Database | Reconcile verdict |
|---|---|---|---|
| B→C | unchanged | operation `applying`, `boot_seq` unchanged | `failed: not applied`; nothing changed |
| during C | mixed | nothing marked | `stalled` + **Resume** (re-runs C–G idempotently) + `ROLLBACK.txt` |
| E/F uncommitted | swapped | nothing marked | `stalled` + **Resume**; a later restart would otherwise run new code on the old schema |
| after F, before G | swapped | marked + flag, `boot_seq == boot_seq_at_apply` | correct by construction: whatever loads the registry next runs the upgrade with the **new** files. A worker that recycled between C and F would run new code briefly; §2.9 I now refuses it instead |
| during G, prefork `graceful` | swapped | marked + flag | the old generation is alive and serving old code for up to 60 s (`server.py:1105-1134`) while the new master upgrades. hm_store calls in those workers are refused by §2.9 I; reconcile run from one of them still reads the marker correctly, because the marker is in the database, not in the process |
| G never happened (`operator`, or a lost signal) | swapped | marked + flag, `boot_seq == boot_seq_at_apply` | `awaiting_restart`: "restart has not happened" — and this is the **only** observation that justifies that verdict (§2.11) |

### 2.10 Unpack rules (`lib/unpack.py`)

Never `extractall`, never `ZipFile.extract`.

1. Open the zip **only after** the archive hash matched.
2. Container: the set of names not ending in `/` must **equal** the signed `files[]` path set, exactly. Refuse: duplicate names in `infolist()`; duplicates after `casefold()`; `flag_bits & 0x1` (encrypted); a compress type other than STORED or DEFLATED; `(external_attr >> 16) & 0o170000` not in `{0, S_IFREG, S_IFDIR}` (this is what rejects symlinks — Python 3.12's `_extract_member` has no symlink handling, brief, and we do not call it anyway); any `ZipInfo.file_size` that differs from the signed size.
3. Per signed `(path, sha256, size)`: create parents `0750`, checking each component with `os.lstat` for a symlink; `fd = os.open(target, O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW, 0o640)`; copy from `zf.open(info)` in 64 KiB chunks, stopping past `size`; hash while copying; any mismatch fails the whole module.
4. Walk the staged tree: it must contain exactly the signed files and nothing else.
5. `ast.literal_eval` the staged `<m>/__manifest__.py` (never import it): `version == index version`; `auto_install` falsy; `installable` not False; `license == "OPL-1"`; `set(depends) ⊆ set(index depends)`.
6. On any failure: delete `ops/<op>/staging` and `downloads`, set `failed` with a code, change nothing on the import path.
7. **When the staged module is `hm_store`: the trust gate** (`lib/unpack.py` `check_hm_store_trust`, run after rule 5 and before anything is swapped). Revision 1 validated a staged manifest's version, `auto_install`, `installable`, `license` and `depends`, and never looked at what was in `lib/trust.py` — so one release signed with a stolen `K_release` could ship a `trust.py` pinning the attacker's roots and cut `K_root` out of that customer permanently.

   Read the staged `hm_store/lib/trust.py` with `ast.parse` and `ast.literal_eval` over its module-level assignments — **never import it, never `exec` it**; a name whose value is not a literal, or a module with any statement other than imports, assignments and a docstring, is itself a refusal (`trust_py_not_literal`). Then compare against the root pin C13:

   | Field | Rule |
   |---|---|
   | `ROOT_KEYS` | must be a `dict[str, str]` of `key_id` → 44-char base64; must be a **superset** of the pinned set with every pinned id mapping to the **same** value. A removed or altered root key is never allowed by a release, only by re-bootstrapping. |
   | added root keys | allowed **only** when the release carries a valid K_root `trust_update` (below) listing exactly those ids |
   | `ROOT_THRESHOLD` | may rise, may not fall; must be ≤ `len(ROOT_KEYS)` |
   | `MIN_KEYRING_SERIAL` | must be ≥ the current persisted keyring floor `KF` |
   | `DOMAIN_KEYRING` / `DOMAIN_RELEASE` / `DOMAIN_BOOTSTRAP` / `DOMAIN_TRUST_UPDATE` | byte-identical to the pinned prefixes |
   | `DEFAULT_STORE_URL` | `https://`, and the **host** must equal the current one, or the operation needs an explicit `ack_store_url_change` on the wizard naming both hosts — the same weight as a takeover acknowledgement |
   | caps (`CATALOGUE_MAX`, archive/file/size limits) | may shrink; may grow by no more than 2× the pinned value |

   **The `trust_update` block.** A release whose `hm_store` archive changes the root set carries, alongside `release.sig`, a second file `release.root.sig`: an Ed25519 signature **by K_root** over `b"hushmand-trust-update-v1\n" + canonical-JSON(trust_update)`, where

   ```json
   {"_type": "hushmand-trust-update", "schema": 1, "series": "19.0", "serial": 7,
    "hm_store_tree_sha256": "<64 hex>", "adds_root_keys": ["root-2029"],
    "root_threshold": 1, "min_keyring_serial": 7}
   ```

   The client requires all of: the signature verifies against a **currently pinned** root key; `hm_store_tree_sha256` equals the `tree_sha256` the (release-signed) index gives for `hm_store`, which is what binds the authorisation to this exact tree; `serial` equals the index serial; `adds_root_keys` exactly equals the set of ids the staged `trust.py` adds; and nothing in the block removes a pinned key. Any failure → refuse the whole operation, `root_pin_change_refused`, delete staging, change nothing.

   **Rewriting the pin.** On a successful apply of an authorised trust update — and only there — reconcile (§2.11) rewrites C13 with the new root set, `0400`, temp → `fsync` → `rename`, keeping the previous file as `root.json.<old-serial>.bak` (`0400`) and appending a line to `audit.log`. That is the second and last writer of C13; there is no third.

   **What this costs the vendor.** A release that changes `trust.py`'s trust constants needs K_root out of the safe and a second signature on C1b. That is deliberate: it is the same ceremony as revoking a release key, and it should be about as rare. A release that only changes hm_store *code* needs nothing extra, because the constants are unchanged and rule 7 passes on equality.

Modes are `0640`/`0750` and not `0440`/`0550`: the owner can `chmod` regardless, and read-only directories break the backup rename (invariant 5). The integrity check (§2.12) is what detects a tampered tree, including a planted `__pycache__/*.pyc`.

### 2.11 Reconcile after restart

Runs on opening Modules (the dashboard's `default_get`) and on an operation's **Check status**.

**The restart witness is the boot marker, not `base.partially_updated_database`.** Revision 2 read the flag's presence as "restart has not happened" and its absence-plus-pending-states as `stalled`. Both mappings are wrong. `Registry.new` does delete the flag in its own committed transaction before `load_modules` runs (`orm/registry.py:172-176`) — but at the *end* of a **successful** `load_modules`, `loading.py:599-607` (container r3) re-inserts it:

```sql
INSERT INTO ir_config_parameter(key, value)
SELECT 'base.partially_updated_database', '1'
WHERE EXISTS(SELECT FROM ir_module_module WHERE state IN ('to upgrade','to install','to remove'))
ON CONFLICT DO NOTHING
```

So a restart that happened, loaded cleanly, and left one target short of `installed` puts the flag straight back — and revision 2's reconcile would have answered "Restart has not happened" and offered **Restart now**, which re-runs the same failing load, for ever. The flag says "this database has pending module work", which is true both before and after a restart; it is not a restart witness and never was.

**The marker.** `hm.store.boot._register_hook()` (§2.3), called exactly once per registry load at STEP 9 of `load_modules` (`modules/loading.py:588-594`), bumps `hm_store.boot_seq` and writes `hm_store.boot_at`:

```sql
INSERT INTO ir_config_parameter(key, value) VALUES ('hm_store.boot_seq', '1')
ON CONFLICT (key) DO UPDATE SET value = (ir_config_parameter.value::bigint + 1)::text
```

`ir_config_parameter` has a UNIQUE constraint on `(key)` and only `key`/`value` NOT NULL, with `id` defaulting from its sequence (container r3, `\d ir_config_parameter`), so the `ON CONFLICT (key) DO UPDATE` is valid. `boot_seq` only ever rises; it is not a clock and nothing compares it to wall time. **Assumption, written as one:** that a write made in `_register_hook` is *committed* in every boot shape (threaded with and without `-d`, prefork with and without `-d`, and `--stop-after-init`). `_register_hook` runs on the same cursor `load_modules` uses and `env.flush_all()` follows it at `loading.py:594`, but "flushed" is not "committed" and this spec does not assert it from reading. **S1(9) settles it, and until it passes nothing in v1 may depend on the marker** — §2.6 check 20 is the gate that keeps that promise.

For each operation in `awaiting_restart`, let `booted = (hm_store.boot_seq > operation.boot_seq_at_apply)`:

| Observation | Result |
|---|---|
| **not `booted`** (whatever the flag says) | `awaiting_restart`: "Restart has not happened." Offer **Restart now** (step G again, by the operation's `restart_method`) and the manual command for this host. This is the *only* branch that offers a restart. |
| `booted`, some target still `to install`/`to upgrade`/`to remove` — flag present or absent | `stalled`. The load ran and left work pending: a worker killed by `limit_time_real` after `registry.py:172-176` deleted the flag, a module that raised, or a dependency Odoo would not resolve. **Never offer an automatic restart here** — the same load would fail the same way. Offer only the CLI: `odoo -c <conf> -d <db> -u <T_upgrade> -i <T_install> --stop-after-init`, plus **Resume** which is explicitly labelled "run the upgrade again — only do this if you have fixed what caused it" and requires `@check_identity`. Show whether the flag is present, because that is what the next boot will act on. |
| `booted`, every target `installed` with `latest_version == index version` | `done`. Write `state.json`; if this operation carried an authorised `trust_update`, rewrite the root pin C13 (§2.10 rule 7, the only other writer); delete `downloads/` and `staging/`; **prune backups (below)**; chatter note on each licence used; INFO log line; `audit.log` line. |
| `booted`, targets back at `from_version` / `uninstalled` (Odoo's `reset_modules_state` ran after a failed load, brief: `loading.py:611-631`) | `failed`. Show `rollback_text`; **prune backups**; the traceback is in the server log. |
| `booted` more than once with no progress (`boot_seq` advanced ≥ 2 since `applied_at` and the targets are unchanged) | `stalled`, and the banner says so in as many words: "Odoo has restarted twice and the upgrade has not moved. Do not restart again." This is the loop revision 2's flag-based table would have entered silently. |

**Timeout, so `awaiting_restart` is not forever.** An operation in `awaiting_restart` with `not booted` and `applied_at` older than `hm_store.restart_timeout_minutes` (default 30) is shown as **`awaiting_restart` (overdue)** with the `operator` instructions, whatever `restart_method` was chosen. It is not auto-failed: the files are swapped and the database is marked, so the correct end state really is "restart this server", and the Store keeps saying that until someone does.

**`state.json`, in full** (revision 1 listed only the first three groups, which is why the keyring floor had nothing to compare against even though S3 was asked to test it):

```json
{"schema": 1,
 "serial": 3, "floor": 3,
 "keyring_serial": 5, "keyring_floor": 5,
 "revoked_key_ids": ["rel-2026-10"],
 "root_pin_sha256": "<64 hex>",
 "last_successful_catalogue_at": "2026-10-01T09:12:44Z",
 "newest_created_at_seen": "2026-10-01T09:00:00Z",
 "modules": {"hm_payroll": {"archive_sha256": "<64 hex>", "tree_sha256": "<64 hex>", "version": "19.0.1.0.2"}},
 "pending": null}
```

Every field is written temp → `fsync` → `rename`. `keyring_floor` and `revoked_key_ids` are written by §2.8a step 4 the moment a keyring is accepted, not here — reconcile only re-states them. `last_successful_catalogue_at` and `newest_created_at_seen` feed §2.7 step 0.

**Pruning is reconcile's job on every terminal path** — `done`, `failed` and `stalled` alike. Keep the last 2 operations' `backup/` trees and the last 2 `pg_dump`s, **or** everything newer than `hm_store.backup_retention_days` (default 14), whichever keeps more; delete the rest; stamp `backup_pruned_at`. A `stalled` operation keeps its own backup until it reaches a terminal state, whatever the counts say, because that backup is the recovery.

A module that `state.json` calls installed but whose folder is missing raises a red banner on Modules and Status: "Files for X are missing from `<d>`. The add-ons data folder is not on persistent storage." Recovery is manual in v1 (§7).

**Auto-rollback is deferred to slice S9 and only in this shape:** a post-boot reconcile, running from `hm.store.boot._register_hook`, that on a definitive failure (`booted`, targets back at `from_version`) restores `backup/<op>/<m>`, records `rolled_back_restart_pending`, and schedules **exactly one** further restart, never a second for the same operation. **Whether `_register_hook` runs during registry load is no longer the open question** — it does, exactly once per load, documented and called at `modules/loading.py:588-594` ("This is done *exactly once* when the registry is being loaded"), read in the container in revision 3; that item leaves Appendix B and S9's gate shrinks to the parts that are genuinely open: whether a restored tree boots, and whether exactly one further restart is emitted. The separate question of whether the marker write **commits** belongs to S1(9) and gates v1's reconcile, not S9. hm_store **does not** monkeypatch `Registry.new`: a wrapper installed from `post_load` runs inside the first `Registry.new` of a restarted process and therefore cannot wrap the boot that runs the upgrade — the exact flaw that sank the operator-first design.

### 2.12 Audit log

Four places, so no single actor can erase the trail:

- **`hm.store.operation` + lines** — read-only to every group, and **write-protected by an explicit, named internal escape hatch** (corrected in revision 3):

  ```python
  def write(self, vals):
      if not self.env.context.get('hm_store_internal'):
          raise UserError(_("Hushmand Store operations are an audit record and cannot be edited."))
      return super().write(vals)

  def unlink(self):
      raise UserError(_("Hushmand Store operations cannot be deleted."))   # no hatch: nothing deletes them
  ```

  Every internal transition — §2.9 B's `applying`, §2.9 F's `awaiting_restart` + `applied_at` + `boot_seq_at_apply`, §2.11's `done`/`failed`/`stalled`, `backup_pruned_at`, `keyring_serial`, every line `result` — runs `with_context(hm_store_internal=True)`, exactly as §2.14 item 2 already does with `hm_license_internal`. `tests/test_access.py` asserts the context key appears only inside `models/` and `wizard/`, never in a view, an action's `context=`, a `default_*` key or an XML data file, so it cannot be set from a URL or a button.

  *Why revision 2's wording could not be implemented:* "written through `sudo` only; `write()` and `unlink()` raise `UserError` unconditionally" is a contradiction. `sudo()` sets `env.su`, which is read by `check_access` (`orm/environments.py:178-190`, where `is_superuser` is `self.su`); it does **not** bypass a model's own overridden `write`, because `su` is an access-check flag, not a method-dispatch switch. An unconditional raise would have made the §2.9 state machine unwritable by anything, including the code that owns it.

  **Say plainly what this is worth.** A context flag is a guard against accident and against a `group_system` user editing a record through the UI or a generic RPC write — not against code running inside the Odoo process, which by definition can set any context it likes. An in-database record can never be truly immutable to its own application. That is precisely why the append-only `audit.log` below and the server-side `odoo_store_events` (§3.2) exist: they are the two sinks that survive a compromised in-database path, and they, not this model, are what an investigator reads.
- **Server log** — one INFO line per transition: `hm_store: op=HMS-2026-0007 user=admin(2) ip=10.0.0.5 db_uuid=… serial 2->3 state=awaiting_restart modules=hm_payroll:19.0.1.0.2:<sha8>`. Odoo's own ALLOW/DENY lines appear too, because step E runs as the user.
- **`<store_dir>/audit.log`** — append-only JSON lines, written with `O_APPEND`, outside the database, so a database restore or an SQL edit does not rewrite history. Three trust events are always written here, whatever else happens: **every keyring-floor raise** (old and new serial, and any ids added to the revocation set), **every root-pin write** (the seed at bootstrap and any K_root-authorised trust update, with both fingerprints), and **every refusal** with a `keyring_replayed`, `revoked_key_readmitted`, `root_pin_change_refused` or `root_pin_mismatch` code. These are the lines that tell an investigator whether the root of trust moved and when.

  **Every line also carries the process identity** (new in revision 3, and the reason is §2.6 check 5): `euid`, `egid`, `pid`, `workers`, `restart_method`, `boot_seq`, and `actor` — one of `user:<login>#<id>`, `cron:<login>#<id>` or `boot`. A line with `"euid": 0` is a deployment that should never have got past check 5, and having it in the file is how that is noticed after the fact rather than argued about.
- **Licence chatter** — a note on each `hm.license` used, and the server's `odoo_store_events` (§3.2). **The daily check cron is attributed, never anonymous:** it runs as `base.user_root` (§2.14 item 6), and its catalogue call is written to `audit.log` with `"actor": "cron:__system__#1"` and to `odoo_store_events` with the same attribution, so a daily outbound call is never mistaken for an admin action and an admin action is never mistaken for the cron.

Signature and hash failures log at **WARNING**, not ERROR, so CI's "no ERROR line" rule (`ci.yml:181-184`) survives the negative tests, which also use `mute_logger`. The UI text is fixed: "SECURITY: the download did not match Hushmand's signature. Nothing was changed. Do not retry — contact Hushmand and quote `<request_id>`."

### 2.13 Uninstall

Odoo's own Apps → Uninstall; hm_store adds nothing to it. Files stay in the data dir — a module that is not installed is never imported — and are removed only through a later "Remove files" action (out of scope for v1). Uninstalling hm_store leaves every other Hushmand module working, along with `state.json` and the opt-in.

### 2.14 hm_license changes (same slice as the hm_store skeleton)

`addons/hm_license/models/hm_license.py`:

1. `key = fields.Text(..., groups="base.group_system")` (repo: the field at lines 82-87 has no `groups=`, and `security/ir.model.access.csv:2` gives `base.group_user` read — the plain `demo` user can `search_read(['key'])` today, tested in the threat brief). Threat T11: the key becomes a download credential.
2. **L2 fix:** in `write()`, if `vals` touches `licence_id, customer, modules, features, issued, expires, max_users, state, status_detail` and the context lacks `hm_license_internal`, call `action_verify()` after `super().write()`. `_apply_payload`, `_mark_invalid` and `_refresh_state` write `with_context(hm_license_internal=True)`. hm_store does not depend on this (it re-verifies from `key` every time), but it costs ~10 lines and closes the defect at source.
3. `_store_verified_payloads()` / `_store_payload_bytes()` helpers (§2.3), returning the exact `json.dumps(payload, sort_keys=True, separators=(",",":")).encode("utf-8")` bytes that `_decode` builds (repo: `hm_license.py` `_decode`).
4. **K_licence re-key (S5a).** `VENDOR_PUBLIC_KEY` at `hm_license.py:56` becomes `VENDOR_PUBLIC_KEYS`, a `{key_id: b64}` map, and `_verify_signature` tries each entry. This is what lets S5a retire the plaintext-key era without stranding a customer who has not yet pasted a re-issued licence; an id is removed from the map once no outstanding licence uses it, and the removal date is recorded. The map is a code constant, never an `ir.config_parameter`.
5. Version → `19.0.1.0.1`. Tests: `demo` gets `AccessError` on `search_read(['key'])` while `status()` still works for `demo`; writing `modules` without `key` re-verifies; a licence signed by a retired key id is refused once that id leaves `VENDOR_PUBLIC_KEYS`; **and the cron user can read `key`** (item 6).
6. **The cron's user is stated, because item 1 makes it load-bearing** (new in revision 3). `key = fields.Text(..., groups="base.group_system")` is enforced by the ORM on **read**, in any context including a cron's, so the daily check cron of D13 — which re-verifies every `hm.license.key` and calls the catalogue with the licence envelope — fails with `AccessError` on its first read if it runs as the default cron user. `data/ir_cron_data.xml` therefore sets `user_id` explicitly to **`base.user_root`**, the conventional owner of a data cron, and `hm_store.check_cron` is the record customers can deactivate (D13).

   Two consequences are written down rather than absorbed. First, this **widens what the cron can do** to everything `base.user_root` can do, which is everything — so the cron's entry point is the narrowest in the module: `_hm_store_guard('cron')` (§2.4) refuses it any access to the import path, `ir.module.module`, `base.partially_updated_database` or `server.restart()`, and `tests/test_guard.py` asserts the cron method reaches none of them. Second, the cron's outbound call is **attributed** in both audit sinks (§2.12), so a daily call from `__system__` is never read as an admin action.

L1 (no database binding in the payload) stays open in `docs/AUDIT-2026-09.md`: binding the **offline** gate to a database would break a ministry restoring onto new hardware with no internet, and the online layer binds instead (§3.7).

---

## 3. Licence server changes — `E:\web\hushmand-license-server`

### 3.1 Why the MyERP tables are not reused

`licenses.product_id` is a single FK; plans are per product and `LicenseIssuer::issue` looks them up by slug alone (`LicenseIssuer.php:19`), which is ambiguous the moment two products share a slug; the JWT hard-codes `aud` and `product` to `hushmand-erp` (`LicenseActivationService.php:289,296`); and Odoo licences are issued and signed **offline**, so the server cannot mint one. v1 therefore adds parallel `odoo_*` tables and **touches no MyERP code path**, including the transfer-on-activate behaviour at `LicenseActivationService.php:112-143` (that remains a MyERP defect; hm_store's flow has no equivalent because activation never moves anything implicitly).

### 3.2 Migration — `database/migrations/2026_09_28_000000_create_odoo_store_tables.php`

```php
Schema::create('odoo_licences', function (Blueprint $t) {
    $t->id(); $t->uuid('uuid')->unique();
    $t->string('licence_id', 64)->unique();       // payload.licence_id — THE lookup key and THE throttle key
    $t->char('payload_sha256', 64)->index();      // sha256(decoded payload_b64): audit + first-use pinning
    $t->foreignId('customer_id')->nullable()->constrained();
    $t->string('customer_label', 190);            // payload.customer, compared on every request
    $t->json('payload');                          // the verified payload — WHAT AUTHORISES (§3.4)
    $t->json('modules');
    $t->string('series', 8)->default('19.0');
    $t->date('issued_on')->nullable(); $t->date('expires_on');
    $t->unsignedSmallInteger('max_databases')->default(2);
    $t->string('status', 16)->default('active');  // active | suspended | revoked
    $t->string('status_reason', 190)->nullable();
    $t->timestamp('registered_at')->nullable();   // null => auto-registered on first use
    $t->timestamps();
});
Schema::create('odoo_activations', function (Blueprint $t) {
    $t->id(); $t->uuid('uuid')->unique();
    $t->foreignId('odoo_licence_id')->constrained()->cascadeOnDelete();
    $t->uuid('database_uuid');                    // lower-cased — an accounting label, NEVER a credential
    $t->char('install_pubkey', 44)->nullable();   // pinned on first use: raw Ed25519 public key, base64 (§3.4 step 5)
    $t->timestamp('install_pubkey_pinned_at')->nullable();
    $t->string('status', 16)->default('active');  // active | released
    $t->string('last_ip', 45)->nullable();
    $t->string('last_asn', 16)->nullable();       // cheap anomaly signal, surfaced by odoo:activations
    $t->unsignedInteger('archive_downloads')->default(0);   // per current serial; reset when last_release_serial moves
    $t->string('hm_store_version', 32)->nullable();
    $t->string('odoo_version', 32)->nullable();
    $t->unsignedInteger('last_release_serial')->nullable();
    $t->timestamp('first_seen_at'); $t->timestamp('last_seen_at');
    $t->timestamp('released_at')->nullable(); $t->string('released_reason', 190)->nullable();
    $t->timestamps();
    $t->unique(['odoo_licence_id', 'database_uuid']);
});
Schema::create('odoo_releases', function (Blueprint $t) {
    $t->id(); $t->string('series', 16); $t->unsignedInteger('serial');
    $t->string('key_id', 32);
    $t->longText('release_json');                 // EXACT signed bytes, base64
    $t->json('release_sig');                      // {"key_id","sig"}
    $t->longText('keyring_json')->nullable(); $t->json('keyring_sig')->nullable();
    $t->unsignedInteger('keyring_serial')->nullable();
    $t->timestamp('created_at_signed');
    $t->timestamp('published_at')->nullable(); $t->timestamp('withdrawn_at')->nullable();
    $t->timestamps(); $t->unique(['series', 'serial']);
});
Schema::create('odoo_release_archives', function (Blueprint $t) {
    $t->id(); $t->foreignId('odoo_release_id')->constrained()->cascadeOnDelete();
    $t->string('module', 64); $t->string('version', 32);
    $t->char('sha256', 64); $t->unsignedBigInteger('size_bytes');
    $t->string('storage_path', 255); $t->timestamps();
    $t->unique(['odoo_release_id', 'module']);
});
Schema::create('odoo_store_events', function (Blueprint $t) {
    $t->id(); $t->string('endpoint', 16);         // catalogue | archive
    $t->string('licence_id', 64)->nullable()->index();
    $t->uuid('database_uuid')->nullable();
    $t->string('module', 64)->nullable(); $t->unsignedInteger('serial')->nullable();
    $t->string('result', 8);                      // ok | denied | error
    $t->string('reason_code', 48)->nullable();
    $t->string('ip', 45)->nullable(); $t->uuid('request_id')->nullable();
    $t->timestamp('created_at')->useCurrent();
});
```

Models: `app/Models/Odoo/{OdooLicence,OdooActivation,OdooRelease,OdooReleaseArchive,OdooStoreEvent}.php`. Factories: `database/factories/Odoo/*Factory.php`. **No raw licence key is ever stored.**

### 3.3 Verifying a licence in PHP — `app/Services/Odoo/OdooLicenceVerifier.php`

The client sends the exact bytes it verified, so **PHP never re-canonicalises JSON**. This removes the whole PHP↔Python canonical-JSON parity risk that would otherwise have to be proven by test vectors.

1. `payload_b64` → `base64_decode($s, true)`; length ≤ 8192; failure → `licence_invalid`.
2. `sodium_crypto_sign_verify_detached(base64_decode($sig), $payloadBytes, $pub)` for each key in `config('odoo_store.licence_public_keys')` until one verifies; none → `licence_invalid`. It is a **map** and not a single key so that the S5a re-key has a transition window; ids are removed from it, not left "just in case".
3. `json_decode($payloadBytes, false, 16, JSON_THROW_ON_ERROR)`; require `licence_id`, `customer`, `modules` (array of strings) and `expires` (ISO date) — the same `REQUIRED_CLAIMS` as `hm_license.py:59` (repo) — and `licence_id` must match `^[A-Za-z0-9._:-]{1,64}$`.
4. `payload_sha256 = hash('sha256', $payloadBytes)`, recorded on the event row and used for first-use pinning (§3.4).

**The `licence` envelope field is gone.** Revision 1 sent it, never verified it, never bound it to `payload_b64`/`sig` — §3.3 said in as many words that it "is not inspected at all" — and then keyed both per-licence rate limits on `sha256` of it and made it the `UNIQUE` lookup column `key_sha256`. Anyone holding one valid `(payload_b64, sig)` pair therefore got a fresh limiter bucket per request by varying an unauthenticated string, collapsing both per-licence limits to the per-IP ones, which a stolen-key attacker distributes trivially; and the audit join key was attacker-chosen. It also could not have been a stable identifier even for an honest client, because `hm_license._decode` canonicalises the *parsed* payload on verify (repo: `json.dumps(payload, sort_keys=True, separators=(",",":"))`), so one licence has unlimited valid envelope encodings. The field carried no authenticated information; it is removed from the request (§3.5), the column is replaced by `licence_id` + `payload_sha256` (§3.2), and every limiter keys on the **verified** `licence_id` (§3.6).

`config/odoo_store.php` is **committed** and holds public keys only, never read from `.env`, so editing `.env` cannot widen trust:

```php
return [
  'licence_public_keys'   => ['lic-2026-11' => '<base64 raw 32 bytes>'],   // map; see S5a re-key
  'root_public_keys'      => ['root-2026' => '<base64 raw 32 bytes>'],
  'release_public_keys'   => ['rel-2026-10' => '<base64 raw 32 bytes>'],
  'series'                => ['19.0'],
  'default_max_databases' => 2,
  'always_entitled'       => ['hm_license', 'hm_store'],
  'require_registration'  => true,      // D9: true from the first sale, not "within a month"
  'storage_prefix'        => 'odoo-releases',
  'enabled'               => true,      // kill switch -> 503 store_unavailable
];
```

### 3.4 Registration and authorisation

`app/Services/Odoo/OdooStoreService::authorise()`, shared by both endpoints, inside `DB::transaction` with the licence row locked:

1. Verify the licence (§3.3); failure → 401 `licence_invalid`. **Nothing before this point does per-licence work** — only the cheap per-IP pre-verify limiter of §3.6 stands in front of it.
2. Look up `odoo_licences` by `licence_id`.
   - found: `status` must be `active` → else 403 `licence_revoked` / `licence_suspended`.
   - not found and `require_registration` → 403 `licence_not_registered`.
   - not found and not `require_registration` → auto-register with `registered_at = null`, storing `payload`, `payload_sha256`, `modules`, `expires_on`, `customer_label` and `max_databases = payload.max_databases ?? default` **as presented** — trust on first use.
3. **The presented payload must match the registered row.** Compare, field by field: `modules` (set equality), `expires` vs `expires_on`, `max_databases`, `customer` vs `customer_label`. Any divergence → 403 `licence_mismatch`, event row `result=denied, reason_code=licence_mismatch`, a `warning`-level log line naming `licence_id`, `payload_sha256` presented vs stored, and the IP, because the overwhelmingly likely cause is a forged licence. For an auto-registered row (`registered_at = null`) the same comparison applies against the first payload ever seen, so even the `require_registration = false` window is pin-on-first-use rather than open.

   *Why this exists.* Revision 1 read `payload.modules` and `payload.expires` from the **presented** licence and never looked at the row, while `odoo_licences.modules`, `expires_on` and `max_databases` were written at registration and then consumed by nothing. Anyone holding `K_licence` — which revision 1 stored unencrypted on disk beside `K_release` (finding 4) — could forge a licence carrying a *known, registered* `licence_id` with `modules` = everything and `expires` = 2099, and `require_registration = true` would have waved it straight through. `licence_id`s are not secret: they appear in the offline bundle filename (§6), in `odoo_store_events.licence_id`, and on the customer's own `hm.license` record. T24's claim was therefore narrower than it read.
4. **Authorise from the row, not from the payload.** Expiry is `today(UTC) > odoo_licences.expires_on` → 403 `licence_expired`; entitlement in §3.5's archive check is `module ∈ odoo_licences.modules ∪ always_entitled`; slots are `odoo_licences.max_databases`. The payload is what step 3 checks; the row is what decides. Downloads stop at `expires`; the 30-day grace only keeps installed code running (decision D3).

   A legitimately re-issued licence updates the row through `php artisan odoo:licence:register --file=… --replace --reason="added hm_payroll, PO-4471"`, which verifies the signature over `payload_b64` before writing and records the previous payload in `odoo_store_events`. There is no path that widens a row from an inbound request.
5. **Installation binding.** Upsert the activation for (`licence_id`, `database_uuid`): an `active` row refreshes `last_seen_at`, `last_ip`, `last_asn`, versions; a missing or `released` row is created/reactivated only if the count of `active` rows is `< max_databases`, else 403 `activation_limit`. On the **first** request for that pair, store the client's `install_pubkey` and stamp `install_pubkey_pinned_at`. On every later request, verify `X-Hm-Install-Sig` — an Ed25519 signature by that pinned key over `sha256(licence_id|database_uuid|endpoint|serial|module|request_id|floor(unixtime/60))`, accepting the current and previous minute — and refuse with 403 `installation_mismatch` when it does not verify. A genuine reinstall on the same uuid is unblocked by `odoo:activation:release`, which clears the pin; the client generates its key on first use and keeps it at `<store_dir>/install_key.pem`, mode `0600`, never in the database and never in a `pg_dump`.

   **What this is and is not worth** (D20). It raises licence-key theft from "read one text field" — which until §2.14's `groups=` fix every internal user could do — to "exfiltrate the server's data directory". It does **not** stop an attacker who copies the whole data dir, and it does not stop the vendor's own mistake. Say that rather than counting it as a theft control it is not (§5 T11). Whether a customer's own backup regime sweeps up `install_key.pem` decides how much of the gap remains, and that is an open item in Appendix B, settled by S7.
6. Write an `odoo_store_events` row whatever the outcome, and increment `archive_downloads` on a successful archive. `odoo:activations` flags an activation whose `last_asn` changed since the previous call, or whose `archive_downloads` for the current serial exceeds the module count by more than 3×; both are cheap, both are detection rather than prevention, and both are surfaced rather than enforced.

**Registration is explicit and offline-friendly.** `tools/issue_license.py --emit-registration <file>` writes `{licence_id, payload_b64, sig, payload_sha256, customer, modules, expires, max_databases}`; the vendor runs `php artisan odoo:licence:register --file=…`, which verifies the signature over `payload_b64` before inserting. The command refuses a raw key file, because extracting the payload bytes from an envelope in PHP would require exactly the canonicalisation this design avoids. Registering is the same keystroke as issuing, which is why D9 now says `require_registration = true` from the first sale rather than within the first month.

### 3.5 Endpoints

`routes/api.php`, a new group **outside** the existing `throttle:license-api` group (that limiter keys on `license_key`):

```php
Route::prefix('v1/odoo')
    ->middleware(['odoo.store.enabled', 'throttle:odoo-store-pre'])   // cheap per-IP, BEFORE any signature work
    ->group(function (): void {
        Route::post('/catalogue', [OdooStoreController::class, 'catalogue']);
        Route::post('/archive',   [OdooStoreController::class, 'archive']);
    });
```

Controller `app/Http/Controllers/Api/Odoo/V1/OdooStoreController.php`; requests `app/Http/Requests/Odoo/{CatalogueRequest,ArchiveRequest}.php`.

Common validation: `payload_b64` (string ≤ 8192), `sig` (string ≤ 128), `database_uuid` (required, `uuid`, lower-cased — Odoo's `database.uuid` is a `uuid1` and passes Laravel's unversioned rule, brief), `install_pubkey` (string, exactly 44 chars, base64), `series` (in `19.0`), `client.hm_store_version` / `client.odoo_version` (≤ 32); header `X-Hm-Install-Sig` (base64 ≤ 128) required once the pair is pinned. Archive adds `serial` (int ≥ 1) and `module` (`^(hm|af)_[a-z0-9_]{1,60}$`). **There is no `licence` field** (§3.3). A request body larger than 32 KiB is rejected by nginx before PHP sees it.

**`POST /api/v1/odoo/catalogue`**

```http
POST /api/v1/odoo/catalogue HTTP/1.1
Content-Type: application/json
User-Agent: hm_store/19.0.1.0.0
X-Request-Id: 5b0c8a0e-3a8e-4c43-9b1e-0c7d2b0f4a11
```
```json
{
  "payload_b64": "eyJjdXN0b21lciI6Ik1pbmlzdHJ5IFgiLCJleHBpcmVzIjoiMjAyNy0wOS0zMCIsLi4ufQ==",
  "sig": "3q2+7wAAAA...==",
  "database_uuid": "662bfd09-a1f8-11f1-bb00-a759a8816bf4",
  "install_pubkey": "9pQ1v0mS3xR2aB4cD6eF8gH0iJ2kL4mN6oP8qR0sT2U=",
  "series": "19.0",
  "client": {"hm_store_version": "19.0.1.0.0", "odoo_version": "19.0-20260817"}
}
```

`200 OK`:

```json
{
  "status": true,
  "error": null,
  "request_id": "5b0c8a0e-3a8e-4c43-9b1e-0c7d2b0f4a11",
  "data": {
    "licence_id": "0d6f2c1e-7b1a-4f0e-9d7e-5c3b1a2f9e10",
    "activation": {
      "database_uuid": "662bfd09-a1f8-11f1-bb00-a759a8816bf4",
      "status": "active",
      "first_seen_at": "2026-10-01T09:12:44Z",
      "databases_used": 1,
      "databases_allowed": 2
    },
    "keyring": {
      "keyring_json_b64": "eyJfdHlwZSI6Imh1c2htYW5kLWtleXJpbmciLC4uLn0=",
      "keyring_sig": {"key_id": "root-2026", "sig": "Tm90QVJlYWxTaWc...=="}
    },
    "release": {
      "series": "19.0",
      "serial": 3,
      "release_json_b64": "eyJjcmVhdGVkX2F0IjoiMjAyNi0xMC0wMVQwOTowMDowMFoiLC4uLn0=",
      "release_sig": {"key_id": "rel-2026-10", "sig": "3q2+7wAAAA...=="}
    }
  }
}
```

The current release is the published, not-withdrawn row with the highest serial for the series; if there is none, `data.release` is `null` and `data.keyring` is still returned.

**`POST /api/v1/odoo/archive`** — same body plus `"serial": 3, "module": "hm_payroll"`. Extra checks: `module ∈ odoo_licences.modules ∪ always_entitled` — **the stored row, not the presented payload** (§3.4 step 4) — else 403 `module_not_licensed`; release published and not withdrawn, else 404 `release_not_found`; module in that release, else 404 `module_not_in_release`.

`200 OK`: `Content-Type: application/zip`, `Content-Length`, `X-Hushmand-Archive-Sha256: <hex>`, `Cache-Control: no-store`, `Content-Disposition: attachment; filename="hm_payroll-19.0.1.0.2.zip"`, streamed from the private disk. **The client ignores the header for trust**; only the signed index decides.

**Errors**, both endpoints:

```json
{"status": false, "error": "activation_limit", "request_id": "5b0c8a0e-…",
 "data": {"databases_used": 2, "databases_allowed": 2}}
```

| HTTP | `error` | `data` |
|---|---|---|
| 422 | `invalid_request` | `{"fields": ["database_uuid"]}` |
| 401 | `licence_invalid` | null |
| 403 | `licence_revoked` / `licence_suspended` / `licence_not_registered` | null |
| 403 | `licence_mismatch` | null — deliberately no field list; a forger is not told which field gave them away |
| 403 | `installation_mismatch` | null |
| 403 | `licence_expired` | `{"expires": "2026-12-31"}` |
| 403 | `activation_limit` | `{"databases_used": 2, "databases_allowed": 2}` |
| 403 | `module_not_licensed` | `{"module": "hm_payroll"}` |
| 404 | `release_not_found` / `module_not_in_release` | null |
| 429 | `rate_limited` | `{"retry_after": 30}` |
| 503 | `store_unavailable` | null |

There is deliberately **no free-text `message`**: hm_store maps codes to local translated strings (threat T12), and an unknown code renders as `Unknown error code: <code>` through a Char field.

### 3.6 Auth, rate limits, storage, admin

- **Authentication** is the signed licence payload over TLS, plus the pinned installation signature once one exists (§3.4 step 5). `database_uuid` is an **accounting label, never a credential** — it is client-chosen and world-readable to any logged-in Odoo user via `/web/session/account` (brief). It follows, and revision 1 did not say so, that **the activation limit counts honest installations and does not constrain a thief at all**: one attacker holding a stolen key picks one uuid and reuses it for ever, refreshing an existing row, consuming no further slot, downloading without limit, leaving only a changing `last_ip` in a table nobody watches. The limit is a billing and support control. §5 T11 is corrected to match.
- **Rate limits.** Two tiers, in `app/Providers/AppServiceProvider.php`:
  - `odoo-store-pre` — **60/min per IP**, route middleware, applied *before* the controller and therefore before any `sodium_crypto_sign_verify_detached`. Its only job is to bound signature work by an unauthenticated caller.
  - Per-licence limits applied **inside the controller, after verification succeeds**, via `RateLimiter::attempt()` keyed on the verified `payload.licence_id`: `odoo-catalogue` 6/min, `odoo-archive` 60/min (a full install is ≤ 26 archives), plus 120/min per IP. Verify first, then throttle — the key must be something the caller cannot choose.

  Revision 1 keyed both per-licence limits on `sha256(whitespace-stripped licence)`, an unauthenticated, attacker-chosen field, which is the same defect that is live today at `app/Providers/AppServiceProvider.php:19-25` for the MyERP `license-api` limiter (repo, re-read: `$key = $request->input('license_key')`). The MyERP limiter is **not** changed in v1 — §3.1's rule is that no MyERP code path is touched — and it is recorded as an accepted, tracked defect in §3.8 rather than quietly inherited.

  Limiter exceptions render as JSON 429 through the existing API exception rendering (`bootstrap/app.php:20-22`). `bootstrap/app.php` also gains `trustProxies(at: '127.0.0.1')`, without which every per-IP limit collapses onto nginx.
- **Storage:** `storage/app/private/odoo-releases/19.0/<serial>/` on the `local` disk, not public, no signed-URL route, no web upload. About 10.4 MB per full release set (brief).
- **Admin is artisan only** (`app/Console/Commands/Odoo/`): `odoo:licence:register {--file=} {--replace} {--reason=}`, `odoo:licence:status {licence_id} {--suspend|--revoke|--activate} {--reason=}`, `odoo:release:import {dir} {--publish}`, `odoo:release:withdraw {serial}`, `odoo:release:list`, `odoo:activations {licence_id?}`, `odoo:activation:release {licence_id} {database_uuid} {--reason=}`. The importer verifies the keyring against `root_public_keys` and the index against the keyring before touching the disk, refuses `serial ≤` the highest imported serial, and checks every archive's sha256 and size. Publish flow: `scp -r dist/releases/19.0/3 deploy@store.hushmand.tech:/srv/odoo-releases-inbox/` then `php artisan odoo:release:import /srv/odoo-releases-inbox/3 --publish`.
- **Portal:** nothing new in v1. The existing portal cannot import, publish or withdraw an Odoo release — that needs an offline signature.

### 3.7 `database.uuid` binding and restore-to-staging

Binding exists **only at the online layer** (activation slots and downloads). The offline hm_license gate stays unbound, so a ministry restoring after a disaster with no internet keeps working.

| Event (brief: `service/db.py`) | `database.uuid` | Server effect | hm_store effect |
|---|---|---|---|
| Duplicate in the DB manager, or restore "as copy" (`copy=True`, `db.py:185-205, 372-374`) | new | counts as a new activation; `activation_limit` when full | if `odoo neutralize` was run, the store is disabled in that copy |
| Restore "moved" / `pg_restore` outside Odoo | kept | same activation, no new slot | works, same entitlement |
| Neutralized copy | new or kept | none — the store never calls | `data/neutralize.sql` sets `hm_store.neutralized=1`; Odoo runs `<module>/data/neutralize.sql` for installed modules (brief: `modules/neutralize.py:18-33`) |
| Migration to new hardware, restored as copy | new | may hit the limit → vendor runs `odoo:activation:release` | message: "This database looks like a new installation (a copy or restore). Your licence allows 2 databases. Ask Hushmand to release an old one." |
| A `group_system` user edits the System Parameter | changed | looks like a new database | same as above |

`addons/hm_store/data/neutralize.sql`:

```sql
INSERT INTO ir_config_parameter (key, value, create_date, write_date)
VALUES ('hm_store.neutralized', '1', now() at time zone 'UTC', now() at time zone 'UTC')
ON CONFLICT (key) DO UPDATE SET value = '1';
```

The exact column requirements of `ir_config_parameter` for a raw insert are **settled** (container r3): only `key` and `value` are NOT NULL, `id` defaults from `ir_config_parameter_id_seq`, and `ir_config_parameter_key_uniq` is UNIQUE on `(key)`, so `ON CONFLICT (key) DO UPDATE` is valid as written. S4 still runs a real `odoo neutralize` against a copy, as an end-to-end check rather than to answer the question.

### 3.8 Server hygiene required before any customer licence reaches the server

This does not stop remote code execution — K_release does — but the server will now hold every customer's licence blob and database identifier.

| Item | Files |
|---|---|
| Remove the committed default admin password **from the working tree and from history**, and rotate it in production to a value that has never been in the repo. `git grep` searches the checkout, not the history: the constant is live at `app/Support/LicenseDefaults.php:9` and is in every existing clone, every deployed vendor directory, and any row a seeder created. Either rewrite history (`git filter-repo`, force-push, every clone re-cloned) or write a dated accepted-risk note in `docs/AUDIT-2026-09.md` naming who holds a clone — S2 acceptance (a) now forces the choice | `app/Support/LicenseDefaults.php:7-9`, `.env.example:11-12`, `check-admin.php`, `artisan-check-login.php` (delete the last two), git history |
| `.env.example` ships `APP_DEBUG=true` twice (`:4`, `:16`) and an empty `LICENSE_SIGNING_SECRET=` (`:9`) — the exact input to the seeder-silently-generates path this section already flags | `.env.example` |
| **Accepted, not fixed in v1:** the MyERP `license-api` limiter keys on unverified request input (`app/Providers/AppServiceProvider.php:19-25`). Same defect class as the one §3.6 fixes for the Odoo routes; changing it touches a MyERP code path, which §3.1 forbids in v1. Record it in `docs/AUDIT-2026-09.md` with an owner and a date | `app/Providers/AppServiceProvider.php` |
| Seeder must stop rewriting admin credentials and must never silently generate a signing secret | `database/seeders/ApplicationBootstrapSeeder.php:25-34` |
| `license:admin:ensure` must require `--password` and stop writing `.env` | `app/Console/Commands/LicenseEnsureAdminCommand.php:21-32` |
| `APP_DEBUG=false`, `SESSION_SECURE_COOKIE=true` | production `.env`, `docs/DEPLOY.md` |
| HTTPS on 443 with HSTS; HTTP 301s; `APP_URL`/`LICENSE_ISSUER` switched to https | `docs/nginx-https.conf.example` (restore), `docs/DEPLOY.md:32,58-59` |
| nginx IP allowlist on `/login` and the portal routes | `docs/nginx-https.conf.example` |
| Baseline green tests | `tests/Feature/ExampleTest.php` (expects 200, gets 302 today) |

---

## 4. Release pipeline — `hushmand-odoo/tools`

### 4.1 Keys — `tools/release_signing.py` (new)

- `--generate-root`, `--generate-release` and `--generate-licence` write PKCS8 PEMs with `BestAvailableEncryption(getpass())`, `chmod 600`, refusing to overwrite; they print `key_id` (`root-YYYY`, `rel-YYYY-MM`, `lic-YYYY-MM`), the raw 32-byte public key as base64, and — for a root key — the **fingerprint**: `sha256(raw public key)` rendered as 8 groups of 4 uppercase hex, with a 6-word mnemonic underneath for reading aloud on the phone. `cryptography` is imported lazily, as `issue_license.py:34-53` already does.
- `sign(body_bytes, key, key_id, prefix) -> {"key_id","sig"}` and `verify(...)`, for all four domain prefixes.
- `keyring --add <key_id> --role release --pub <b64> --revoke <key_id> --serial N --sign-with root.pem` writes `keyring.json` + `keyring.sig`. `--serial` must be strictly greater than the ledger's last keyring serial; the tool refuses otherwise, and refuses to emit a keyring that drops a `revoked_key_ids` entry present in the previous one (the client enforces this too, §2.8a, but the vendor should not be able to make the mistake in the first place).
- `sign-release --request SIGN-REQUEST.json` and `sign-bootstrap --zip … --out ….rootsig` and `sign-trust-update --file …` — the three signing verbs. **They run on C1b only, and none of them has a `--yes`** (§4.2b).
- **Pinning:** K_root's public key goes into `addons/hm_store/lib/trust.py` `ROOT_KEYS` and into `config/odoo_store.php`; on a customer's machine the copy that is actually used is the root pin C13. K_release lives only in the keyring, so rotating it is a keyring bump, not an hm_store reinstall.

**K_licence must be re-keyed, and it is the first thing that happens (S5a).** Today `tools/issue_license.py:74` writes the licence signing key with `serialization.NoEncryption()` and `:101` loads it with `password=None`, at `:56` `~/.hushmand/licence_signing_key.pem` — the same directory revision 1 chose for `K_release`. One laptop compromise therefore yields both RCE on every customer (K_release) and the power to mint any licence (K_licence), which is exactly the forgery §3.4 step 3 now refuses — but D9's "flip `require_registration` within the first month" gave that forgery a month of free rein, and §3.4 without step 3 gave it free rein for ever. D6's "never in one backup with K_licence" addressed backups and not the live filesystem.

The work, all in S5a:

1. `tools/release_signing.py --generate-licence` creates `lic-2026-11` with `BestAvailableEncryption(getpass())`.
2. `issue_license.py::load_private_key` gains a passphrase path (`--passphrase-file`, else `getpass()`), and `generate_keys` is changed to `BestAvailableEncryption` so the plaintext form cannot be recreated.
3. Re-issue every outstanding licence under the new key. **Do this before the first sale** (D18); afterwards it costs one reissue and one paste per customer, and the price rises with every licence sold.
4. Rotate the public half: `VENDOR_PUBLIC_KEY` at `hm_license.py:56` becomes `VENDOR_PUBLIC_KEYS`, a map, shipped in an `hm_license` release; `config/odoo_store.php` `licence_public_keys` gains `lic-2026-11`.
5. Remove the old id from both maps once no outstanding licence uses it, and record the date.

Until step 5 lands, **T24 and D9 offer no protection and the spec says so**: `require_registration` is `true` from the first sale (D9, changed), and §3.4 step 3's row comparison — not registration alone — is what a leaked K_licence actually runs into.

### 4.2 Building and signing a release — two machines, two commands

Revision 1 had one command on one host it called an "offline release station", and then required that host to run `gh run list --commit <sha>` against GitHub and to hold a fetched git tag — a networked signing host, which is the concrete precondition for the K_release theft that the other findings make unrecoverable. Worse, its one human checkpoint, the typed `sign release 3` after the per-module diff sheet, could be skipped with `--yes`, so a compromised build script could produce a signature over arbitrary content in silence. D8 forbade an override on the *automatic* CI check and left one on the *human* review, which is backwards.

The pipeline is therefore split. **C1a (online) assembles bytes and produces no signature. C1b (air-gapped) sees only hashes and produces only signatures.** A USB stick carries a small JSON file each way.

#### 4.2a `tools/build_release.py stage` — on C1a, online, no key present

```
python tools/build_release.py stage --serial 3 --tag odoo-r3 \
    --keyring dist/keyring.json --out dist/releases/19.0/3
```

1. Refuse if `git status --porcelain` is non-empty, if `odoo-r3` does not exist or does not equal `HEAD`, if CI is not green for that commit (`gh run list --commit <sha> --json conclusion,databaseId,headSha`), or if `serial ≤` the ledger's last serial.
2. `git worktree add --detach <tmp> odoo-r3`; every later step reads only `<tmp>`, so untracked files cannot ship (today `files_for` uses `rglob` over the working tree, `build_release.py:207-212`). Remove the worktree at the end.
3. Per module: the existing guards (`check_licence_key_is_real`, `check_licence_permits_sale`, `check_module_is_gated`) plus new release guards — name matches `^(hm|af)_[a-z0-9_]{1,60}$`; `auto_install` falsy; `installable` not False; `license == "OPL-1"`; version starts `19.0.`; every path matches `PATH_RE`; no symlinks; no `.pyc`/`__pycache__`; ≤ 5,000 files and ≤ 100 MiB uncompressed. And, for hm_store: **the `addons/hm_store/lib/trust.py` in `<tmp>` must pin a non-placeholder `ROOT_KEYS` whose hash matches the keyring's root set, `MIN_KEYRING_SERIAL` must equal the serial of the keyring being shipped and be ≥ the previous release's, and `ROOT_THRESHOLD` must be ≤ `len(ROOT_KEYS)`** — so a release can never ship an hm_store that cannot verify the next one, and never one that lowers a customer's keyring floor.

   **This guard is not a security control against a stolen K_release.** It runs on the vendor's own builder and an attacker holding the signing key simply does not run it. The control that matters is client-side: §2.10 rule 7, which refuses the staged tree before the swap. This step exists to stop the vendor shipping a brick by mistake, and §5 T16 is worded accordingly.
4. **Deterministic zips:** sorted entries, no directory entries, `ZipInfo(date_time=(1980,1,1,0,0,0))`, `external_attr = 0o100644 << 16`, `create_system = 3`, `ZIP_DEFLATED` at `compresslevel=9`, no comment. Named `<module>-<version>.zip`. Two builds of one tag must be byte-identical.
5. Per-file `(path, sha256, size)`; `tree_sha256 = sha256(b"".join(f"{p}\0{h}\0{s}\n".encode() for p,h,s in sorted(files)))`.
6. **Version rules against `releases/19.0/ledger.json`:** tree changed and version not strictly greater → refuse ("bump `addons/hm_payroll/__manifest__.py`"); version lower → refuse; module removed → allowed and printed.
7. Write `release.json` as `json.dumps(index, sort_keys=True, indent=1, ensure_ascii=True) + "\n"`, with `created_at` = the tag commit's committer time in UTC, so a rebuild is byte-identical.
8. Write **`SIGN-REQUEST.json`** — the only thing that crosses to C1b. It is small (a few KiB) and carries no archive bytes: `{"_type": "hushmand-sign-request", "serial": 3, "series": "19.0", "git_commit": "<40 hex>", "release_json_sha256": "<64 hex>", "release_json_b64": "<the exact bytes>", "ci": {"run_id": …, "conclusion": "success", "head_sha": "<40 hex>"}, "review": [{"module": "hm_payroll", "from": "19.0.1.0.1", "to": "19.0.1.0.2", "files_changed": 7, "bytes": 2712345, "new_depends": [], "diffstat": "…"}], "trust_update": {…} | null}`. Also write `REVIEW.txt`, the same sheet in human form, and `SHA256SUMS` (informational only — unsigned, nothing trusts it).
9. `stage` **stops here. It never touches a private key and never writes a `.sig`.** Its exit line is: "Carry `SIGN-REQUEST.json` to the signer. Nothing is signed yet."

`--yes` exists on `stage`, which produces no signature, and nowhere else.

#### 4.2b `release_signing.py sign-release` — on C1b, air-gapped, key present

```
python tools/release_signing.py sign-release --request /media/usb/SIGN-REQUEST.json \
    --key ~/.hushmand/release_signing_key.pem --key-id rel-2026-10 --out /media/usb/
```

1. Refuse if the request's `_type`, `schema`, `series` or `serial` is wrong, if `serial ≤` the **signer's own** ledger copy (C1b's copy is authoritative, C4 is informational), or if `sha256(release_json_b64 decoded)` ≠ `release_json_sha256`.
2. Refuse if the `ci` block is absent, `conclusion != "success"`, or `head_sha != git_commit`. D8's rule survives the split: the check now runs on C1a, where the network is, and the **attestation** is what crosses; the signer refuses a request that does not carry one. There is no override flag, on either half.
3. Print the review sheet from `review[]` — changed modules, old → new versions, sizes, diffstat, any new dependency, and in red any `trust_update` — and require the typed confirmation `sign release 3`. **There is no `--yes`, no `--batch`, no environment variable, and no config file that can supply this string.** `--dry-run` prints the sheet and exits without touching the key; that is the only non-interactive mode.
4. Sign `b"hushmand-release-v1\n" + release_json_bytes` → `release.sig`. If the request carries a `trust_update`, prompt separately — a second typed confirmation naming the key ids being added — and sign `b"hushmand-trust-update-v1\n" + canonical(trust_update)` with **K_root** → `release.root.sig`. Append to the signer's ledger.
5. Carry `release.sig` (and `release.root.sig`) back to C1a; `build_release.py assemble --out dist/releases/19.0/3` drops them in beside the archives, copies in `keyring.json`/`keyring.sig`, re-verifies the whole set with `lib/verify.py`, and appends to the committed ledger C4.

**This makes the first release materially harder to build, and that is the point.** Revision 1's single command was one `python …` on a laptop that was already online. The new flow is: run `stage` on C1a; copy one JSON to a USB stick; boot or walk to C1b; type a confirmation after reading a diff sheet; copy two `.sig` files back; run `assemble`. Fifteen minutes and a stick, per release. It is placed in the build order at **S5b**, after S5a's key custody and before S10 publishes anything, so the cost lands before the first customer rather than after. D19 records the one concession a solo vendor gets: C1b may be the same physical laptop booted from a separate, offline live-USB with the key USB attached — not the same running OS, not "with Wi-Fi turned off in the menu bar".

**`release.json`** (one module shown):

```json
{
 "created_at": "2026-10-01T09:00:00Z",
 "git_commit": "<40 hex>",
 "key_id": "rel-2026-10",
 "modules": {
  "hm_payroll": {
   "archive": {"file": "hm_payroll-19.0.1.0.2.zip", "sha256": "<64 hex>", "size": 2712345},
   "depends": ["hm_license", "hr"],
   "external_python": [],
   "files": [["hm_payroll/__init__.py", "<64 hex>", 118], ["hm_payroll/__manifest__.py", "<64 hex>", 2210]],
   "name": "Payroll", "summary": "…",
   "tree_sha256": "<64 hex>", "version": "19.0.1.0.2"
  }
 },
 "product": "hushmand-odoo",
 "schema": 1,
 "serial": 3,
 "series": "19.0",
 "_type": "hushmand-release"
}
```

`release.sig`: `{"key_id":"rel-2026-10","sig":"<base64 Ed25519 over b'hushmand-release-v1\n' + release.json bytes>"}`.
`release.root.sig` (only when the release changes the root pin): `{"key_id":"root-2026","sig":"<base64 Ed25519 over b'hushmand-trust-update-v1\n' + canonical trust_update bytes>","trust_update":{…}}`.

### 4.3 Other subcommands

- `bootstrap --release dist/releases/19.0/3` (C1a) → `hm_store-bootstrap-r3.zip` containing exactly the `hm_license` and `hm_store` trees from the signed index, plus `verify_bootstrap.py` and a `BOOTSTRAP.txt` naming the release serial, the keyring serial, the K_root `key_id` and its fingerprint. It prints the zip's SHA-256 **for the vendor's own records only** and says in as many words: "this hash is not a trust anchor; the customer must verify the signature."
  Then, on **C1b**: `release_signing.py sign-bootstrap --zip hm_store-bootstrap-r3.zip --key root.pem --out hm_store-bootstrap-r3.zip.rootsig`, which signs `b"hushmand-bootstrap-v1\n" + zip bytes` with **K_root** and embeds the raw public key and its fingerprint in the `.rootsig` so `verify_bootstrap.py` has something to check against the operator's typed fingerprint.

  **Why a signature and not a hash.** Revision 1 rooted every new installation in a SHA-256 sent in the licence email, with the zip on an unnamed vendor HTTPS host, and called it "two channels". Both channels are vendor infrastructure; neither was required to be separate from `store.hushmand.tech` or `license.hushmand.tech`; nothing required DKIM or DNSSEC; and the K_root fingerprint was published nowhere an operator could check independently. Anyone who compromised vendor mail *or* the vendor web host substituted the bootstrap and owned every subsequent install, with no key theft at all — so invariant 1 was simply false for the install path. A K_root signature moves the secret off the wire entirely: the attacker must have K_root, which lives on paper and two encrypted USBs, or must corrupt the fingerprint in the customer's signed contract. §5 T25 records the case that revision 1's threat table did not contain.
- `bundle --release dist/releases/19.0/3 --licence <key file> --out …` → the offline `.hmpkg` (§6), containing `payload.modules ∪ {hm_license, hm_store}`.

### 4.4 Versioning

- **Catalogue serial:** a monotonic integer per series, git tag `odoo-r<serial>`. `CATALOGUE_VERSION` (`build_release.py:44`) is untouched and still names the suite zips.
- **Module version:** every content change bumps the manifest version, enforced at §4.2a step 6. Reconcile (§2.11) and Odoo's migration rule — scripts run only when `installed < script_version <= current` (brief: `migration.py:195-208`) — both depend on it.
- **Release r1 bumps every module to at least `19.0.1.0.1`**, so that taking over a legacy `19.0.1.0.0` copy in `/mnt/extra-addons` changes `latest_version` and the upgrade can be proven to have run. All 21 module manifests are `19.0.1.0.0` today (repo: 21 directories under `addons/`).

### 4.5 Rollback

- **Vendor side: roll forward only.** A bad release not yet installed anywhere → `odoo:release:withdraw N`. Already installed → publish `N+1` with the previous code under **bumped** versions. The client floor makes a published downgrade impossible by construction, and Odoo has no downgrade guard of its own (brief).
- **Customer side, failed apply:** `ops/<op>/backup/`, `ROLLBACK.txt`, `lib/rescue.py`, and the `pg_dump` taken before the swap. There is no downgrade button in the store UI in v1.

### 4.6 CI

`tier0` picks up `tools/tests/test_release.py` (ephemeral keys, a temporary git repo fixture) through the existing `unittest discover tools/tests`, plus the new `addons/hm_store/lib` step. The `odoo` job gains hm_store. A new `store-e2e` job runs `tools/store_e2e.py` against a fake store server (`tools/tests/fake_store_server.py`) with throwaway keys, in threaded and prefork modes. **No private key ever exists on GitHub**; signing happens only on C1b. A tier0 test asserts that no module under `tools/` reachable from `stage` imports `release_signing`'s signing verbs, so the two halves cannot silently recombine.

---

## 5. Security controls mapped to threats

| # | Threat | Control | Where |
|---|---|---|---|
| T1 | Licence server compromised (DB, `.env`, TLS, DNS, portal) pushes malicious code | Code is authorised only by offline K_release under a root-pinned keyring; the server signs nothing hm_store trusts; public keys never come from `/health` | `addons/hm_store/lib/trust.py`, `lib/verify.py` |
| T2 | Build/repo compromise; dirty tree or untracked files signed; a compromised build script signing arbitrary content | Build from a verified tag through `git worktree`; refuse dirty trees, symlinks, `.pyc`; CI-green check whose attestation travels to the signer; reproducible zips so a second machine can re-derive the hashes; and the split itself — **the host that assembles bytes holds no key, and the host that holds the key sees only hashes and a review sheet and requires a typed confirmation with no `--yes` anywhere** | `build_release.py stage`, `release_signing.py sign-release`, D8, D19 |
| T3 | K_release theft | Passphrase-encrypted PEM on the **air-gapped** signer C1b, never on a host that runs `gh`, `git fetch` or a browser (D6, D19); never in the same backup as K_licence; **rotation without reinstall** via a root-signed keyring with a higher serial and `revoked_key_ids` — which is only a real recovery because the client now has a **persisted keyring floor and a sticky revocation set** (T26), and because a stolen key cannot rewrite the root pin (T27) | `tools/release_signing.py keyring`, §2.8a, §2.10 rule 7 |
| T4 | MITM, DNS hijack, TLS-inspecting proxy | Integrity comes from signature + hash, never TLS; `verify=True` with no switch; `allow_redirects=False`; https-only constant URL; on TLS failure the UI points at the offline bundle. **Availability too, not only integrity:** the response body is bounded before it is parsed (T30) and staleness is visible (T28) | `lib/client.py`, §2.8 step 1, §2.7 step 0 |
| T5 | Malicious zip: traversal, symlink, bomb, duplicates, parser differentials | Hash and signature **before** `zipfile` opens it; exact signed file set; per-file size and hash; `O_EXCL\|O_NOFOLLOW`; no `extractall`; entry/size/ratio caps | `lib/unpack.py` |
| T6 | Mix-and-match: a valid archive for another module or series | The index binds product, series, module, version, sha256 and size; the staged manifest's version is re-checked | `lib/verify.py`, `lib/unpack.py` |
| T7 | Downgrade or replay of an older signed release | Floor in `state.json` **and** the DB (higher wins); `serial < floor` refused with an explicit replay warning; mandatory version bump | `lib/plan.py`, `lib/fsops.py` |
| T8 | A module name shadowing core or a customer's module | `^(hm\|af)_…` regex; names present in the core addons dir refused; takeover of another addons path needs an explicit acknowledgement; locations probed with `isdir`, never through the Manifest API | `lib/plan.py` |
| T9 | Unauthorised trigger: `group_erp_manager`, backend XSS, API key, CSRF, cron | `is_system() and is_admin()`, never `sudo`; `@check_identity`; a **closed path allowlist** (`call_button` for apply, `call_kw` for reads) with every mutating entry point built as a `type="object"` button so it lands on the strict path; `/jsonrpc` and `/xmlrpc` cannot reach these methods because `dispatch_rpc` pops the request (`http.py:444`); **no HTTP route at all**; the cron has its own `kind='cron'` door that reaches neither the import path nor `ir.module.module` nor `server.restart()` | §2.4, §2.5, `models/*`, `wizard/*` |
| T10 | An admin of database A changes code that database B runs | `hm_store_database` opt-in in `odoo.conf`; updates refused when another database on the server has the module installed; the restart confirmation names every database affected | preflight 1, `lib/plan.py` step 7 |
| T11 | Licence key theft (every internal user can read it today) | `groups="base.group_system"` on `hm.license.key`; never logged, never in the support file, sent only over TLS to the pinned host; **revocation** (`odoo:licence:status --revoke`) is the real control; **installation binding** — a keypair generated on first use, pinned server-side per (`licence_id`, `database_uuid`), signing every later request — raises theft from "read one text field" to "exfiltrate the data directory"; plus detection (ASN change, download-count anomaly) and the event log. **The activation limit is explicitly *not* listed here:** `database_uuid` is client-chosen, so a thief reuses one uuid for ever and consumes no slot. It is a billing control | `hm_license.py:82-87`, §3.4 step 5, `lib/instkey.py` |
| T12 | Stored XSS or phishing text injected by the server | The server has no free-text field; codes map to local strings; index text lands only in escaped Char/Text; no Html field, `t-out` or `Markup`; a test scans the view arch | `lib/client.py`, views, `tests/test_access.py` |
| T13 | Half-applied update, mixed code across workers | Restart-only apply; swap **before** marking; `LOCK ir_module_module` + `ir_cron FOR UPDATE` + `flock`; reconcile against a **boot marker**, not against `base.partially_updated_database`, which `loading.py:599-607` re-inserts after a successful load that left work pending; `ROLLBACK.txt`; `lib/rescue.py`. **Mixed code is reduced, not eliminated** (invariant 3): a prefork graceful reload overlaps generations by design for up to 60 s (`server.py:1105-1134`), the operator is offered `hard`/`operator` restarts that do not, and the **stale-worker guard** makes any surviving old worker refuse hm_store calls | §2.9 G/I, §2.11 |
| T14 | Staged files altered between verify and apply | Staging inside a `0700` work dir; full re-hash against the signed index at apply time | §2.9 A |
| T15 | Licence coverage bypassed by editing stored `modules` (audit L2) | hm_store re-decodes and re-verifies `key` on every use and never reads stored payload fields; hm_license L2 fix re-verifies on payload writes | §2.7 step 5, §2.14 |
| T16 | A release that ships an hm_store which cannot verify the next one, or a placeholder key | Builder refuses unless the shipped `trust.py` pins the keyring's root set and `MIN_KEYRING_SERIAL` matches. **Vendor-mistake guard only** — it runs on the vendor's builder, so it is worth nothing against someone holding K_release; T27 is the control for that | §4.2a step 3 |
| T17 | Malicious or missing pip dependency | Never installed; `external_python` must match the signed manifest and be importable, else the plan blocks | `lib/plan.py` |
| T18 | Server admin takeover through the committed default password | S2 hygiene: rotate, remove from four tracked files, stop the seeders, IP allowlist, `APP_DEBUG=false` | §3.8 |
| T19 | Neutralized or staging copy acting as production | `data/neutralize.sql` disables the store; a copy's new uuid consumes a slot and is visible to the vendor | §3.7 |
| T20 | Tampered installed tree, planted `.pyc` | Weekly integrity check of the installed tree against the signed per-file hashes, flagging extras including `__pycache__/*.pyc`; alerts, never auto-repair | cron, §2.12 |
| T21 | The operator loses the shell and the update has half-run | `ROLLBACK.txt` and `lib/rescue.py`, both usable without a working Odoo; the pre-apply `pg_dump`; the mandatory Test restart before the update path is allowed, which since revision 3 also proves the boot marker commits (§2.6 checks 11 and 20) | §2.6 checks 11/20, §2.8, §7 |
| T22 | Audit trail erased by whoever broke in | Four sinks: read-only model, server log, append-only `audit.log` outside the DB, server-side `odoo_store_events` | §2.12 |
| T23 | Making the addons dir writable widens the blast radius | Only the data dir is writable; core and `/mnt/extra-addons` stay read-only; hm_store never chmods, so the opt-in is the operator's; the verifier is one small fail-closed file with negative test vectors. **The opt-in is now checked by mode bits, not by `os.access`** (revision 3): `os.access(..., W_OK)` is evaluated with the real uid and a root process bypasses DAC mode checks entirely, so on any deployment running Odoo as root — a `docker run` without `--user`, a systemd unit without `User=` — revision 2's check 5 went green against the untouched `0500` directory and the operator's one deliberate command was never performed and never shown. Check 5 now refuses outright when `os.geteuid() == 0`, requires `S_IMODE & 0o200` on a directory the Odoo uid owns, and the euid is printed on the Status page and written to `audit.log` | §2.6 check 5, §2.12, `lib/verify.py` |
| T24 | Forged licences if K_licence ever leaks | Three layers, because registration alone was never enough: K_licence is **passphrase-encrypted and re-keyed** (S5a) — revision 1 left it in plaintext at `issue_license.py:74`; `require_registration = true` from the first sale refuses an unregistered `licence_id`; and **§3.4 step 3 refuses a signed payload that diverges from the registered row**, which is what catches the realistic forgery — a known, registered `licence_id` (they are not secret) carrying `modules` = everything and `expires` = 2099 | §4.1, §3.4 steps 2–4 |
| **T25** | **Vendor mail or the bootstrap download host is compromised and the bootstrap zip is substituted** — no key theft needed, and revision 1's threat table did not contain this case | The bootstrap zip is signed by **K_root**; the operator verifies the signature against a fingerprint from a channel the vendor does not control end to end (signed contract, quote PDF, printed card, phone), never from the download page or the email; the bootstrap host C14 shares no DNS zone, TLS key, hosting account or credential with C8/C9 (D16); the Status page re-prints the pin fingerprint for later comparison | §1.5 step 1, §4.3, D16 |
| **T26** | **Keyring replay: an old, validly-signed keyring is served to re-admit a revoked or stolen K_release** — by a compromised store, a MITM, or anyone who can bind the loopback override host | Persisted `keyring_serial` floor in `state.json` **and** on operation rows, highest wins, pre-seeded from `trust.MIN_KEYRING_SERIAL` so a fresh install has a floor immediately; a keyring below the floor is refused **before the release index is parsed at all**; the revocation set is a **union** over every keyring ever seen, so no later document can un-revoke a key | §2.8a |
| **T27** | **A release signed with a stolen K_release ships an `hm_store` whose `lib/trust.py` pins the attacker's roots**, permanently cutting K_root out of that customer | The root pin C13 lives **outside** the tree the store swaps; §2.10 rule 7 parses the staged `trust.py` with `literal_eval` and refuses any change to the root set, threshold, domain prefixes or store host unless the release carries a **K_root-signed `trust_update`** bound to that exact `tree_sha256`; root keys can be added by such an update, never removed; preflight 18 refuses to run at all if the pin and the running code disagree; hm_store updates alone so a refusal leaves everything else untouched | §2.10 rule 7, §2.6 check 18, §2.7 step 6a |
| **T28** | **A held or MITM'd store silently starves a customer of security updates** while "Check for updates" reports "up to date" for ever | Freshness on the **online** path, not only for offline media: warn at 45 days and again in red at 180, on the signed `created_at` and on the time since the last successful catalogue call; the clock reference only ratchets forward; the check-and-notify cron repeats it | §2.7 step 0, D13, D17 |
| **T29** | **Unauthenticated abuse of an hm_store route**: DoS amplification and a database-name oracle | **There is no hm_store route.** Revision 2's `auth='none'` status route was removed in revision 3 (§2.4): it could not observe a restart (a runtime-installed module cannot own a nodb route, `http.py:2758-2768`; a db-bound request is itself what loads the registry, `http.py:2849-2852`), and a 3-second unauthenticated poll was a way to make the server SIGHUP itself mid-upgrade (`server.py:503-524`, `732-751`). Progress is now a static-asset liveness probe — served by `_serve_static` before `request.db` is consulted (`http.py:2852-2854`), no registry, no cursor — plus exactly one authenticated `call_kw`. This closes T29 by deletion rather than by mitigation. Odoo's own "any request can name any database" behaviour remains, and preflight 16 still warns about it, because it is not hm_store's to fix | §2.4, §2.6 check 16 |
| **T30** | **An uncapped catalogue response body**, reachable by a network attacker before any signature is checked, including a gzip bomb | `Content-Length` refused above 4 MiB; bounded `iter_content` read with a hard ceiling on **decompressed** bytes; `Accept-Encoding: identity`; `response.json()`/`.text`/`.content` never called, enforced by a lint test; archives additionally refused when `Content-Length` exceeds the signed size | §2.8 step 1 |

**Deferred, because none of them prevents remote code execution** (the signature and the floors already do): server-signed freshness (`K_ts` — reconsidered in D17 now that the keyring floor exists, and deferred to v1.1 rather than dismissed); signed yank/revocation lists inside releases; a root-privileged apply helper; TOTP on the portal (the nginx IP allowlist stands in). **No longer deferred:** installation keypairs and proof-of-possession, which moved into v1 in a reduced form (§3.4 step 5) — the "does not prevent RCE" rationale was true and was answering the wrong question, since T11 is about key theft, not code execution.

---

## 6. Offline fallback

**Format:** `hushmand-19.0-r<serial>-<licence_id8>.hmpkg`, a flat zip with STORED entries only:

```
keyring.json   keyring.sig
release.json   release.sig
archives/<module>-<version>.zip      # licensed modules + hm_license + hm_store
```

**Flow** (`wizard/hm_store_offline_wizard.py`):

1. Settings → Hushmand Store → **Offline install** → choose the file. The upload is a Binary field over JSON-RPC, so CSRF does not apply; Odoo's request cap is 128 MiB (brief: `http.py:247`) and the web client's limit is `web.max_file_upload_size` (brief: `web/models/ir_http.py:91-94`). A full catalogue is ~10.4 MB.
2. Guard and preflight, exactly as online, minus the network checks.
3. Write to `ops/<op>/upload.hmpkg` with a 64 MiB cap.
4. **The outer container is never trusted** — it is only split: names must match `^(keyring\.(json|sig)|release\.(json|sig)|release\.root\.sig|archives/[a-z0-9_]+-19\.0\.[0-9.]+\.zip)$`; no duplicates; STORED only; per-entry caps. `keyring.json`/`release.json` are verified **first**; each inner archive is then copied out with a cap of its signed size and hashed before anything opens it.
5. **Both floors apply, identically to the online path.** The keyring goes through §2.8a in full — an old `.hmpkg` is the easiest keyring replay there is, and it is the same check on the same persisted value — and the release floor applies unchanged. Entitlement comes from the licences in the database (hm_license, fully offline). Freshness uses the same `FRESH_WARN_DAYS`/`FRESH_STALE_DAYS` constants as §2.7 step 0: `created_at` older than 180 days shows "This bundle is old; security fixes may be missing" — a warning, never a block, because clocks and delivery schedules in the field are unreliable.
6. From there the pipeline is identical: plan → unpack → backup → apply → restart → reconcile. The operation records `source = offline`.
7. **Checking media before it reaches the server:** `python3 -m hm_store.lib.verify <bundle.hmpkg>` runs on any machine with Python 3.8+ and `cryptography`, because `lib/` never imports Odoo. It prints module, version, serial and key ids, or the failure reason.

Not in v1: offline activation receipts (there is no server binding offline, and the activation count is accounting, not DRM).

---

## 7. Failure modes and recovery

| Failure | Detected by | State | What the admin sees and does |
|---|---|---|---|
| Data dir read-only | preflight 5 | nothing changed | The chmod message with resolved paths and both commands; **Check again** |
| Opt-in missing, `--dev=reload`, not POSIX, neutralized | preflight 1/3/2/13 | nothing | the specific message and its fix |
| **An `hm_`/`af_` module was installed through Apps → Import Module** | preflight 8 | nothing | **The recovery path, written out because revision 2 blocked the whole store on this and documented no way out** — and it is exactly the thing the goal statement says a customer will have tried first. The message names each offending module and gives the steps: (1) Apps → remove the **Apps** filter → search the module by its technical name → **Uninstall**; (2) if it is still listed, open it in developer mode and delete the `ir.module.module` row, or run `odoo -c <conf> -d <db> --stop-after-init` after deleting the folder from `addons_path`; (3) click **Check again**. The message also explains *why* it is invisible: `imported=True` modules are filtered out of the **load** domain (`base_import_module/models/ir_module.py:50-52` adds `('imported','=',False)` to the base `[('state','=','installed')]` at `base/models/ir_module.py:347-349`), not out of the Apps list, so the module appears installed and is silently never loaded. The same steps go into `docs/STORE-INSTALL.md` under "I already tried importing the zip". Blocking stays: a store-managed tree and an imported ghost of the same module is a state nothing can reason about |
| Test restart never run or failed | preflight 11 | nothing | "Run Test restart before updating." Failure means Odoo cannot restart itself here; the update path stays blocked and the docs give the manual restart route |
| TLS error, DNS failure, server down | `lib/client.py` | op `failed: store_unreachable` | "Cannot reach the Hushmand store securely. Check the proxy CA and the system clock, or use Offline install." No bypass exists |
| `licence_invalid` / `expired` / `revoked` / `not_registered` | server | op `failed` | local message, contact Hushmand |
| `activation_limit` | server | op `failed` | counts shown; vendor runs `odoo:activation:release` |
| Index or keyring signature invalid, schema error | `lib/verify.py` | op `failed` | SECURITY message, WARNING log, `request_id` to quote |
| Serial below floor | `lib/plan.py` | nothing | "The store offered an older release than the one installed (possible replay). Nothing was changed." |
| **Keyring serial below the keyring floor, or a keyring re-admitting a revoked key** | §2.8a steps 2–3 | op `failed: keyring_replayed` / `revoked_key_readmitted` | the SECURITY text of §2.8a; the release index in that response is never parsed; WARNING log, `request_id` to quote |
| **Staged hm_store changes the root pin without a K_root `trust_update`** | §2.10 rule 7 | op `failed: root_pin_change_refused`, staging deleted | "SECURITY: this update tried to change which Hushmand key the Store trusts, and it is not signed by Hushmand's root key. Nothing was changed. Contact Hushmand and quote `<request_id>`." |
| **Root pin and installed code disagree** | preflight 18 | every operation refused | the check 18 message; the operator re-installs from a bootstrap zip verified against the contract fingerprint (§1.5 step 1) |
| **Bootstrap signature does not verify, or the key does not match the typed fingerprint** | `verify_bootstrap.py` | nothing placed | one-line refusal naming which of the two failed; the runbook says **stop and phone Hushmand** — do not unzip, do not "try the other mirror" |
| **Store offered nothing new for a long time** | §2.7 step 0 | nothing | yellow at 45 days, red at 180: "Hushmand has not published a release in N days… your connection to Hushmand may be intercepted." Never blocking |
| **Catalogue response too large, or a decompression bomb** | §2.8 step 1 | op `failed: response_too_large` | "The Hushmand store sent an unexpectedly large reply. Nothing was changed." WARNING log |
| **Server refuses with `licence_mismatch`** | server, §3.4 step 3 | op `failed` | "Your licence does not match what Hushmand has on record. Contact Hushmand." The server side logs it as a probable forgery with the IP |
| **Server refuses with `installation_mismatch`** | server, §3.4 step 5 | op `failed` | "This database is already registered with a different Store installation. If you restored or moved this server, ask Hushmand to release the old registration." |
| **A `pg_dump` cannot be deleted at prune time** | §2.11 | op unchanged | WARNING log and a Status row naming the file, so an unencrypted full-database dump is never left behind silently |
| Download truncated, hash or size mismatch | `lib/unpack.py` | op `failed`, staging deleted | retry; nothing on the import path changed |
| Disk full | `OSError`, preflight 10 | op `failed`, staging deleted | free space and retry |
| `pg_dump` missing or fails | backup `.done` | op stays `verified` | tick "I have a backup made today", or install postgresql-client |
| Module used by another database | plan | nothing | names the database, gives the `-u … --stop-after-init` command |
| Missing Python dependency, or a core dependency unavailable | plan | nothing | names the library or Odoo module; hm_store never pip-installs |
| Exception in `button_install`/`button_upgrade` | §2.9 E | swap reversed, op `failed` | error text; nothing changed |
| Crash after swap, before commit | reconcile | `stalled` | **Resume**, or `ROLLBACK.txt` / `rescue.py rollback` |
| Restart never happened (supervisor, lost signal, `restart_method = operator`) | reconcile: **no boot since `applied_at`** (`boot_seq == boot_seq_at_apply`) | `awaiting_restart`, then `(overdue)` after 30 min | **Restart now**, or restart the service by hand — the flag makes the upgrade run at the next boot. This is the only state that offers a restart |
| Worker killed mid-upgrade (`limit_time_real`), threaded server re-exec'd itself mid-upgrade, or a module simply would not install | reconcile: **a boot happened** and targets are still pending — whether or not `base.partially_updated_database` is present, because `loading.py:599-607` re-inserts it after a successful load that left work pending | `stalled` | The CLI only: `odoo -c <conf> -d <db> -u … --stop-after-init`. **Restart now is deliberately not offered** — the same load would fail the same way, which is the loop revision 2's flag-based reconcile would have entered. **Resume** exists but is labelled "only after you have fixed the cause" and re-prompts for the password. Preflight 12 warned about the time limit beforehand, in threaded mode too |
| Two boots, no progress | reconcile: `boot_seq` advanced ≥ 2 since `applied_at`, targets unchanged | `stalled` | "Odoo has restarted twice and the upgrade has not moved. Do not restart again." Then the CLI and `ROLLBACK.txt` |
| Upgrade raises at boot | reconcile: a boot happened, versions not reached, `reset_modules_state` ran | `failed` | server-log traceback; `ROLLBACK.txt`; restore the `pg_dump` if the upgrade got partway (whether a failed module load's DB changes are rolled back is **UNVERIFIED**, settled in S8(3)) |
| **A worker of the previous generation is still serving** (prefork `graceful` only) | §2.9 I: the in-process hm_store build id ≠ `.hm_build_id` on disk | operation unchanged | "This Odoo worker is still running the previous version of Hushmand Store. Reload the page." The rest of Odoo keeps working; only hm_store's own surface refuses. If it persists past the graceful-reload window, the old workers are stuck and the fix is a full restart |
| Store UI unreachable after a failed upgrade | admin | n/a | `ROLLBACK.txt` at `<data_dir>/hm_store/ops/<op>/ROLLBACK.txt`, or `python3 <addons_data_dir>/hm_store/lib/rescue.py rollback --op HMS-…` |
| Files gone (non-persistent data dir) | red banner; Odoo logs "Some modules are not loaded" | n/a | restore the volume, or re-place the installed serial from a `.hmpkg` by hand and restart. In-app Repair is out of scope |
| hm_store's own update broke the store | admin | n/a | re-unzip `hm_store-bootstrap-r<N>.zip` into the data dir, then `-u hm_store --stop-after-init` |
| K_release compromised | vendor | n/a | On C1b: generate `rel-YYYY-MM` afresh, sign a keyring with K_root that **revokes the old id and raises `keyring_serial`**, re-sign the current release with the new key, publish. Customers pick it up on the next catalogue call — **no hm_store reinstall**. This works *only* because of the three revision-2 controls: the client's keyring floor refuses the pre-revocation keyring (T26), its revocation set is a union so nothing can un-revoke the stolen id, and the stolen key could not have rewritten the root pin in the meantime (T27). Customers who are offline or intercepted are reached by the offline `.hmpkg` and by the staleness warning (T28) telling them to call. **Residual, stated honestly:** a customer who applied a malicious release *before* the revocation has already run attacker code as the `odoo` user, and no key rotation undoes that — the recovery there is the `pg_dump`, a rebuild from a verified bootstrap, and a new licence |
| K_root compromised | vendor | n/a | There is no in-band recovery and the spec does not pretend otherwise: a new K_root is established by re-bootstrapping every installation by hand, with a **new fingerprint delivered on the out-of-band channels** (contract addendum, phone) exactly as at first install. This is why K_root lives on paper and two encrypted USBs in separate locations, is loaded only on the air-gapped C1b, and is used a handful of times a year (§1.2) |
| Two admins apply at once | `LOCK … NOWAIT` + `flock` | second refused | "Another store operation is running on this server." |

**`ROLLBACK.txt` template** (paths substituted and `shlex.quote`d; checked on both targets in S10):

```
# hm_store operation HMS-2026-0007: release 2 -> 3, database prod, 2026-10-01T09:20:11Z
# Run on the Odoo host as the odoo user (Docker: docker exec -u odoo -it <container> sh).
# Easiest: python3 /var/lib/odoo/addons/19.0/hm_store/lib/rescue.py rollback --op HMS-2026-0007
# Or by hand:
# 1. Stop Odoo.   Docker: docker stop <container>   Package: sudo systemctl stop odoo
# 2. Put the previous files back:
chmod 0750 /var/lib/odoo/addons/19.0/hm_payroll
mv /var/lib/odoo/addons/19.0/hm_payroll /var/lib/odoo/hm_store/ops/HMS-2026-0007/failed-hm_payroll
mv /var/lib/odoo/hm_store/ops/HMS-2026-0007/backup/hm_payroll /var/lib/odoo/addons/19.0/hm_payroll
rm -rf /var/lib/odoo/addons/19.0/af_zakat          # newly placed by this operation, no previous copy
# 3. If the upgrade got partway, restore the backup taken before it:
#    pg_restore -U odoo -d prod --clean /var/lib/odoo/hm_store/backups/prod-HMS-2026-0007.dump
# 4. Re-run the previous version's upgrade once, then start Odoo:
odoo -c /etc/odoo/odoo.conf -d prod -u hm_payroll --stop-after-init
```

---

## 8. Out of scope for v1 (explicit)

**Hosting.** Odoo Online (Import Module drops `.py`, verified) and Odoo.sh (code comes from a Git branch into rebuilt containers; runtime writes to the data dir would not persist — **UNVERIFIED**, treated as unsupported). Windows hosts (`fcntl`, rename semantics). Several app servers sharing one database without a shared persistent data dir. Odoo series other than 19.0 — `series` is carried in every format so 20.0 can be added.

**Odoo cannot do these, so neither can we.** Installing pip or apt packages; making a module server-wide (`server_wide_modules` is startup-only); hot-reloading already-imported Python; in-process upgrade of imported code.

**Deliberately not built in v1.** In-process install without a restart (the mechanics are proven in S1; shipping it is deferred, D1). More than one store-managed database per data dir. Per-module update to a serial different from the rest. Downgrade or rollback through the store UI. Automatic or cron-driven installs. An in-app Repair for lost files. Removing files on uninstall. A systray badge.

**Security extras deferred.** Server freshness signatures (`K_ts`) — deferred to v1.1 under D17, not dismissed; signed yank/revocation lists inside releases; a privileged root apply helper; hardware-token signing; portal TOTP. **Installation keypairs and proof-of-possession are no longer deferred** — a reduced form is in v1 (§3.4 step 5), because T11 is about key theft and the "it does not prevent RCE" rationale was answering a different question.

**Server.** Portal UI for Odoo releases or activations; self-service activation release; issuing Odoo licences on the server; web upload of releases; enforcing `max_users`.

**Existing defects untouched.** MyERP's transfer-on-activate hole (`LicenseActivationService.php:112-143`), the MyERP JWT/product model, and hm_license audit L1.

---

## 9. Build order: small verifiable slices

**S1 comes first, before a single line of product code, because it is the only slice that can kill the project.**

**Order, and the gates revision 2 adds** (the slice numbers are unchanged so every cross-reference in this document still resolves; S5 is split in two and S5a moves early):

```
S1  →  S5a  →  S2  →  S3  →  S4  →  S5b  →  S6  →  S7  →  S8  →  S9  →  S10
       key      server  lib    module  keyring,  server  client  apply  auto-  offline
       custody  hygiene               signer,   +auth   +verify        rollback  + runbook
                                      bootstrap
```

- **S5a gates S2.** No customer licence is issued under the plaintext K_licence once S5a is designable, and no customer licence blob reaches the server until S2 has landed. Revision 1 had K_licence written with `NoEncryption()` beside K_release; that is fixed before anything else is built.
- **S3 must not start until findings 1, 2, 6, 7 and 9 are settled in this document**, because each of them changes code that S3's own acceptance tests cover. They are settled: §2.8a, §2.10 rule 7, §3.3, §3.4, §2.8 step 1.
- **S5b gates S10.** No bootstrap zip is published before it can be signed by K_root and verified by the operator against an out-of-band fingerprint.
- **S6 carries the server-side authorisation fixes** (row-based authorisation, verified-id throttling, installation pinning). If S6 runs long, the installation pinning may slip — but only together with T11's claim, which §5 already words honestly, never by shipping a control table that overstates what the server does.
- **S1(9) gates S8, added in revision 3.** §2.11's entire reconcile now rests on the boot marker, so S8 must not start until S1(9) has shown the marker commits in every boot shape. If it does not, §2.11 is redesigned around the fallback witness named there — a redesign, not a patch, and cheaper before S8 than during it.
- **`models/hm_store_boot.py` moves from S9 into S8**, because `_register_hook` running during registry load is settled (`modules/loading.py:588-594`), and because v1's reconcile needs the marker. S9 keeps only the auto-rollback behaviour and its own probe.

### S1 — Prove the riskiest assumption: runtime placement, in-process install, and self-restart (odoo repo, probes only)

The whole product rests on one unproven-in-this-environment chain: *the Odoo process itself can put importable Python into `addons_data_dir` while running, get Odoo to see and install it, and restart itself from inside.* The mechanics brief proved most of it on probe servers; S1 re-proves it in the real target shapes and settles the items that kill or reshape the design.

**Revision 3 adds three probes to this slice**, because three mechanisms this spec now depends on are assumptions rather than facts: the **restart methods and the prefork overlap window** (4a–4d), the **boot marker's commit** (9), and **`os.access` as root** (10). Acceptance 6 is rewritten: it no longer probes a status route, because there is no longer one; it now *reproduces* the two failures that caused the route to be removed, so the design decision is on the record with numbers attached.

Files: `tools/store_e2e.py` (probe harness), `tools/tests/fixtures/store_modules/hm_storefixture_a` v1 and v2 (v2 adds a column and a data record), `docs/probes/2026-10-hm-store.md` (results, committed). Disposable databases and `--data-dir /tmp/hmprobe` only; never the `hushmand` database.

Acceptance:
1. `chmod 700 <addons_data_dir>`; the Odoo process copies a module folder in, calls `Manifest._get_manifest_from_addons.cache_clear()` + `importlib.invalidate_caches()`, `update_list()`, `button_immediate_install()`. The model, a route and a static file all work **in the same process, with no restart**, in threaded mode with `-d`.
2. The same in prefork, `workers=2`, no `-d`: the second worker picks the module up through registry signalling and serves it.
3. **The negative case:** request the module's static path *before* the files exist, then place and install without clearing the cache — confirm it strands in `to install` and sets `base.partially_updated_database`, then confirm the cache clear fixes it. This is the reason invariant 3 exists.
4. **The restart methods of §2.9 G, measured, not assumed.** Odoo is PID 1 in an unmodified `odoo:19` container for all of these.
   - **4a `graceful`, threaded.** `odoo.service.server.restart()` (SIGHUP) brings the server back with the PID unchanged. Record whether the listening socket refuses connections at any point (`ThreadedServer.stop` calls `self.httpd.shutdown()`, `server.py:657-670` — a dip is expected).
   - **4b `graceful`, prefork `workers=2`.** Same, and record that the socket **never** refuses (it is passed through `ODOO_HTTP_SOCKET_FD`, `server.py:1087-1089`, `1107-1113`).
   - **4c `hard`.** `hm_store_restart_command` = `/usr/bin/docker restart <container>` run detached from inside Odoo: the container comes back, the operation survives, and the command's own death (it kills its parent) does not corrupt the operation row. Same for `/usr/bin/systemctl restart odoo` on the package target.
   - **4d `graceful` prefork, the overlap window — pass/fail with a number.** During an upgrade of the fixture module, drive a request every 250 ms from a second process and record, with timestamps: when the old generation stops answering, when the new one starts, and **how many requests were served by a worker running v1 code after the swap**. *Pass condition:* the count is > 0 (proving invariant 3's corrected wording, not the old one), the overlap is bounded by the 60 s `reload_timeout` of `server.py:1129-1134`, and **every hm_store request served in that window is refused by the §2.9 I stale-worker guard while non-hm_store requests still succeed**. *Fail condition:* the guard does not fire, or a non-hm_store request 500s — either means the overlap cannot be left as a disclosed residual and prefork must default to `operator` with `graceful` removed from §2.9 G entirely.
5. Deferred upgrade: swap files → `button_upgrade` → set flag → commit → restart; after the restart every worker runs v2 and 20 of 20 `search_read` calls succeed against the new column.
6. **Progress observation, replacing revision 2's status-route probe.** There is no hm_store route to probe any more (§2.4). Instead, *(a)* confirm `GET /web/static/img/favicon.ico` with `credentials: 'omit'` answers with no `Registry` open — assert it by logging inside `Registry.new` and seeing nothing, and by checking the request never appears in `pg_stat_activity`; *(b)* confirm the dip/no-dip asymmetry of 4a vs 4b from the client's point of view, since that is what `store_progress.js` reasons about; *(c)* **the negative control that proves why the old design was removed**: from a prefork server with **no** `-d`, issue one cookie-less `X-Odoo-Database` GET just after the swap and record that *this request* runs the whole upgrade and how long it takes against `limit_time_real`; then in threaded mode, issue polls every 3 s during an upgrade and record whether `process_limit` accumulates them into `limits_reached_threads` and calls `self.reload()` (`server.py:503-524`, `732-751`). Both are expected to reproduce; record them in the probe document so nobody re-proposes the route.
7. `find_pg_tool('pg_dump')` resolves inside the `odoo:19` image. Expected to pass — `/usr/bin/pg_dump` is present (container r3) — so this is a confirmation, not a gate, and preflight 15's hard-acknowledgement fallback is the exception path, not the expected one.
8. Kill the process between swap and commit, and between commit and restart; record exactly what the database and the disk look like in each case, to lock the reconcile table (§2.11).
9. **The boot marker commits — pass/fail, and v1's reconcile depends on it.** Install `hm.store.boot`, then boot the server in each of: threaded with `-d`, threaded without `-d` (marker written inside the first request's registry load), prefork with `-d`, prefork without `-d`, and `--stop-after-init`. *Pass condition:* after each boot, a **fresh psql connection** (not the Odoo process) reads a strictly higher `hm_store.boot_seq` than before, and `hm_store.boot_at` parses; and after a boot whose `load_modules` **raised**, the marker either is not written or is written and committed — recorded either way, because §2.11's `stalled` branch has to be right about which. *Fail condition:* any shape where the write is flushed but not committed. If it fails, `hm.store.boot` is not the witness: fall back to a witness written by the first successful `hm_store_progress` call in its own committed cursor, re-scope §2.11's table onto it, and say so in §2.6 check 20 — do not ship a reconcile that cannot tell a restart from a stall.
10. **`os.access(W_OK)` as root** (settles the Appendix B item behind preflight check 5). In a throwaway container started **without** `--user`, with `/var/lib/odoo/addons/19.0` left at `0500`: record `os.geteuid()`, `os.access(d, os.W_OK)` and whether `open(d + "/x", "w")` succeeds. POSIX says root bypasses DAC mode checks, so `True`/succeeds is expected. The result does not change check 5, which refuses `euid == 0` regardless; it decides only how the check-5 message explains itself.

**If 1, 4a–4c, 5 or 9 fails, stop or re-scope.** 1 failing means no in-app installer is possible on that shape. All of 4a–4c failing means hm_store can never restart anything and every apply is `operator` — buildable, but the UI and §2.9 G change shape. 5 failing means the whole apply design changes. **9 failing means §2.11 has no restart witness**, which is a reconcile redesign and must be settled before S8 starts, not during it. 4d is a *measurement*, not a gate on the project — but its result is what §2.9 G's prefork default and §2.9 H's wording have to match, and the probe document must carry the number. Everything below assumes S1 passed and records its answers in the probe document.

### S2 — Licence server hygiene and TLS (server repo)

Files: §3.8. Acceptance:

(a) **`git log -p -S'<the password>' --all` returns nothing** — not `git grep`, which searches the checkout and would have left the credential in history, in every existing clone and in every deployed vendor directory. Meeting this means either a history rewrite (`git filter-repo`, force-push, every clone re-cloned and the old ones destroyed) or a dated accepted-risk note in `docs/AUDIT-2026-09.md` naming every party who holds a clone; the acceptance is met by doing one of the two, not by choosing neither.
(b) on a copy of production data, `php artisan db:seed` leaves the admin password hash and `LICENSE_SIGNING_SECRET` unchanged;
(c) `curl -sI http://store.hushmand.tech/` returns 301 to https and `https://…/api/v1/health` returns 200 on a valid certificate;
(d) production `.env` has `APP_DEBUG=false` and `SESSION_SECURE_COOKIE=true`;
(e) `php artisan test` is green;
(f) **the production admin password is rotated to a value that has never been in the repository**, verified by attempting to log in with the old one and being refused;
(g) `.env.example` has `APP_DEBUG=false` in both places and no empty `LICENSE_SIGNING_SECRET=` line;
(h) the `license-api` limiter's unverified-input keying is recorded in `docs/AUDIT-2026-09.md` with an owner and a date (accepted for v1, §3.8).

**No customer licence blob is sent to the server until S2 has landed, and none is issued under the old plaintext K_licence once S5a has landed.**

### S3 — `hm_store/lib`, pure Python (odoo repo)

Files: `addons/hm_store/lib/*` including `test_verify.py`, `test_unpack.py`, `test_plan.py`, `test_rescue.py`, `test_rootpin.py`, `test_client.py`. Acceptance: `python -m unittest discover -s addons/hm_store/lib -p "test_*.py"` passes, covering at least —

- **keyring:** a signature by a non-pinned root; a wrong domain prefix; **`keyring_serial` below the floor, with each of the three floor sources in turn (`trust.MIN_KEYRING_SERIAL`, `state.json`, an operation row) as the one that refuses it**; a keyring that omits a `revoked_key_ids` entry the installation has already seen (refused, `revoked_key_readmitted`); a revoked key used for a release; **and the ordering assertion: when the keyring is below the floor, the release index in the same response is never parsed — a deliberately malformed index in that response must not change the error code**;
- **floor persistence:** the floor is written before the index is trusted, survives a simulated crash immediately after acceptance, and never decreases across any sequence of inputs;
- **root pin:** seeding on a clean tree; refusal when the pin and `trust.py` disagree; rule 7 against a staged `trust.py` that removes a root key, alters one, lowers `ROOT_THRESHOLD`, lowers `MIN_KEYRING_SERIAL`, changes a domain prefix, changes the store host, or grows a cap beyond 2×; an added root key **without** a `trust_update` (refused), **with** a `trust_update` signed by a non-root key (refused), with one whose `hm_store_tree_sha256` names a different tree (refused), and with a correct one (accepted, and the pin rewritten exactly once); a `trust.py` containing a non-literal expression (refused without evaluating it);
- **index:** one flipped byte, `key_id` mismatch, wrong series or product, a release signed by a root key;
- **transport:** a response whose `Content-Length` exceeds 4 MiB (refused before reading); a chunked response with no `Content-Length` that keeps sending (aborted at the ceiling); **a gzip bomb that is small on the wire and large decompressed** (refused, counted post-decompression); the lint that `lib/client.py` never references `.json()`, `.text` or `.content`;
- **download:** archive sha mismatch; a stream longer than the signed size; `Content-Length` greater than the signed size;
- **zip:** extra member, missing member, duplicate, case-duplicate, `../x`, `/abs`, `a\b`, symlink mode, encrypted flag, per-file hash mismatch, a symlink already at the target path;
- **manifest:** version ≠ index, `auto_install: True`, `license` not OPL-1;
- **plan:** below floor, not entitled, closure, takeover, unchanged archive not placed, another database blocks, **hm_store present in `P` reduces the plan to `{hm_store, hm_license}`**, and the freshness banner fires at 45 and 180 days and not at 44, including with the clock set backwards;
- the AST test that `lib/` never imports `odoo`.

### S4 — hm_store skeleton, hm_license changes, CI compliance (odoo repo)

Files: §2.1 minus apply/offline, §2.2 CI files, §2.14. Acceptance: all CI jobs green with hm_store in every list; `demo` gets `AccessError` on `hm.license` `search_read(['key'])` while `status()` still works; a `group_erp_manager`-only user can read nothing under `hm.store.*` and run no action; on a probe server the Status page shows the 0500 message with resolved paths and both commands **and the chmod-before-unzip ordering**, turns green after `chmod 700` with no restart, shows the opt-in message without `hm_store_database`, and flags `--dev=reload`; **preflight 17 fails on a root-owned `hm_payroll` folder placed by `sudo unzip` and names the `chown` fix; preflight 18 seeds the root pin on first run, prints the fingerprint, and refuses every operation when the pin is edited to disagree with `lib/trust.py`; preflight 16 warns when neither `db_name` nor `dbfilter` is set**; `odoo neutralize` on a copy sets `hm_store.neutralized=1`; `tests/test_no_chmod.py` and `tests/test_root_pin_immutable.py` pass. And, for the revision-3 fixes:

- **`tests/test_menus.py` clicks every menu entry and every button end to end** and asserts none raises `AccessError`: Modules (and its `default_get` reconcile), Check for updates, Update all, Check status, Status, Offline install, the per-row Install/Update buttons, Operations → Check status / Restart now / Resume. This test exists because a path allowlist converts a working button into an `AccessError` silently, which is exactly how revision 2's guard broke every one of these; it is a **blocking** acceptance item, not a nice-to-have.
- `tests/test_guard.py`: the allowlist is a closed set (a call from `/web/action/run` is refused for `kind='mutate'` and `kind='apply'`; a call from `/web/dataset/call_kw` is refused for `kind='apply'`); a `kind='cron'` call with a request present is refused; the cron method reaches no import-path, `ir.module.module`, flag or restart code path; an XML-RPC call to `action_apply` is refused because `dispatch_rpc` pops the request.
- `hm.store.operation.write()` raises `UserError` without `hm_store_internal`, succeeds with it, and `unlink()` raises either way; `tests/test_access.py` asserts `hm_store_internal` appears nowhere in a view, an action `context=`, a `default_*` key or an XML data file.
- **Preflight 5 as root:** in a container started without `--user`, the Status page refuses with the euid message and the store is blocked, even though `/var/lib/odoo/addons/19.0` is still `0500` and `os.access` returns `True`. The euid appears on the Status page and in the `audit.log` line for the refusal.
- **Preflight 8's recovery is testable:** create an `imported=True` row named `hm_probe`, confirm the message names it and gives the Apps → Uninstall steps of §7 verbatim, uninstall it, and confirm preflight goes green with no restart.
- **Preflight 12 fires in threaded mode:** with `workers = 0`, `db_name` unset and `limit_time_real = 120`, the warning is shown and its text is the *threaded* variant (the one that says the whole server re-execs).
- `hm.store.status` reports `euid`, `process_user`, `worker_mode` and the restart methods preflight 19 found; the module ships **no** `controllers/` package and a test asserts hm_store registers no route at all.

### S5a — Key custody: re-key K_licence, generate K_root and K_release, stand up the signer (odoo repo + C1b)

**Runs immediately after S1 and gates S2 and S5b.** Files: `tools/release_signing.py` (`--generate-root`, `--generate-release`, `--generate-licence`, fingerprint printing), `tools/issue_license.py` (`load_private_key` passphrase path; `generate_keys` switched to `BestAvailableEncryption`), `docs/KEY-CUSTODY.md` (written, printed, and stored with the USBs).

Acceptance: (a) `issue_license.py` can neither create nor load an unencrypted licence key — the `NoEncryption()` path is gone, not merely unused, and a test asserts it; (b) every outstanding licence is re-issued under `lic-2026-11` and the old id is removed from `VENDOR_PUBLIC_KEYS` and `config/odoo_store.php`, with the date recorded; (c) K_root's fingerprint is printed, written onto the contract template, the quote PDF template and the printed card, and read back correctly over the phone by a second person; (d) C1b is demonstrably air-gapped — `ip link` shows no associated interface, and a `ping` from it fails — with the procedure written down in `docs/KEY-CUSTODY.md`; (e) a sealed paper copy of each passphrase exists in a second location. **If (a)–(c) are not done, no customer licence is issued and no bootstrap is published.**

### S5b — Keyring, split builder, signed bootstrap (odoo repo)

Files: `tools/build_release.py` (`stage`, `assemble`, `bootstrap`, `bundle`), `tools/release_signing.py` (`keyring`, `sign-release`, `sign-bootstrap`, `sign-trust-update`), `tools/verify_bootstrap.py`, `releases/19.0/ledger.json`, `tools/tests/test_release.py`.

Acceptance: two `stage` runs on one tag produce byte-identical zips, `release.json` and `SIGN-REQUEST.json`; refusals for a dirty tree, an untracked file under `addons/`, a symlink, changed content with an unchanged version, a lower version, a non-increasing serial, `auto_install`, a non-OPL-1 licence, an hm_store whose `trust.py` does not pin the keyring root, **and an hm_store whose `MIN_KEYRING_SERIAL` does not equal the keyring being shipped or is lower than the previous release's**; `lib/verify.py` accepts the output; a keyring that revokes `rel-2026-10` and adds `rel-2027-01` is accepted, and a release signed only by the revoked key is refused; **a keyring that drops a previously-published `revoked_key_ids` entry is refused by the tool**; `lib/verify.py` accepts the output. And, for the split:

- `stage` writes no `.sig` and never imports a signing routine — enforced by a tier0 test, not by inspection;
- `sign-release` refuses a request with no `ci` block, with `conclusion != "success"`, with `head_sha != git_commit`, or with a mismatched `release_json_sha256`;
- `sign-release` **has no `--yes`**: a test asserts that the typed confirmation cannot be supplied by a flag, an environment variable or a config file, and that `--dry-run` produces no signature;
- a `trust_update` requires its own second confirmation and a K_root signature, and `lib/rootpin.py` accepts the pair end to end;
- `bootstrap` + `sign-bootstrap` produce a zip and a `.rootsig`, and `verify_bootstrap.py` **accepts** it with the right fingerprint, **refuses** it with one wrong hex group, **refuses** a zip with one flipped byte, and **refuses** a `.rootsig` whose embedded public key is a different key that correctly signs the zip (the fingerprint, not the bundle, decides);
- the existing `tools/tests/test_packaging.py` still passes.

### S6 — Server: tables, verifier, catalogue endpoint, import command (server repo)

Files: §3.2–3.6 (catalogue only), `tests/Unit/Odoo/OdooLicenceVerifierTest.php`, `tests/Feature/Odoo/CatalogueTest.php`, fixtures in `tests/Fixtures/odoo/` generated by `tools/issue_license.py --emit-registration` with a throwaway key (ASCII customer, Dari customer name, empty `features`, with and without `max_databases`, tampered payload, tampered signature). Acceptance: valid fixtures verify and tampered ones fail **over `payload_b64` only, with no PHP canonicalisation anywhere in the diff**; the exact 200 JSON shape of §3.5; 401 `licence_invalid`, 403 `licence_expired` (expires yesterday), 403 `licence_revoked`, 403 `licence_not_registered` with the flag on; the third distinct uuid returns `activation_limit` at a limit of 2 while repeating a uuid consumes no slot; `odoo:release:import` refuses a bad keyring, a bad index signature, a size or hash mismatch, and a non-increasing serial; every MyERP API test still passes. And, for the revision-2 server fixes:

- **`licence_mismatch`:** a payload that is *correctly signed* and carries a **registered** `licence_id` but a widened `modules` list is refused 403 `licence_mismatch`; likewise a later `expires`, a larger `max_databases`, and a changed `customer`. The `data` body is `null` — the response does not tell the forger which field failed. A `warning` log line records `licence_id`, both `payload_sha256` values and the IP;
- **authorisation reads the row:** with a registered row whose `modules` is narrower than the payload's, the archive endpoint refuses the module that only the payload lists — proving the row, not the payload, decides;
- **first-use pinning:** with `require_registration = false`, the first payload for an unknown `licence_id` is stored, and a second, differently-shaped but correctly-signed payload for the same id is refused `licence_mismatch`;
- **throttling keys on the verified id:** the seventh catalogue call in a minute returns 429 JSON **even when every request body differs**, and **there is no `licence` field in the request at all** — a request carrying one is either ignored or rejected by validation, and a test asserts the string `licence` does not appear as an accepted input key;
- **pre-verify limiting:** the 61st request from one IP in a minute is refused *before* any `sodium_crypto_sign_verify_detached` runs (asserted by a spy on the verifier);
- **installation binding:** the first request pins `install_pubkey`; a later request with a valid licence but a signature from a different key is 403 `installation_mismatch`; `odoo:activation:release` clears the pin and the next request re-pins; a replayed `X-Hm-Install-Sig` from three minutes ago is refused.

### S7 — Archive endpoint and client download/verify, no swap (both repos)

Files: the server archive endpoint + `tests/Feature/Odoo/ArchiveTest.php`; hm_store `action_download_verify`, `lib/client.py` and `lib/instkey.py` wiring. Acceptance, on a probe Odoo pointed at a local server over loopback: the operation reaches `verified` and staged hashes match; `find <addons_data_dir> -newer <marker>` is empty; flipping one byte of a stored zip on the server produces `archive_hash_mismatch`, deletes staging and changes nothing; an unlicensed module is refused client-side before any request **and** 403 when the endpoint is called directly; a 307 response is not followed. And:

- the fake server returns a 5 MiB catalogue body → `response_too_large`, refused before `json.loads`, worker memory flat;
- the fake server returns a 2 KiB gzip body that decompresses to 500 MiB → refused at the 4 MiB ceiling, with `Accept-Encoding: identity` sent and honoured or not;
- the fake server serves a keyring one serial below the floor → `keyring_replayed`, and a deliberately malformed release index in the same response does **not** change the error code (proving it was never parsed);
- the client generates `install_key.pem` at `0600` on first use, signs subsequent requests, and never writes the private key into the database or a `pg_dump`;
- an index whose signed `created_at` is 200 days old produces the red staleness banner while still allowing the install.

### S8 — Apply, restart, reconcile, backup (odoo repo)

Runs only on disposable probe servers and databases. Acceptance:
1. Threaded with `-d`: install `af_jalali` through the store; after the restart the operation is `done`, the module `installed`, `latest_version` equals the index version.
2. Prefork, `workers=2`, no `-d`: update r1 → r2 where a fixture module adds a column and a record; afterwards the column exists, 20 of 20 `search_read` calls across both workers succeed, the operation is `done`, `state.json` has serial 2 and floor 2. **Plus, on the same run:** the operation records `restart_method`, `boot_seq_at_apply` and `tree_id_at_apply`; during the graceful reload every hm_store call served by an old worker is refused by §2.9 I with the stale-worker message while non-hm_store requests keep succeeding; and the number from S1(4d) is re-observed within the same order of magnitude.
3. Failure injection: r3 with broken data XML → operation `failed`; running `ROLLBACK.txt` by hand and `rescue.py rollback` each restore r2 and service.
4. Crash injection between swap and commit → reconcile shows `stalled`; **Resume** completes.
5. A second database with the module installed blocks the update with the named message. **The enumeration is the `pg_database` query, not `list_dbs`:** the block still fires when the server is started with `-d prod` (where `list_dbs` would have returned only `prod`), and when the second database is owned by a *different* PostgreSQL role (where `list_dbs`'s `datdba` filter would have hidden it). A third database the store cannot connect to appears in the wizard as **`unknown — could not check`** with its reason, never as "not affected", and the restart acknowledgement text changes to the "N databases could not be inspected" variant.
6. An XML-RPC call to `action_apply` with an API key is refused — `dispatch_rpc` pops the request (`http.py:444`), so `check_identity` raises `UserError` and guard step 3 refuses. A `/web/action/run` call naming a server action that tries to reach a mutating method is refused by the allowlist.
7. Test restart works with Odoo as PID 1 in an `odoo:19` container **and leaves a committed boot marker**; without either, the update button stays disabled and the message says which of the two failed.
7a. **Reconcile cannot loop (the blocker-4 regression test).** Stage an update whose target module fails to install, restart, and let `load_modules` complete: `base.partially_updated_database` is back (`loading.py:599-607`) *and* `boot_seq > boot_seq_at_apply`. Assert reconcile reports **`stalled`**, not "Restart has not happened", and that **no Restart now button is rendered**. Then force a second restart by hand and assert the banner becomes "Odoo has restarted twice and the upgrade has not moved." Separately, with the flag present and **no** boot (`restart_method = operator`, nobody restarted), assert reconcile reports `awaiting_restart` and *does* offer Restart now, and that after 30 simulated minutes it reads `(overdue)`.
7b. **`hard` and `operator` restarts end to end.** With `hm_store_restart_command` set, an apply in prefork uses `hard`, the container restarts, and reconcile reaches `done` — and no old-generation worker exists at any point (the inverse of 2). With no command set, prefork defaults to `operator`: the wizard shows the resolved command, hm_store restarts nothing, and reconcile reaches `done` only after the operator's own restart.
8. A `pg_dump` runs detached, survives a worker recycle, and its `.done` sha256 matches the file. **Its mode is `0600` with the process umask set to `0022` and to `0000`** — the mode comes from the `O_EXCL|O_NOFOLLOW` open, not from the umask — and reconcile prunes it on the `done`, `failed` and `stalled` paths alike, stamping `backup_pruned_at`.
9. No ERROR lines in the server log on any success path.
10. **hm_store updates itself alone:** a release that changes `hm_store` and `hm_payroll` together produces a first operation containing only `{hm_store, hm_license}`, and the modules follow in a second operation offered after reconcile.
11. **The self-update trust gate:** a locally-signed release whose `hm_store` archive ships a `trust.py` with an extra root key and **no** `trust_update` is refused `root_pin_change_refused` with staging deleted and the import path untouched; the same release **with** a correct K_root `trust_update` applies, and reconcile rewrites C13 exactly once, keeping `root.json.<old>.bak` and appending to `audit.log`. Afterwards preflight 18 is green, and a release signed by the *old* keyring is still accepted (adding a root never removes one).

### S9 — Auto-rollback, gated on its own probe (odoo repo)

**The probe shrank in revision 3.** "Does `_register_hook` actually run during registry load in 19" is **settled and no longer gates anything**: `modules/loading.py:588-594` calls it on every model, once per load, with a comment saying so ("This is done *exactly once* when the registry is being loaded"), read in the container. `models/hm_store_boot.py` therefore ships in **v1**, in S8, carrying only the boot marker (§2.11) — S1(9) is what proves the marker *commits*, and that is a v1 gate, not an S9 one.

What S9 still probes, and it is the genuinely open part: **does a restored tree boot, and is exactly one further restart emitted?** Only if yes, extend `hm.store.boot` with the post-boot reconcile of §2.11: restore `backup/<op>/`, state `rolled_back_restart_pending`, **exactly one** further restart, then `rolled_back`. Acceptance: S8(3) now recovers with no shell at all; the banner names the failure; a forced double failure never produces a second automatic restart; and — because §2.9 G now has three methods — the one automatic restart uses the operation's own `restart_method`, and under `operator` it emits **no** restart at all but leaves `rolled_back_restart_pending` with the command. If the probe fails, this slice ships nothing beyond the marker and `ROLLBACK.txt` + `rescue.py` remain the documented recovery.

### S10 — Offline `.hmpkg` and the first-customer runbook (odoo repo)

Files: `wizard/hm_store_offline_wizard.py`, `docs/STORE-INSTALL.md`, `docs/STORE-FORMATS.md`, `tools/verify_bootstrap.py`, and a **K_root-signed** bootstrap zip published on the bootstrap host C14 — a host that must already satisfy D16 (separate domain, registrar account, hosting account and TLS key from `store.hushmand.tech` and `license.hushmand.tech`), with the separation written down and checked, not assumed.

Acceptance: a bundle from `build_release.py bundle` gives the same end state as S8(1); refused — a tampered `release.json` inside the bundle, an extra entry, an oversize entry, a serial below the release floor, **a keyring below the keyring floor**; and on a fresh `odoo:19` Docker host **and** a fresh Ubuntu machine with the Odoo 19 package, following `STORE-INSTALL.md` word for word gets from nothing to `hm_payroll` installed from the store in 20 minutes or less, running only the documented shell commands. And, for the bootstrap:

- **no step requires root**, and after the run every placed tree is owned by the Odoo process uid — checked by the runbook itself, so an operator who used `sudo` finds out immediately (preflight 17);
- the runbook's step 1 **fails closed**: an operator who cannot produce a K_root fingerprint from a non-download channel is told to stop and phone, and a dry run with a wrong fingerprint produces a refusal and no unzip;
- `verify_bootstrap.py` runs on both targets with only `cryptography` (present in `odoo:19`, container r2: 41.0.7) and its output is a single line either way; whether `openssl pkeyutl -verify -rawin` is available on both is recorded here (**UNVERIFIED** until this slice runs);
- the fingerprint the Status page prints after install equals the one in the contract, character for character, and a screenshot of both is filed with the customer record.

---

## 10. Open decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| D1 | Always restart, even for a fresh install, in v1? | **Yes.** S1 proves the in-process path exists, but one code path removes the per-worker manifest-cache hazard in the applying worker and halves the test matrix. **Revised in r3:** it does *not* remove the mixed-code hazard in prefork, because a graceful reload overlaps generations on purpose (invariant 3) — so "always restart" buys one code path and a clean applying worker, not the absence of mixed code. That is still the right trade, and D21 is where the overlap is actually addressed. Revisit only after v1 has run in the field for a quarter. |
| D2 | Default databases per licence when the claim is absent | **2** (production plus one restore or staging). Add `--max-databases` to `tools/issue_license.py`; the server enforces it; you free slots with `odoo:activation:release`. |
| D3 | Downloads during the 30-day grace period? | **No.** Downloads stop at `expires`; grace keeps installed code running. Extend the licence if a customer needs a security fix during grace. |
| D4 | Opt-in via `odoo.conf` key or a file in the data dir? | **`hm_store_database` in `odoo.conf`.** Unknown-key behaviour is verified, it is the same edit on Docker and the Debian package, and it costs one startup WARNING. |
| D5 | Store hostname | **`https://store.hushmand.tech`** on 443, nginx + Let's Encrypt, CAA record with `accounturi`, registrar lock, 2FA on the registrar. A separate name from `license.hushmand.tech` so it can move without an hm_store release. The **bootstrap** host is separate again — D16. |
| D6 | K_root, K_release and K_licence custody | **Three passphrase-encrypted PEMs on the air-gapped signer C1b**, with a sealed paper copy of each passphrase in a second location. K_licence is re-keyed from its current plaintext form in S5a — revision 1 left it at `NoEncryption()` beside K_release, so one laptop compromise yielded both RCE and the power to mint licences. K_root is touched only to sign a keyring, a bootstrap zip or a trust update. **No key ever sits on a host that runs `gh`, `git fetch`, a browser, or a package manager against the internet.** Backups of the three are separate and offline; K_licence never shares a backup with K_release. Hardware token later. |
| D7 | Release granularity | **One serial for the whole catalogue**, per-module archives. Customers never mix modules from different releases. |
| D8 | Must a tag have green CI before signing? | **Yes.** The check runs on C1a, where the network is (`gh run list --commit <sha> --json conclusion,databaseId,headSha`), and the attestation travels to the signer inside `SIGN-REQUEST.json`; C1b refuses a request without one. **No override flag on either half** — and, changed in revision 2, **no override on the human review either**: `sign-release` has no `--yes`. Revision 1 automated the machine check with no escape hatch and left one on the only human checkpoint, which is backwards. A hotfix goes through CI like everything else. |
| D9 | `require_registration` from day one? | **`true` from the first sale.** Changed from revision 1's "start `false`, flip within the first month". The month-long window was only defensible while registration was believed to be the control against a leaked K_licence; it is not — §3.4 step 3's comparison of the presented payload against the registered row is, and registration is what gives that comparison something to compare against. Registering a licence is one artisan command at the moment it is issued, so `false` buys nothing and costs a window. |
| D10 | Automatic `pg_dump` before updates | **Yes where `pg_dump` exists**, detached, with a free-space check; a mandatory acknowledgement where it does not. The judge's graft, and the difference between a recoverable and an unrecoverable bad night. |
| D11 | Bootstrap location | **The addons data dir**, not `/mnt/extra-addons`, so the store never has to take over its own files. |
| D12 | Ship module `tests/` folders inside release archives? | **Keep them** (status quo). The shipped tree is then exactly what CI tested, and they are inert without `--test-enable`. |
| D13 | Daily "check only" cron with a notice? | **Yes, check-and-notify only, never install** — but tell ministry customers it makes one outbound HTTPS call a day and give them the off switch (`hm_store.check_cron` inactive). It also carries the **staleness line** of §2.7 step 0: a customer who turns the cron off loses the daily freshness signal, and the off-switch text says so, because a silent client is exactly what T28's attacker wants. |
| D14 | Show unlicensed catalogue modules in the list? | **Yes, badged "Not licensed"**, with no download. Names and versions are not sensitive and it helps upselling. |
| D15 | Auto-rollback (S9) before or after the first customer? | **After.** Ship v1 with `ROLLBACK.txt` + `rescue.py`; add auto-rollback once its probe passes and one real update has been done with you on the phone. |
| **D16** | Where the bootstrap zip is published, and how the K_root fingerprint reaches the customer | **A separate host C14 and four out-of-band fingerprint channels.** The host: its own domain, its own registrar account with its own 2FA, its own hosting account, its own TLS key, static files only, no server-side code, and **no credential, DNS zone or TLS key shared with `store.hushmand.tech` or `license.hushmand.tech`**. The fingerprint: printed in the signed sales contract, on the signed quote/invoice PDF, on a printed quick-start card, and read aloud on the onboarding call — at least two of them on paper and none of them the download page or the mailbox. Host separation is **containment, not the control**; the K_root signature is the control, and the spec says which is which. Cost: one extra domain and about an hour of setup, once. |
| **D17** | Server-signed freshness (`K_ts`) now that a keyring floor exists | **Defer to v1.1, do not dismiss.** Revision 1 dropped it on the ground that it does not prevent RCE, which is true and is not the point — a held store silently starving a customer of security updates is exactly the failure invariant 1's "denial of service" allowance was hiding. v1 ships the unsigned version of the same signal (§2.7 step 0): warnings on the signed `created_at` and on the time since the last successful call, which need no new key and catch the same behaviour, at the cost of being suppressible by an attacker who is willing to re-serve a *recent* index. `K_ts` runs through the same verification path as the keyring, so adding it later is a keyring role and a schema field, not a redesign. **Assumption to settle before v1.1:** that the unsigned warning is enough in practice, which only field use can answer. |
| **D18** | When to re-key K_licence | **Before the first sale (S5a), not after.** Re-keying costs one reissue and one paste per existing customer, so the price rises with every licence sold. Until it lands, treat T24 as offering nothing. |
| **D19** | Two machines, or one machine with two boot environments? | **Either, and be honest about which.** The requirement is that the OS holding the keys has never had a network interface associated in that boot: a second retired laptop with the Wi-Fi card removed, or C1a booted from a dedicated offline live-USB with the key USB attached. **Not** acceptable: the same running OS with Wi-Fi switched off in the menu bar, or a VM on a networked host. `docs/KEY-CUSTODY.md` records which of the two is in use and the check that proves it (`ip link` shows no carrier; a `ping` fails). A solo vendor can run the live-USB variant; nobody should pretend the laptop that ran `gh` an hour ago is air-gapped. |
| **D20** | Installation keypair in v1, or defer with the rest of the proof-of-possession work? | **In v1, in the reduced form of §3.4 step 5** — pin on first use, sign every later request, ~40 lines client-side and ~30 server-side. It is the difference between a stolen licence *string* being usable and not. It is **not** a defence against an attacker who copies the whole data directory, and §5 T11 says so. If S6 slips, this may slip with it, but T11's wording does not change back. |
| **D21** | Which restart method is the default in prefork, given that SIGHUP overlaps generations for up to 60 s? | **`operator`, not `graceful`.** SIGHUP in prefork is a graceful reload by design (`server.py:1105-1134`, `1175-1181`, `1195-1209`): old workers serve old Python against a schema the new master is migrating, for the whole migration. hm_store can make its own surface fail closed (§2.9 I) but it cannot make the *rest* of Odoo stop serving stale code, and choosing that for a customer's production server without asking is not the Store's call. So prefork defaults to telling the operator the command and waiting, `hard` is offered when they configure `hm_store_restart_command`, and `graceful` stays available and honestly labelled. **Cost:** the prefork happy path is no longer one click; a prefork customer must restart Odoo themselves or set one `odoo.conf` key once. **What would change this:** if S1(4d) shows the overlap is short and the stale-worker guard covers it cleanly, `graceful` can become the prefork default in v1.1 with the UI text of §2.9 H unchanged. That is a decision to make with a measurement in hand, which is exactly what 4d produces. |

---

## Appendix A — Odoo 19 facts this spec depends on

All from the four input briefs, which read them in the container source (`/usr/lib/python3/dist-packages/odoo`) or the 19.0 branch; the Docker daemon was down when revision 1 wrote this list, so S1 re-confirms the starred ones. Revisions 2 and 3 re-read the items they newly depend on in the live container and list them in their own blocks below; where a line number differs from the brief's, the **r3 block is authoritative** and the difference is a line drift in the same function, not a behaviour change.

- `initialize_sys_path()` adds `tools.config.addons_data_dir` whatever `addons_path` says, before every `addons_path` entry (`modules/module.py:141-171`) ★
- `addons_data_dir` = `<data_dir>/addons/19.0`, created `0o500` "will need manual +w to activate it" (`tools/config.py:1005-1017`) ★
- `Manifest._get_manifest_from_addons` is an `lru_cache` that core never clears (`modules/module.py:279`); a cached miss strands a module in `to install` ★
- `load_openerp_module` returns early when the module is already in `sys.modules` (`module.py:502`); there is no `importlib.reload` in core
- `Registry.new` deletes `base.partially_updated_database` in its own committed transaction and loads with `update_module=True` (`orm/registry.py:160-176`); on failure it calls `reset_modules_state` (`modules/loading.py:611-631`) ★
- STEP 2 runs `update_list()` when updating (`loading.py:423-427`); `latest_version` is written on a successful load (`:269`); **the flag is re-inserted at the end of a successful load whenever states are still pending** (`:599-607`, container r3) — which is why §2.11 does not use it as a restart witness
- `button_upgrade` calls `update_list()`, marks installed dependents, and `button_install`s new dependencies (`base/models/ir_module.py:704-752`)
- `_button_immediate_function` sets `lock_timeout 3s`, refuses on pending module states, and locks `ir_module_module` + `ir_cron` (`ir_module.py:599-659`) — copied, not called
- `assert_log_admin_access` requires `env.is_admin()` and logs ALLOW/DENY (`ir_module.py:55-73`); `is_admin()`/`is_system()` at `orm/environments.py:182-190`
- `check_identity` refuses without a request and re-prompts after 10 minutes (`base/models/res_users.py:87-117`)
- `restart()` is SIGHUP to `server.pid` on POSIX (`service/server.py:1681-1688`, container r3); Odoo's own delayed-restart thread is `addons/iot_drivers/tools/helpers.py:50-61` ★. **What that SIGHUP then does is not the same in both worker modes** — see the r3 block and invariant 3
- `cr.postcommit` callbacks (`sql_db.py:166`, run at 568)
- `list_dbs(force)` (`service/db.py:434-453`) — **not an enumeration of the server**, see the r3 block; §2.7 step 7 queries `pg_database` directly instead. `database.uuid` is `uuid1`, regenerated on duplicate and on restore with `copy=True` (`base/models/ir_config_parameter.py:18-25`; `service/db.py:185-205, 372-374`)
- Neutralize runs `<module>/data/neutralize.sql` for installed modules (`modules/neutralize.py:18-33`) ★
- CSRF tokens are checked only for non-safe methods (`http.py:2493`); JSON-RPC accepts only `application/json` (`:2544-2554`); request cap 128 MiB (`:247`); `X-Odoo-Database` selects a database without a session **only when `db_filter` accepts it for the request Host** (`:1826-1839`, container r3) — hm_store no longer uses it, see §2.4
- Unknown `odoo.conf` keys are stored with a WARNING and readable via `config.get()` (`tools/config.py:164-168, 901-917`); `limit_time_real` default 120 (`:488`); `'reload' in config['dev_mode']` gates the file watcher (`service/server.py:1657`)
- `imported=True` modules (Apps → Import Module) are excluded from the load domain (`base_import_module/models/ir_module.py:39-52`); import extracts only xml/csv/sql, `static/`, `i18n/` and drops `.py`
- Python 3.12 `zipfile._extract_member` has no symlink or `external_attr` handling (`/usr/lib/python3.12/zipfile/__init__.py:1770-1820`) — and hm_store never calls it
- Migration scripts run only when `installed < script_version <= current` (`modules/migration.py:195-208`); there is no downgrade guard
- Container libraries: `cryptography` 41.0.7, `requests` 2.31.0

**Read in the container during revision 2** (`docker exec hushmand-odoo`, source at `/usr/lib/python3/dist-packages`), for the facts this revision newly depends on:

- `X-Odoo-Database` is honoured only when `db_filter([header_dbname], host)` passes, and the session is marked `can_save = False` (`odoo/http.py:1828-1838`) — it cannot be combined with a session cookie for a different database (403, `:1830-1834`)
- `db_filter` returns the list **unchanged** when neither `dbfilter` nor `db_name` is configured, and intersects against `config['db_name']` when it is (`odoo/http.py:402-425`) — so without one of them an anonymous caller names any database and reaches `Registry(self.db)` (`:2849-2856`); a database that cannot be opened raises `RegistryError`, is logged at warning, and falls through to `_serve_nodb` (`:2856-2871`), whose body is the fixed `NOT_FOUND_NODB` HTML (`:280-286`, `:2240-2252`)
- mode `0500` denies the **owning** uid the write: as `uid=100(odoo)` in the `odoo:19` image, `os.access(d, os.W_OK)` is `False` and `open(d + "/x", "w")` raises `PermissionError` errno 13; `/var/lib/odoo/addons/19.0` is `dr-x------ odoo odoo` as shipped
- `requests.Response.iter_content` yields from `self.raw.stream(chunk_size, decode_content=True)` (`requests/models.py:816`, requests 2.31.0, urllib3 2.0.7) — so a byte ceiling applied to `iter_content` counts **decompressed** bytes, which is what §2.8 step 1 relies on
- the licence signing key is still written with `serialization.NoEncryption()` and loaded with `password=None` (repo, re-read: `tools/issue_license.py:74`, `:101`, default path at `:56`)

**Read in the container during revision 3** (`docker exec hushmand-odoo`, `19.0-20260817`), for the facts the four blockers and five majors turn on. Every one of these was read, not recalled:

- **Server actions dispatch over a different route from object buttons.** `@route('/web/action/run', type='jsonrpc', auth="user")` → `request.env['ir.actions.server'].browse([action_id]).run()` (`addons/web/controllers/action.py:53-59`); the only `call_button` route in core is `addons/web/controllers/dataset.py:34`, reached solely by `<button type="object">` (`call_kw` is `:28`). This is why §2.4 step 3 is an allowlist and §2.5 converts every mutating entry point.
- **Prefork SIGHUP is a graceful, overlapping reload.** `PreforkServer.stop()` → `fork_and_reload()` then `stop_workers_gracefully()` (`service/server.py:1175-1181`); `fork_and_reload()` forks, the parent `_reexec()`s, the child installs a `sighup_handler` and loops `while not phoenix_hatched and time.monotonic() < reload_timeout` with a 60 s budget (`server.py:1105-1134`); the new master's `run()` calls `preload_registries(preload)` **first** and only then `os.kill(int(os.environ.pop('ODOO_READY_SIGHUP_PID')), signal.SIGHUP)` (`server.py:1195-1209`). The listening socket survives the re-exec through `ODOO_HTTP_SOCKET_FD` (`server.py:1087-1089`, `1107-1113`). Threaded `stop()` instead calls `self.httpd.shutdown()` and joins non-daemon threads (`server.py:657-691`).
- **`limit_time_real` is enforced in every mode, and threaded enforcement re-execs the server.** `process_limit` iterates `threading.enumerate()` and flags any non-daemon (or cron) thread over `config['limit_time_real']` (`server.py:503-524`); the main loop then calls `self.reload()` (`server.py:732-751`), which is `os.kill(self.pid, signal.SIGHUP)` (`server.py:764-765`).
- **A db-bound request is what loads the registry.** `elif request.db: response = request._serve_db()` (`http.py:2849-2852`) → `registry = Registry(self.db)` (`http.py:2274-2277`) → `Registry.__new__` under the class-level `_lock` → `Registry.new`, itself `@locked` (`orm/registry.py:92`, `99-106`, `115-117`). A static file is served **before** that branch (`http.py:2852-2854` → `_serve_static`, `:2219-2238`).
- **A runtime-installed module can never own a nodb route.** `nodb_routing_map` is built from `[''] + config['server_wide_modules']` with `nodb_only=True` (`http.py:2758-2768`); `_serve_nodb` answers anything else with the fixed `NOT_FOUND_NODB` body (`:2246-2253`).
- **`base.partially_updated_database` is re-inserted after a successful load that left work pending** (`modules/loading.py:599-607`), contrasted with the committed DELETE in `Registry.new` (`orm/registry.py:172-176`). It is not a restart witness.
- **`_register_hook` runs exactly once per registry load**, at STEP 9 of `load_modules`, with the comment saying so, followed by `env.flush_all()` (`modules/loading.py:588-594`).
- **`list_dbs` does not enumerate the server.** It short-circuits to `sorted(config['db_name'])` when `dbfilter` is unset and `db_name` is set, and otherwise filters on `datdba = (SELECT usesysid FROM pg_user WHERE usename = current_user)` (`service/db.py:434-453`).
- **`db_filter` returns `dbs` unchanged only when neither `dbfilter` nor `db_name` is set**; with `dbfilter` it matches against the request Host, with `db_name` it intersects (`http.py:389-425`). `X-Odoo-Database` is honoured only if `db_filter` passes, and header+cookie for different databases is a hard `Forbidden` (`http.py:1826-1839`).
- **`_auth_method_none` gives the environment `uid = None`** (`addons/base/models/ir_http.py:260-262`), unlike `_auth_method_public` which swaps in `base.public_user` (`:265-268`) — so `.sudo()` on such an env leaves `env.user` an empty recordset. Moot in revision 3, since hm_store has no route; recorded because it is why the route could not simply have been patched.
- **`sudo()` does not bypass an overridden `write`.** `env.su` is what `check_access` reads (`orm/environments.py:178-190`, `is_superuser` is `self.su`); method dispatch is untouched. Hence §2.12's named context hatch.
- **`check_identity` requires a request and otherwise returns a wizard action instead of calling the method** (`addons/base/models/res_users.py:87-127`); the replay is `res.users.identitycheck.run_check()` (`:1430-1439`), a `type="object"` button. **`dispatch_rpc` pops the request** with `with borrow_request():` (`http.py:444`; `borrow_request` at `:1460-1466`), so `/jsonrpc` and `/xmlrpc` reach neither.
- **`assert_log_admin_access` requires `env.is_admin()` and logs ALLOW/DENY with login, id and remote addr** (`addons/base/models/ir_module.py:57-73`).
- **`imported=True` modules are excluded from the load domain, not from the Apps list** (`base_import_module/models/ir_module.py:38-39`, `:50-52`, over the base `[('state','=','installed')]` at `base/models/ir_module.py:347-349`).
- **`pg_dump` is present** at `/usr/bin/pg_dump`; the process runs as `uid=100(odoo) gid=101(odoo)`; `/var/lib/odoo/addons/19.0` is `dr-x------ odoo odoo`.
- **`ir_config_parameter` has only `key` and `value` NOT NULL**, `id` defaulting from `ir_config_parameter_id_seq`, and a UNIQUE constraint on `(key)` — so the `ON CONFLICT (key) DO UPDATE` in §2.11's boot marker and in `neutralize.sql` is valid.

## Appendix B — UNVERIFIED, and the slice that settles each

**Settled in revision 3, with evidence, so nobody spends a probe on them again:**

| Was UNVERIFIED | Evidence (container r3) |
|---|---|
| Whether the `/web/dataset/call_button` guard covers the spec's own menu entries | It does not: server actions go to `/web/action/run` (`web/controllers/action.py:53-59`). §2.4 step 3 is now an allowlist; §2.5 converts mutating entry points to object buttons |
| What a prefork graceful reload does to a worker mid-upgrade | It overlaps generations by design, up to 60 s (`server.py:1105-1134`, `1175-1181`, `1195-1209`). Invariant 3 rewritten; the *size* of the window is still open — S1(4d) |
| Whether a no-cookie `auth='none'` GET can observe a restart | It cannot (`http.py:2758-2768`, `2849-2852`, `2274-2277`; `orm/registry.py:92`, `99-106`). The route is removed |
| Whether `_register_hook` is called during registry load | Yes, exactly once (`modules/loading.py:588-594`). S9's gate shrinks to the restored-tree question; the marker's *commit* is a separate open item below |
| Whether `pg_dump` is present in the `odoo:19` image | Yes, `/usr/bin/pg_dump`. Preflight 15's hard acknowledgement is the exception path |
| `ir_config_parameter` column requirements for a raw insert | `key`/`value` NOT NULL, `id` from the sequence, UNIQUE on `(key)`; `ON CONFLICT (key) DO UPDATE` is valid |
| Whether `check_identity` alone refuses `/json/2` and XML-RPC API-key calls | `dispatch_rpc` pops the request (`http.py:444`, `1460-1466`), so `check_identity` raises `UserError` and the guard refuses too (`res_users.py:87-127`) |
| `display="always"` list-header buttons in 19 | **No longer needed** — §2.5's transient dashboard puts the buttons in a form header, so the spec does not depend on the answer either way |

**Still UNVERIFIED:**

| Item | Settled in |
|---|---|
| **Whether a write made in `_register_hook` is committed in every boot shape**, which is what makes the boot marker a usable restart witness — the single assumption §2.11 rests on | **S1 (9)**, and it gates S8 |
| **The size of the prefork graceful-reload overlap window**, and whether the §2.9 I stale-worker guard covers it cleanly enough for `graceful` to be a defensible prefork default | **S1 (4d)**, feeding D21 |
| **Whether `hard` restart (`hm_store_restart_command`) works from inside Odoo on both targets** — the command kills its own parent | **S1 (4c)**, S8 (7b) |
| **Whether `os.access(W_OK)` returns True for uid 0 against a `0500` directory in this image** (POSIX says yes; not re-run here). Preflight 5 refuses `euid == 0` regardless, so this decides only the message | **S1 (10)** |
| **Whether `openssl pkeyutl -verify -rawin` (OpenSSL 3.0+) is available on both bootstrap targets**; `verify_bootstrap.py` with `cryptography` is the documented path either way | **S10** |
| **Whether the unsigned freshness warning (§2.7 step 0) is enough in the field, or whether `K_ts` is needed** — an explicit assumption, not an assertion | **field use after v1; D17** |
| **Whether a customer's own backup regime captures `<store_dir>/install_key.pem`**, which decides how much §3.4 step 5's binding is really worth against a data-dir thief | **S7**, recorded in the probe document |
| In-process placement + install works on the real target shapes; the stale-manifest negative case behaves as probed | **S1 (1,2,3)** |
| `server.restart()` works when Odoo is PID 1 in the `odoo:19` image | **S1 (4a,4b)**, enforced afterwards by preflight 11 |
| Exactly what a crash between swap and commit, and between commit and restart, leaves behind | **S1 (8)** |
| Whether a failed module load's database changes are rolled back (so whether a `pg_restore` is required) | **S8 (3)** |
| Whether a restored tree boots, and whether exactly one further restart is emitted | **S9 probe** |
| Whether the CI Dari export step aborts on a module missing from `-i` (avoided by adding hm_store to `-i`) | **S4** |
| Production PHP, nginx and TLS on the licence VPS; PHP upload and body limits | **S2** |
| Odoo.sh runtime persistence (treated as unsupported) | never — out of scope |