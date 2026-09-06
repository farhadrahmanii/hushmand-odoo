LISTING = {
    "eyebrow": "Localization",
    "title": "Afghanistan Localization Base",
    "lede": "The geography and identity fields every Afghan organisation needs, as "
            "real data rather than free-text boxes — 34 provinces, 546 districts, "
            "tazkira and TIN, in English, Dari and Pashto.",
    "callout": (
        "This is the foundation.",
        "Provinces are loaded as Odoo country states, so they work in every address "
        "Odoo already has — partners, employees, invoices, delivery addresses — with "
        "nothing else to configure.",
    ),
    "screenshot": "All 34 provinces, with their districts counted",
    "blocks": [
        {
            "h2": "What is loaded",
            "table": {
                "head": ["Data", "Count", "Languages"],
                "rows": [
                    ["Provinces (as country states)", "34", "English, Dari, Pashto"],
                    ["Districts", "546", "English, Dari, Pashto"],
                    ["Villages", "structure only — see below", "—"],
                ],
            },
        },
        {
            "h2": "Also included",
            "bullets": [
                ("Dari and Pashto as Odoo languages", "Odoo ships Persian and nothing "
                 "else from the region, so without this a customer cannot select their "
                 "own language at all"),
                ("Tazkira and TIN on contacts", "recorded as fields, not as a note"),
                ("Afghan address layout", "on printed documents, including the "
                 "district"),
                ("ISO 3166-2:AF codes", "the published ones, so the data lines up with "
                 "anyone else's"),
            ],
        },
        {
            "h2": "Where the data comes from",
            "text": [
                "The province and district lists come from a production ERP that has "
                "been in daily use in Afghanistan for years, not from a scrape.",
                "The village list starts <em>empty on purpose</em>. No reliable public "
                "dataset of Afghan villages exists, and shipping invented place names "
                "into a system people make decisions with would be worse than shipping "
                "none. The structure is there; you add the villages you actually work "
                "in.",
            ],
        },
    ],
    "footer": "Odoo 19.0 · depends on <code>base</code> and <code>contacts</code>.",
}
