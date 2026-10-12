# ibos_poultry — Ponytail Audit (over-engineering)

One-shot whole-repo audit of the Odoo 18 poultry module (~18.5k lines, 107 files).
Scope: dead code, duplication, speculative features, needless complexity.
Correctness/security/performance were out of scope; findings routed there are listed at the bottom.

**net: -~5,600 lines, -0 deps possible.** No files modified by the audit.

---

## 1. Dead model files — never imported (biggest cut)

`models/__init__.py` never imports these; the live models come from the `poultry_flock_*` / `poultry_growth_*` variants. Delete the files outright (~1,630 lines):

- `models/poultry_flock_receipt.py` (623) — old duplicate of `poultry.flock`
- `models/poultry_feed_consumption.py` (318) — old duplicate of `poultry.feed.consumption`
- `models/poultry_medicine_usage.py` (314) — old duplicate of `poultry.medicine.usage`
- `models/poultry_gas_consumption.py` (324) — old duplicate of `poultry.gas.consumption`
- `models/poultry_water_consumption.py` (51) — `poultry.water.consumption`, no views/ACL/menu

## 2. Dead data (~1,950 lines)

- **Zero-valued schedule lines (~1,560 lines):** all 42+62 mortality lines (`mortality_rate` = 0) and 42+62 weight lines (`expected_weight` = 0) in the HW/PR files are placeholders; the generators early-return on empty schedules, so deleting the lines changes nothing. Keep the 4 header records. `data/mortality_schedule_hw_data.xml`, `data/mortality_schedule_pr_data.xml`, `data/weight_schedule_hw_data.xml`, `data/weight_schedule_pr_data.xml`
- **`feed_schedule_hw_data.xml` is a strict subset of PR (383 lines):** script-verified 40/41 HW records byte-identical to PR (only day-40 qty differs 0.210 vs 0.201; PR adds days 41–60 a 41-day HW flock never reaches). Point `'HW Schedule'` lookups (`models/poultry_flock.py:357`) at PR records or keep a 1-record override.
- **`poultry_bom_data.xml` is comment-only** yet loaded in the manifest — remove file + `__manifest__.py:105` entry.

## 3. Model copy-paste (~900 lines)

- **Consumption machinery duplicated across 6 models:** `_create_landed_cost`, `_create_internal_consumption`, `_create_stock_move`, `unlink` (date-gap check), `name_get` differ only in model name / product type across flock feed/gas/medicine and growth feed/gas/medicine. Replace with one AbstractModel mixin. `models/poultry_flock_feed_consumption.py:132`, `poultry_flock_gas_consumption.py:136`, `poultry_flock_medicine_usage.py:136`, `poultry_growth_feed_consumption.py:90`, `poultry_growth_medicine_usage.py:101`, `poultry_growth_gas_consumption.py:75`
- **4 `_generate_*_from_schedule` methods duplicated** between flock and growth tracking (~240 lines each side; only the brooding-cutoff direction and record model differ). One parameterized generator. `models/poultry_flock.py:813-1053`, `models/poultry_growth_tracking.py:577-789`
- **`action_update_scheduled_data` duplicated verbatim (~100 lines)** including the notification-return dict. `models/poultry_flock.py:716`, `models/poultry_growth_tracking.py:417`
- **`_adjust_future_consumption` implemented 3×** (mortality, culling, slaughter wizard) with the same ratio math. `models/poultry_mortality.py:186`, `models/poultry_culling.py:72`, `wizards/growth_slaughter_wizard.py:184`
- **`active` field declared twice** in `poultry.flock` (`models/poultry_flock.py:38,260`)
- **Unused class attrs** (`filter_date_from = None` etc.) and dead `_get_locations_section()` in `models/poultry_reports.py:12-15`, `models/poultry_dashboard.py:381`
- **No-op `create()` overrides** just calling `super().create()` in the three flock consumption models.

## 4. Views / security (~420 lines)

