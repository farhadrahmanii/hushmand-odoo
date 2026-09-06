#!/usr/bin/env python
"""Open every module's main screen in a real browser, and photograph it.

    python tools/take_screenshots.py --base-url http://localhost:8069
    python tools/take_screenshots.py --lang fa_AF --out screenshots/dari

This is a smoke test first and a source of listing images second.

The test suite proves the models behave. It does not prove a single screen
renders: a broken xpath, a field removed from a view, an OWL component that
throws on mount -- all install cleanly, pass every test, and greet the customer
with an empty page or a red dialog. Nothing in CI opened a screen until this.

So a failure here is a failure. The script exits non-zero if a page shows
Odoo's error dialog, logs a client-side traceback, or renders no view at all.
The PNGs it leaves behind are a by-product that happens to be what the listing
pages need.
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import screenshot_trim  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("This tool needs playwright:\n"
             "    pip install playwright && playwright install chromium")

#: One screen per module: the thing a customer opens first. Modules that
#: define no action of their own are photographed through the screen they
#: actually contribute to, which is the honest picture of what they do.
SCREENS = [
    ("af_correspondence", "af_correspondence.action_af_correspondence", "Correspondence register"),
    ("af_dual_currency", "af_dual_currency.action_af_exchange_period", "Exchange periods"),
    ("af_hr", "af_hr.action_af_employee_discipline", "Disciplinary actions"),
    ("af_hr_payroll", "af_hr_payroll.action_af_income_tax_scale", "Income tax scale"),
    ("af_jalali", "base_setup.action_general_configuration", "Jalali settings"),
    ("af_l10n_account", "account.action_account_form", "Afghan chart of accounts"),
    ("af_l10n_base", "af_l10n_base.action_af_district", "Districts"),
    ("af_liaison", "hm_expiry_docs.action_hm_expiry_document", "Liaison documents"),
    ("af_procurement", "af_procurement.action_af_comparative_form", "Comparative forms"),
    ("af_zakat", "af_zakat.action_af_zakat_fund", "Zakat funds"),
    ("hm_account_reports", "hm_account_reports.action_hm_account_report", "Financial reports"),
    ("hm_approvals", "hm_approvals.action_hm_approval_request", "Approval requests"),
    ("hm_assets", "hm_assets.action_hm_asset", "Fixed assets"),
    ("hm_contracts", "hm_contracts.action_hm_contract", "Service contracts"),
    ("hm_expiry_docs", "hm_expiry_docs.action_hm_expiry_document", "Expiring documents"),
    ("hm_frontdesk", "hm_frontdesk.action_hm_visitor_on_site", "On site now"),
    ("hm_license", "hm_license.action_hm_license", "Licences"),
    ("hm_payroll", "hm_payroll.action_hm_payslip", "Payslips"),
    ("hm_purchase_request", "hm_purchase_request.action_hm_purchase_request", "Purchase requests"),
    ("hm_roster", "hm_roster.action_hm_roster", "Rosters"),
    ("hm_timesheet", "hm_timesheet.action_hm_timesheet_sheet_all", "Timesheets"),
]

VIEWPORT = {"width": 1600, "height": 1000}

#: Odoo renders its crash dialog with these. Seeing one means the screen is
#: broken for the customer, whatever the tests said.
ERROR_SELECTORS = [
    ".o_error_dialog",
    ".o_dialog_error",
    ".modal-content:has-text('Odoo Error')",
    ".modal-content:has-text('Traceback')",
]

#: Something that proves a view actually mounted, rather than a blank shell.
VIEW_SELECTORS = ".o_list_view, .o_form_view, .o_kanban_view, .o_calendar_view, .o_graph_view, .o_pivot_view, .o_setting_container, .o_content"


def log_in(page, base_url, password):
    """Log in and wait for the web client, not for the network.

    Never wait for "networkidle" against Odoo: the bus holds a long poll open
    for the life of the session, so the network is never idle and the wait can
    only ever time out.
    """
    page.goto("%s/web/login" % base_url, wait_until="domcontentloaded")
    page.fill("input[name='login']", "admin")
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    try:
        page.wait_for_selector(".o_main_navbar", timeout=60000)
    except Exception:
        alert = page.locator(".alert-danger")
        detail = alert.first.inner_text() if alert.count() else "still at %s" % page.url
        raise SystemExit("Could not log in as admin: %s" % detail.strip())


def check_rtl(page):
    """Prove the run really is in a right-to-left language.

    Without this the pass is a photo opportunity: if the language failed to
    activate, or the user's lang did not take, the browser cheerfully produces
    twenty perfectly good English screenshots in a directory named fa_AF, and
    the right-to-left layout stays untested while looking tested.

    So two things are asserted -- the document direction flipped, and the
    interface is actually showing translated text rather than falling back to
    the English source.
    """
    # The computed direction, not the dir attribute. Odoo renders <html> from
    # a t-att dict that need not carry dir at all, and expresses right-to-left
    # through generated RTL stylesheets instead. What matters is how the page
    # actually lays out, which is what getComputedStyle reports however it was
    # arrived at.
    direction = page.evaluate("getComputedStyle(document.body).direction")

    # The navbar element exists before its menus are in it: the web client
    # fetches them separately, and on a slow runner the bar reads as
    # "1 | YourCompany" for a second or so. Reading it straight after login
    # therefore fails an assertion the interface is about to satisfy, so wait
    # for the menus rather than for the element that will hold them.
    try:
        page.wait_for_function(
            "() => { const nav = document.querySelector('.o_main_navbar');"
            " if (!nav) return false;"
            " return [...nav.innerText].some(c => c.charCodeAt(0) >= 0x0600"
            " && c.charCodeAt(0) <= 0x06FF); }",
            timeout=20000,
        )
    except Exception:
        pass  # Report it below, with everything else that is known.

    navbar = page.locator(".o_main_navbar").inner_text()
    translated = any("؀" <= character <= "ۿ" for character in navbar)

    if direction == "rtl" and translated:
        return

    # Report both facts at once. Told only the first, the next run diagnoses
    # the second, and each round trip through CI costs four minutes.
    raise SystemExit(
        "Expected a translated right-to-left interface.\n"
        "  computed direction : %s\n"
        "  menus translated   : %s\n"
        "  menu text          : %r"
        % (direction, translated, navbar[:160].replace("\n", " | "))
    )


def capture(page, base_url, module, action, label, out_dir, console_errors):
    target = "%s/odoo/action-%s" % (base_url, action)
    problems = []

    console_errors.clear()
    page.goto(target, wait_until="domcontentloaded")
    try:
        page.wait_for_selector(VIEW_SELECTORS, timeout=25000)
    except Exception:
        problems.append("no view rendered")

    # Let charts, kanban images and lazy columns settle before the shutter.
    page.wait_for_timeout(1200)

    for selector in ERROR_SELECTORS:
        try:
            if page.locator(selector).count():
                problems.append("error dialog: %s" % selector)
                break
        except Exception:
            pass

    if console_errors:
        problems.append("console: %s" % console_errors[0][:160])

    out_dir.mkdir(parents=True, exist_ok=True)
    shot = out_dir / ("%s.png" % module)
    page.screenshot(path=str(shot), full_page=False)
    # A browser window is 1000px tall and a list of three rows is not. Trim
    # here so the artifact is already the shape a listing page wants.
    screenshot_trim.trim(shot)
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8069")
    parser.add_argument("--password", default="admin")
    parser.add_argument("--out", default="screenshots")
    parser.add_argument("--lang", help="only used to label the run")
    parser.add_argument("--only", nargs="*", help="limit to these modules")
    parser.add_argument("--expect-rtl", action="store_true",
                        help="fail unless the web client is actually rendering "
                             "right-to-left, in a language that is not English")
    args = parser.parse_args()

    out_dir = pathlib.Path(args.out)
    screens = [s for s in SCREENS
               if not args.only or s[0] in args.only]

    failures = {}
    with sync_playwright() as play:
        browser = play.chromium.launch(args=["--no-sandbox"])
        context = browser.new_context(viewport=VIEWPORT, locale="en-US")
        page = context.new_page()

        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text)
                if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        log_in(page, args.base_url, args.password)

        if args.expect_rtl:
            check_rtl(page)

        for module, action, label in screens:
            problems = capture(page, args.base_url, module, action, label,
                               out_dir, console_errors)
            status = "ok" if not problems else "; ".join(problems)
            print("%-22s %-46s %s" % (module, label, status))
            if problems:
                failures[module] = problems

        browser.close()

    print()
    print("%d screen(s) photographed into %s%s"
          % (len(screens), out_dir, " [%s]" % args.lang if args.lang else ""))
    if failures:
        for module, problems in failures.items():
            print("::error::%s: %s" % (module, "; ".join(problems)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
