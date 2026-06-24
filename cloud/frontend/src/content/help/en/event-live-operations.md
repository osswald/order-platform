Once an event has status **Test**, **Live**, or **Completed**, additional operational tabs appear in event configuration. These are for reporting — changes still happen in the configuration sections.

## When tabs are visible

| Tab | Requirement |
|-----|-------------|
| Sales, collective bills | Status ≠ Configuration |
| Transactions | Status test, live, or completed |
| Shifts | Same as transactions + registers/shift settlement enabled |
| Bookkeeping | Same as sales + accounts enabled on organisation |

In **Configuration** status only setup sections (stations, layouts, etc.) are available.

## Sales

Overview of sales status:

- Order count, line value, paid, open
- Breakdown by waiter and station
- **Refresh** loads the latest data from the server

## Collective bills

List and status of collective bills for the event. Useful for billing regular customers or internal accounts.

## Transactions

Chronological log of all payments and relevant operations. Helps trace individual payments or voids.

## Shifts (cash sessions)

When registers and shift settlement are enabled:

- Open and closed cash sessions
- Opening float, sales, and variances per shift

## Bookkeeping

When the organisation has accounts enabled:

- Summary and detail postings
- Debit/credit, tax codes, net/VAT/gross
- Link to collective bills where applicable

## Notes

- Operational tabs are **read-only** — configuration stays in setup sections
- Data comes from Pi sync; use **Refresh** if delayed
- For event setup see **Set up an event**
