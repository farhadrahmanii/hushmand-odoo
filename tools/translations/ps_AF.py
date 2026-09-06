# Part of the Hushmand Odoo addons. Pashto (ps_AF) translation memory.
"""Pashto, awaiting a translator.

This file is deliberately almost empty, and that is the honest state of the
Pashto translation. The Dari memory beside it was drafted by an AI and is
labelled a draft for a native speaker to correct. The same was not done here:
producing 2,000 plausible-looking Pashto strings nobody could vouch for would
be worse than producing none, because a reviewer skimming fluent-looking text
approves errors that an empty file would have forced them to write properly.

What is here is everything that does not need a Pashto speaker: the terms that
must not be translated at all, and the workflow, so that the day a translator
is engaged the job is filling in words rather than working out a process.

    python tools/build_po.py ps_AF        # writes addons/*/i18n/ps_AF.po

Read ``docs/TRANSLATOR-BRIEF.md`` first, then this file's Dari counterpart —
``fa_AF.py`` — whose docstring explains every Afghan-versus-Iranian decision
the catalogue has already made. Pashto has the same decisions to make and the
reasoning transfers even where the words do not.

Decisions a Pashto translator has to make, which Dari has already made
---------------------------------------------------------------------

============  =======================  ====================================
English       Dari chose               Note for Pashto
============  =======================  ====================================
Province      ولایت                    the Afghan administrative unit
District      ولسوالی                  ditto; not the Iranian form
Village       قریه                     کلی is the usual Pashto word
Number        نمبر                     Afghan documents say نمبر, not شماره
Salary        معاش                     shared with Dari in Afghan usage
Draft         مسوده                    the Afghan administrative term
Approve       منظوری                   kept distinct from تأیید (Confirm)
Confirm       تأیید                    a fact confirmed, not permission given
Timesheet     تایم‌شیت                  the borrowed word Afghan offices write
Manager       آمر                      the Afghan administrative title
============  =======================  ====================================

The Approve/Confirm distinction matters most. Afghan administrative practice
separates granting permission from confirming a fact, and collapsing the two
makes the whole approvals module read as clerical.
"""

#: Terms that must survive untranslated in every language: date and time
#: format patterns, field paths the approval engine evaluates, and a report's
#: print-name expression. Translating any of these does not produce bad
#: Pashto -- it produces a crash, or a date that renders as its own pattern.
#:
#: Copied from the Dari memory rather than derived, so the two languages
#: cannot disagree about what is a word and what is code.
VERBATIM = {
    "'ID Card - %s' % (object.name)",
    "'Payslip - %s' % (object.number or object.employee_id.name)",
    "'Timesheet - %s' % (object.employee_id.name or '')",
    'amount_total',
    'employee_id',
    'employee_id.parent_id.user_id',
    'fund_id',
    'hm_contract_id',
    'hm_request_id',
    'sheet_id',
    'yyyy/MM/dd',
    'yyyy/MM/dd HH:mm',
}

#: Empty, and honestly so. Add entries as a Pashto speaker supplies them, or
#: let them edit addons/<module>/i18n/ps_AF.po directly and run
#: ``python tools/build_po.py ps_AF --harvest`` to fold their wording back in
#: here, where every other module picks it up.
TRANSLATIONS = {}
