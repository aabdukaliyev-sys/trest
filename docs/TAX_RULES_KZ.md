# Kazakhstan investor tax rules used by this calculator

This document lists the assumptions `tax_optimizer/kz_tax_rules.py` is built
on. It is a working summary for building the calculator, **not a substitute
for the Tax Code text or professional advice**. Rates and conditions below
reflect a general reading of the Tax Code of the Republic of Kazakhstan for a
tax-resident individual investing through a licensed broker; always confirm
the current wording and your own facts before filing.

## Flat individual income tax (ИПН) rate

- 10% on most individual income, including capital gains and dividends
  handled by this calculator (Tax Code, Art. 320).

## Capital gains on securities (прирост стоимости при реализации ценных бумаг)

- Gain = sale proceeds − cost basis (both converted to KZT at the NBK rate on
  the transaction date) − brokerage commissions on the buy and sell legs.
- **Exemption**: gains on shares that are in the official list of a stock
  exchange operating in Kazakhstan (KASE) *at the date of sale* are exempt
  from ИПН (Art. 341). For KZ-resident issuers there is an additional
  condition that the issuer's assets are not more than 50% attributable to
  subsoil users at the date of sale — this calculator cannot verify that
  condition automatically, so it relies on a `kase_official_list` flag you
  set per trade after confirming eligibility with your broker.
- Realized losses on non-exempt securities net against realized gains on
  other non-exempt securities within the same tax period. A net loss:
  - is **not** usable against other categories of income (salary, rent, etc.);
  - is **not** carried forward to future tax years for an individual.
  This is why the calculator floors the taxable gain at zero and simply notes
  the unused loss rather than trying to "bank" it.
- Exempt (KASE-listed) trades are kept out of the taxable netting pool
  entirely — an exempt loss does not reduce taxable gains, and an exempt gain
  is not taxed.

## Dividends

- Taxed at the same flat 10% ИПН rate unless exempt.
- **Exemptions** modeled here:
  - dividends on shares in the KASE official list at payment date, and
  - dividends on shares held for 3 years or more (`holding_period_years >= 3`).
  Both mirror exemption grounds in Art. 341; verify the exact conditions
  (e.g. minimum free-float, issuer requirements) with your broker.
- **Foreign tax credit**: tax withheld abroad (e.g. US dividend withholding)
  is credited against the KZ tax on the same dividend, capped at the KZ tax
  amount — Kazakhstan does not refund foreign tax in excess of its own tax on
  that income. Claiming the credit requires supporting documents from the
  broker and is done via the annual return.

## Filing mechanics

- KZT-source income paid through a KZ-licensed broker may already have ИПН
  withheld and remitted by the broker acting as a tax agent.
- Foreign-source income (most notably gains/dividends on foreign shares
  bought via international access) is generally self-declared by the
  individual on Form 240.00, due 31 March of the year following the tax year,
  with tax payable by 10 April. Confirm with your broker exactly which
  amounts they withhold vs. which you must self-report.

## What this calculator deliberately does NOT do

- It does not verify KASE official-list status or the subsoil-user asset test
  — you provide that as an input flag.
- It does not model corporate-level or entrepreneurial income tax, VAT, or
  property tax.
- It does not model social tax / pension contributions.
- It does not know current NBK exchange rates — you supply `fx_rate_to_kzt`
  per transaction (use the NBK official rate for that date).

Treat every number this tool produces as a draft for your own or your
accountant's review, not a filed figure.
