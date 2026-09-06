LISTING = {
    "eyebrow": "Human Resources",
    "title": "Payroll for Odoo Community",
    "lede": "Salary structures, a rule engine, payslips and journal entries. The "
            "single biggest gap in Odoo Community, filled.",
    "callout": (
        "Community knows what an employee earns and stops there.",
        "<code>hr.version</code> carries the wage, and then nothing turns that wage "
        "into a payslip, a deduction or a journal entry. This module is that engine.",
    ),
    "screenshot": "A month's payroll, every figure computed by the salary rules",
    "blocks": [
        {
            "h2": "How a payslip is built",
            "bullets": [
                ("Salary structures", "an ordered list of rules, tied to a structure "
                 "type from core <code>hr</code>, so employees pick them up naturally"),
                ("Salary rules", "a fixed amount, a percentage of any base, or a "
                 "Python expression with the employee, the contract version, the other "
                 "inputs and the running category totals in scope"),
                ("Rules run in order", "a Net rule sees what Gross came to — exactly "
                 "the way a payroll officer works down a sheet"),
                ("Batches", "one payslip per employee for a period, confirmed together"),
            ],
        },
        {
            "h2": "Salary advances",
            "text": [
                "Money paid before it is earned, recovered over as many payslips as you "
                "choose. The schedule is built when the advance is approved, and each "
                "payslip claims the instalments due to it while it is still a draft — "
                "so two payslips can never take the same instalment, and cancelling one "
                "gives the instalments back.",
            ],
        },
        {
            "h2": "It posts when you tell it to",
            "text": [
                "Confirming a payslip freezes it and creates a <strong>draft</strong> "
                "journal entry for the accountant to post. Nothing reaches the ledger "
                "on its own, and a payslip whose entry is already posted refuses to be "
                "reset — you reverse the entry, so the ledger keeps a record of both.",
                "The entry is checked before it is written: if the debits and credits "
                "do not agree, the module says so and names the figures rather than "
                "posting something unbalanced.",
            ],
        },
        {
            "h2": "Printed and understood",
            "bullets": [
                ("A payslip document", "with the net pay in words, the way a wage slip "
                 "is signed for"),
                ("Advance recovery shown on the slip", "the instalment taken and what "
                 "is still owed, so the employee can see why the figure moved"),
                ("Rules can be hidden", "intermediate lines still compute and still "
                 "count toward their category, without appearing on the printed slip"),
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>hr</code>, <code>account</code> "
              "and <code>mail</code>. Afghan wage withholding is a separate module, "
              "<code>af_hr_payroll</code>.",
}
