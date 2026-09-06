LISTING = {
    "eyebrow": "Human Resources · Localization",
    "title": "Afghanistan Liaison Documents",
    "lede": "Visas, work permits, vehicle permits, weapon licences, membership cards "
            "and airport CIP cards — the six things an Afghan liaison office spends "
            "most of its time keeping from lapsing.",
    "callout": (
        "This module is deliberately thin.",
        "The tracking, the reminders and the renewal chain all come from "
        "<strong>Expiring Documents</strong>, because a visa and a vehicle "
        "registration are the same shape and did not need six separate models.",
    ),
    "screenshot": "Visas, permits and licences, with what expires when",
    "blocks": [
        {
            "h2": "What it actually adds",
            "bullets": [
                ("The six document types", "ready configured, with sensible notice "
                 "periods already set"),
                ("A link to the employee", "so an expiring permit shows on their record "
                 "and a warning appears on the employee form"),
                ("The issuing province", "which office issued it, when you need to go "
                 "back to them"),
                ("The official reference", "the maktoob or file number the issuing "
                 "office quotes when you ring about it"),
            ],
        },
        {
            "h2": "Who gets reminded",
            "text": [
                "The person named responsible — which in a liaison office is the officer "
                "who has to do the renewing, not the employee whose permit it is.",
                "That distinction is the difference between a reminder that produces "
                "action and one that produces a forwarded email.",
            ],
        },
        {
            "h2": "Why not six modules",
            "text": [
                "Because they would have been six copies of the same reminder logic, "
                "the same renewal chain and the same status refresh — and the sixth one "
                "would have been the one where the bug lived. Everything general is in "
                "Expiring Documents; this carries only what is specific to the context.",
            ],
        },
    ],
    "footer": "Odoo 19.0 Community · depends on <code>hm_expiry_docs</code>, "
              "<code>hr</code> and <code>af_l10n_base</code>.",
}
