# Dunning

Frappe app for payment reminders, configurable text blocks and reminder emails.
Contributor instructions: [AGENTS.md](AGENTS.md).

## Status: retired

Newmatik no longer runs this app. ERPNext has shipped its own `Dunning` DocType
since v13, and Newmatik moved its records to it when it migrated to ERPNext v16.
The repository is kept as a historical reference:

- `version-14` is the last state that ran in production.
- `main` has no deployment target. A merge here changes no running system.
- Do not install the app on ERPNext v15 or later: it would shadow the core
  `Dunning` DocType, and `dunning.py` still imports `six`, which current Frappe
  no longer installs.

### License

MIT

## Install (ERPNext v14 and earlier only)

```
cd ~/frappe/bench
bench get-app dunning https://github.com/newmatik/erp-dunning.git
bench --site [mysite] install-app dunning
```

## Offline tests

From this checkout, with Python 3.14:

```sh
python -m unittest dunning.dunning.doctype.dunning.test_dunning -v
```

CI runs these tests for pull requests and pushes to `main`. They mock Frappe's
database and mail functions: no site, credentials or outgoing email is needed.
They stub `six` as well, so a green run does not show that the app imports on a
current bench. Site integration and actual email delivery require a separate
development bench on ERPNext v14 or earlier.