- 3 unreferenced dialog forms: `poultry_feed_consumption_dialog_form`, `poultry_gas_consumption_dialog_form`, `poultry_medicine_usage_dialog_form` (`views/poultry_feed_consumption_views.xml:95`, `poultry_gas_consumption_views.xml:79`, `poultry_medicine_usage_views.xml:63`)
- Unused `poultry_flock_kanban_view` (`views/poultry_flock_views.xml:295`); unreferenced `poultry_reports_action` act_window on an AbstractModel (`views/poultry_feed_consumption_views.xml:22`)
- **Duplicate XML id `poultry_feed_consumption_action`** declared twice with contradictory `res_model`; menu_views.xml loads last and shadows the other (`views/poultry_feed_consumption_views.xml:5` vs `views/menu_views.xml:132`)
- Dead `action_stock_locations_config` (menu commented out) + `view_poultry_configuration_assist_line_form` + empty `<group invisible="not warehouse_id">` + duplicate "Create Poultry Locations" footer button (`views/poultry_configuration_assist_views.xml:45,65,78,110`)
- `purchase_order_form_view_inherit_flock` renders an empty group (`views/poultry_flock_views.xml:406`)
- **3× `'transferred'` state references that never match** (model uses `'transfer'`): list/kanban decorations + statusbar (`views/poultry_flock_views.xml:22,51,350`)
- **~150 lines of copy-pasted Feed/Gas/Medicine list blocks** across flock + growth forms (`views/poultry_flock_views.xml:195-269`, `views/poultry_growth_tracking_views.xml:213-282`)
- Two "Create Processing Order" footer buttons differing only by confirm — merge (`views/growth_slaughter_wizard_views.xml:69-78`)
- No-op context `{'search_default_is_farm_raw_material': 1}` on the raw-material action (`views/raw_material_on_hand_views.xml:26`)
- `farm_records_views.xml` triplicates one schedule list+form skeleton for feed/mortality/weight (`views/farm_records_views.xml:89-344`)
- Security: unused `group_poultry_production_user`, duplicate `access_cleaning_schedule_user` ACL row, inert ACL on abstract `poultry.reports` (`security/security_groups.xml:17`, `security/ir.model.access.csv:28,30`)

## 5. Static assets (~700 lines)

- **~318 lines dead SCSS** — `poultry_dashboard.scss:25-352` styles a card/table layout the template no longer uses; keep `.o_poultry_dashboard/.o_dashboard_header/.o_dashboard_title/.o_dashboard_loading/.o_clickable`
- **~250 lines triplicated template markup** — slaughter/feed/vaccine item blocks in `poultry_dashboard.xml:189-298,323-395,420-492`; collapse into one parameterized sub-template
- **KPI card body duplicated via t-if/t-else** (`poultry_dashboard.xml:43-72`) — one card with conditional `t-att-class`
- **Dead JS:** legacy string-action dispatch (`open_flocks`/`open_growths`/`open_locations` — backend only emits action objects), unused `openLocations`/`openLocation`, location-filter machinery behind a commented-out `<select>` (`poultry_dashboard.js:47-54,67-94,137-144`, `poultry_reports.js:29,35,94-101,150-163`, `poultry_reports.xml:74-84`)
- **`onExport` console.log stub + Export button** (`poultry_reports.js:174-177`)
- **Redundant `static props` block** — `"*": true` already accepts anything (`poultry_reports.js:8-14`)

## 6. Native replacements

- Hand-rolled `format_value`/`_format_currency` vs `currency.format` (`models/poultry_reports.py:562`, `models/poultry_dashboard.py:9`); hand-rolled `formatDate` vs `@web/core/l10n/dates` (`poultry_reports.js:74-79`)
- Architecture-level: the OWL dashboard duplicates Odoo 18's `act_dashboard` (transient-model RPC + KPI cards); the report view reimplements a list view + `window.print()` where a native list/pivot view or `ir.actions.report` would do. Not quick cuts.

## 7. Misc

- `data/cron_data.xml` ships `active=True` hourly while the method docstring says "disabled by default, enable manually" — align
- Commented-out code blocks everywhere (date constraints, byproduct % validation, `_prepare_picking`, occupancy check, serial buttons) — delete the archaeology
- README over-doc: version badge 1.2.3 vs manifest 1.5.7; 4 screenshot links + `docs/` links to nonexistent files; placeholder `yourusername` clone URL

---

## Routed to normal review (correctness — out of audit scope)

- `models/poultry_weighing.py:105-107` — `name_get` reads `flock_id.flock_code`, a field that doesn't exist on `poultry.flock` (AttributeError)
- `models/poultry_location.py:196` — reads `self.parent_location_id`, not defined
- `models/poultry_culling.py:192` — creates mortality with `reason='natural_death'`, not in the mortality `reason` selection
- `models/poultry_growth_tracking.py:1180` — `action_view_gas` opens `poultry.gas.consumption` but growth-level gas lives in `poultry.growth.gas.consumption`
- `models/stock_picking.py` — `is_backdated_receipt` computed as `has_chick_moves` (same value as `is_poultry_receipt`); backdate detection never happens
- `data/vaccination_schedule_broiler_data.xml` — all 27 lines have `quantity_per_bird` = 0 (structure real, values need completion)
- `models/poultry_flock.py` — never-called methods: `action_close`, `action_view_transfers`, `transfer_count`, `cleanup_brooding_records`

---

*Generated 2025 — one-shot ponytail-audit; no fixes applied. Verified by grep/import cross-checks and three parallel subagent passes (data, views/security, static).*
