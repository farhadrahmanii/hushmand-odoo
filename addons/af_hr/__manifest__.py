# Part of af_hr. See LICENSE file for full copyright and licensing details.
{
    "name": "Afghanistan HR",
    "summary": "Tazkira, father and grandfather names, Afghan addresses, "
               "ID cards and disciplinary actions",
    "description": """
Afghanistan HR
==============

Afghan employee records need things Odoo's HR does not carry, and this module
adds them where they belong rather than bolting them on.

**Names that identify a person.** Afghan names have no inherited surname.
Someone is identified by their own name plus their father's and grandfather's,
and every official document is issued that way.

**The tazkira as it actually is.** A paper tazkira is identified by volume,
page and registration entry together, not by one serial number. An electronic
one has a national identity number instead. Both are in circulation, so both
are recorded rather than forcing one into the other's shape.

**Addresses two levels deeper than Odoo goes.** Province, district and
village, for where someone lives now and where they are from, which are
different questions on every Afghan employment file.

**Disciplinary actions.** Odoo has no equivalent in either edition. Verbal
through to termination, with issue and acknowledgement tracked separately,
because whether the employee actually saw it is the part that matters later.

**Employee ID cards**, printed from the employee record.

Everything is stored on the employee's version, so a corrected name or a
change of address becomes history instead of overwriting what the record said
before.
""",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["hr", "af_l10n_base"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/af_employee_discipline_views.xml",
        "views/hr_employee_views.xml",
        "report/af_employee_id_card.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
