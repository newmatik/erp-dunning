# Dunning

This Frappe app owns the Dunning DocType, reminder text blocks and payment
reminder email templates. Read `README.md` for installation and offline tests.

- Preserve the existing DocType, hook and whitelisted-method contracts.
- Payment reminders send real email and attach invoice documents. Never invoke
  live reminder methods during maintenance; tests mock Frappe and email delivery.
- Keep customer data and credentials out of the repository and test fixtures.
- Run `python -m unittest dunning.dunning.doctype.dunning.test_dunning -v`.
  This suite needs neither a Frappe installation nor a site; CI runs Python 3.14.
  Passing it does not validate a live bench or delivery to a mail server.
- Follow existing Python formatting. Use Conventional Commits and base changes
  on `main`. `CLAUDE.md` is a pointer to these canonical instructions.
