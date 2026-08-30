# Payroll

Salary structures, a rule engine, payslips and journal entries for Odoo
Community.

---

## Why this exists

Payroll is the single biggest gap in Odoo Community. The `hr` module knows what
an employee earns — `hr.version` carries the wage — and then nothing turns that
wage into a payslip, a deduction, or a journal entry.

Odoo 19 moved some scaffolding into core: `hr.payroll.structure.type` is there,
and so is `hr.version.wage`. Everything else — structures, rules, payslips,
batches, advances and posting — is this module.

---

## How a payslip is computed

Rules run in **sequence order**, and each one sees the category totals of the
rules that ran before it. That is deliberate: it is how a payroll officer works
down a sheet, and it is what lets a Net rule read what Gross came to.

```
10  BASIC      Basic Salary        result = version.wage
20  HRA        Housing Allowance   fixed 2,000
30  GROSS      Gross               categories['BASIC'] + categories['ALW']
40  TAX        Income Tax          (a deduction, negative)
50  NET        Net                 categories['GROSS'] + categories['DED']
```

### Rule amounts

| `amount_select` | Field used | Meaning |
|---|---|---|
| `fix` | `amount_fix` | a flat figure |
| `percentage` | `amount_percentage` + `amount_percentage_base` | a share of any base expression |
| `code` | `amount_python` | Python statements that set `result` |

There is **no** `python` value, even though the field it drives is called
`amount_python`.

### Conditions and amounts are evaluated differently

```python
# condition_python — eval mode. A bare expression.
version.wage > 0

# amount_python — exec mode. Statements that assign result.
result = version.wage * 0.1
```

Writing `result = ...` in a condition is a `SyntaxError` at compute time, not
at install. In scope for both: `employee`, `version`, `payslip`, `categories`,
`inputs`.

---

## Nothing posts by itself

Confirming a payslip freezes it and creates a **draft** journal entry for the
accountant to post. Before it is written, the entry is checked:

- debits and credits must agree, or the module says so and names both figures;
- the structure's journal must belong to the payslip's company;
- a rule with accounts requires the structure to have a salary journal.

A payslip whose entry is already posted refuses to be reset. You reverse the
entry, so the ledger keeps a record of both.

---

## Salary advances

Money paid before it is earned, recovered over as many payslips as you choose.

```
Approve  →  schedule built
            each payslip claims the instalments due to it while it is a draft
            confirming the payslip actually recovers them
            cancelling the payslip gives them back
```

Claiming at draft is what stops two payslips taking the same instalment. An
instalment already recovered cannot be deleted — cancel the payslip instead, so
the money taken back is not lost from the record.

A deduction rule reads the total as:

```python
result = -inputs.get('ADVANCE', 0.0)
```

---

## Batches

Name a batch after the month, press **Generate Payslips**, and get one draft
payslip per employee, computed immediately. Employees who already have a
payslip in the batch are skipped, so pressing it twice is safe.

**Confirm All** confirms every draft in the batch and creates their journal
entries together.

---

## Groups

| Group | Can |
|---|---|
| Payroll Officer | compute and confirm payslips, run batches |
| Payroll Manager | that, plus configure structures, rules and categories |

Officer implies HR officer, because a payslip cannot be processed without
reading the employee's contract version.

---

## Which contract version is read

The version in force during the payslip period, not the latest one. A raise
given in March does not rewrite January.

---

## Compatibility

- Odoo **19.0** Community and Enterprise
- Depends on `hr`, `account`, `mail` and `hm_license`
- Afghan wage withholding is a separate module: `af_hr_payroll`
- Installation instructions: see `af_jalali/INSTALL.md`
