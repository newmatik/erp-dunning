# Dunning

Frappe app for payment reminders, configurable text blocks and reminder emails.
Contributor instructions: [AGENTS.md](AGENTS.md).

### License

MIT

## Install

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
Site integration and actual email delivery require a separate development bench.
