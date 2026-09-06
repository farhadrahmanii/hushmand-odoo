# Brief for a translator

Two jobs, either of which can be taken on its own.

| Job | Size | State |
|---|---|---|
| **Review the Dari (`fa_AF`)** | 2,051 terms | Drafted by an AI. Fluent and consistent, **not verified**. Needs a native speaker to correct it. |
| **Translate the Pashto (`ps_AF`)** | 2,051 terms | Not started. Nobody has written a word of it. |

Roughly a third of the 2,051 are distinct; the rest repeat across modules and
are filled in automatically once translated one time.

---

## What the software is

Twenty-one Odoo modules sold to organisations operating in Afghanistan —
payroll, HR, procurement, accounting, timesheets, a zakat register, a
correspondence (maktoob) register. The interface is what an accountant, an HR
officer or a payroll clerk reads every day.

The audience is Afghan offices: ministries, NGOs, private companies. **Not
Iranian users.** That distinction drives most of the decisions below.

---

## This is not Iranian Persian

An Afghan reader notices immediately, and the words that give it away are the
ones an ERP puts on every screen. Where an Afghan form differs from the
Iranian one, the Afghan form wins.

| English | Used here | Rejected |
|---|---|---|
| Province | ولایت | استان — Iranian administrative language |
| District | ولسوالی | بخشداری — does not exist in Afghanistan |
| Village | قریه | روستا — Iranian |
| Number | نمبر | شماره — Afghan documents say نمبر |
| Salary | معاش | حقوق — Iranian usage |
| Currency | اسعار | ارز — Afghan banks say اسعار |
| Draft | مسوده | پیش‌نویس — Iranian |
| Journal | روزنامچه | the Afghan accounting term, in the tax law |
| Code | کود | کد — Iranian orthography |
| Phone | تیلفون | تلفن — Iranian orthography |
| Website | ویب‌سایت | وب‌سایت — Iranian orthography |
| Monthly | ماهوار | ماهانه — Iranian |
| Quarterly | ربع‌وار | فصلی — Iranian |
| Position | بست | the Afghan establishment post |
| Purchase | خریداری | خرید alone reads as retail shopping |
| Manager | آمر | مدیر — آمر is the Afghan administrative title |
| Timesheet | تایم‌شیت | the borrowed word Afghan offices actually write |

**Please challenge any of these.** They were chosen with care but not by a
native speaker, and the whole point of the review is that you know better.

### Approve is not Confirm

The catalogue keeps these apart deliberately:

- **تأیید** — confirming a fact
- **منظوری** — an authority granting permission

An approval chain grants منظوری. A user confirming their own entry gives
تأیید. Collapsing them makes the approvals module read as though every step
were clerical.

---

## What must not be translated

Leave these exactly as they are. Translating them does not produce awkward
wording — it produces a crash, or a date that prints as its own pattern:

- Format patterns: `yyyy/MM/dd`, `yyyy/MM/dd HH:mm`
- Field paths: `employee_id`, `employee_id.parent_id.user_id`, `sheet_id`,
  `amount_total`, `fund_id`
- Expressions: `'Payslip - %s' % (object.number or object.employee_id.name)`
- Icon names inside help text, such as `fa-tasks`

### Placeholders must survive

Some strings contain `%s`, `%(week)s`, `%(days)s`. Every one that appears in
the English **must appear in your translation**, spelled identically. They are
replaced with real values at run time; a missing one raises an error in front
of the user. Word order can change freely — `%(name)s` may go anywhere in the
sentence.

The build refuses any translation whose placeholders do not match the source,
so a mistake here is caught rather than shipped.

---

## How to do the work

You receive one `.po` file per module, 21 of them. They are plain text and
open in any PO editor — Poedit is free and the usual choice — or in a text
editor.

Each entry looks like this:

```
#: model:ir.model.fields,field_description:hm_payroll.field_hm_payslip__number
msgid "Reference"
msgstr ""
```

Fill in `msgstr`. Leave `msgid` alone. The `#:` line above says where the term
appears, which is often the fastest way to work out what it means.

**Context matters more than usual.** "State" is a status, not a country.
"Post" is an accounting action in one module and a guard's post in another —
those two are already flagged and handled separately, but tell us if you find
more like them.

Send the files back and they are folded in automatically; every module then
picks up your wording for the terms it shares.

---

## What happens after

The translations are compiled into the product and checked by an automated
build: it verifies that every term still matches the source text, that
placeholders survived, and — for Dari — that the interface really renders
right-to-left with your words in it rather than falling back to English.

If something you translated does not appear in the running software, that is a
bug on our side, not yours. Tell us.

---

## Questions worth asking us

- Is a term a noun or a button? Ask; we can tell you where it appears.
- Two English words that should be one word in Dari or Pashto, or the reverse?
  Say so — the source text can be changed.
- Is the English itself unclear? That is worth knowing before a customer reads
  it in either language.
