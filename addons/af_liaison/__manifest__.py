# Part of af_liaison. See LICENSE file for full copyright and licensing details.
{
    "name": "Afghanistan Liaison Documents",
    "summary": "Visas, work permits, vehicle permits, weapon licences, "
               "membership and CIP cards, with renewal reminders",
    "description": """
Afghanistan Liaison Documents
=============================

An Afghan liaison office spends most of its time keeping six kinds of document
from lapsing: visas, work permits, vehicle permits, weapon licences,
membership cards and airport CIP cards.

This module is deliberately thin. The tracking, the reminders and the renewal
chain all come from **Expiring Documents**, because a visa and a vehicle
registration are the same shape and did not need six separate models. What is
added here is what is actually specific to the context:

* the six document types, ready configured with sensible notice periods;
* a link to the **employee**, so an expiring permit shows on their record and
  a warning appears on the employee form;
* the issuing **province**, and the official reference the issuing office
  quotes when you ring them about it.

The person reminded is the one named responsible, which in a liaison office is
the officer who has to do the renewing -- not the employee whose permit it is.
""",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Farhad Rahmani",
    "website": "https://hushmand.af",
    "license": "OPL-1",
    "depends": ["hm_expiry_docs", "hr", "af_l10n_base"],
    "data": [
        "data/af_document_type_data.xml",
        "views/af_liaison_views.xml",
    ],
    "demo": [
        "demo/af_liaison_demo.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
