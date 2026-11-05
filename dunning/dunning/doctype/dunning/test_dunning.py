# -*- coding: utf-8 -*-
# Copyright (c) 2019, Alyf and Contributors
# See license.txt
"""Test the whitelisted helpers of the Dunning DocType without a site."""
from __future__ import unicode_literals

import sys
import types
import unittest
from unittest import mock


def _load_module():
	"""Import dunning.py, stubbing only the dependencies that are not installed."""
	try:
		import frappe  # noqa: F401
	except ImportError:
		frappe_stub = types.ModuleType("frappe")
		frappe_stub.whitelist = lambda *a, **k: (lambda fn: fn)
		frappe_stub._ = lambda s: s
		frappe_stub.PermissionError = type("PermissionError", (Exception,), {})
		model = types.ModuleType("frappe.model")
		document = types.ModuleType("frappe.model.document")
		document.Document = type("Document", (), {})
		sys.modules.update({
			"frappe": frappe_stub,
			"frappe.model": model,
			"frappe.model.document": document,
		})
	try:
		import six  # noqa: F401
	except ImportError:
		six_stub = types.ModuleType("six")
		six_stub.string_types = (str,)
		sys.modules["six"] = six_stub
	from dunning.dunning.doctype.dunning import dunning
	return dunning


dunning = _load_module()


class TestGetTextBlock(unittest.TestCase):
	def test_renders_both_blocks_and_parses_json_doc(self):
		block = types.SimpleNamespace(top_text_block="top", bottom_text_block="bottom")
		with mock.patch.object(dunning.frappe, "db", create=True, new_callable=mock.MagicMock) as db, \
				mock.patch.object(dunning.frappe, "render_template", create=True,
					side_effect=lambda text, doc: "%s:%s" % (text, doc["name"])) as render:
			db.get_value.return_value = block
			result = dunning.get_text_block("Type A", "de", '{"name": "DUN-1"}')

		self.assertEqual(result, {"top_text_block": "top:DUN-1", "bottom_text_block": "bottom:DUN-1"})
		self.assertEqual(render.call_count, 2)
		self.assertEqual(db.get_value.call_args[0][1], {"parent": "Type A", "language": "de"})

	def test_returns_none_without_matching_block(self):
		with mock.patch.object(dunning.frappe, "db", create=True, new_callable=mock.MagicMock) as db:
			db.get_value.return_value = None
			self.assertIsNone(dunning.get_text_block("Type A", "fr", {"name": "DUN-1"}))


class _Thrown(Exception):
	"""Stand in for the exception frappe.throw raises."""


class TestSendPaymentReminderEmail(unittest.TestCase):
	def _run(self, language, email):
		values = {
			("Sales Invoice", "SINV-1"): types.SimpleNamespace(customer="C1", contact_person="P1"),
			("Customer", "C1"): language,
			("Contact", "P1"): email,
		}
		patches = {
			"db": mock.DEFAULT, "attach_print": mock.DEFAULT, "sendmail": mock.DEFAULT,
			"msgprint": mock.DEFAULT, "throw": mock.DEFAULT, "get_doc": mock.DEFAULT,
		}
		with mock.patch.multiple(dunning.frappe, create=True, new_callable=mock.MagicMock, **patches) as m:
			m["db"].get_value.side_effect = lambda doctype, name, *a, **k: values[(doctype, name)]
			m["attach_print"].side_effect = lambda doctype, name, **k: {"fname": name}
			m["throw"].side_effect = _Thrown
			m["docs"] = []

			def get_doc(doctype, name, *args, **kwargs):
				doc = mock.Mock()
				doc.doctype = doctype
				doc.name = name
				if doctype == "Dunning":
					doc.sales_invoice = "SINV-1"
				m["docs"].append(doc)
				return doc

			m["get_doc"].side_effect = get_doc
			try:
				dunning.send_payment_reminder_email("SINV-1", "DUN-1")
			except _Thrown:
				m["raised"] = True
			return m

	def test_german_customer_gets_german_template(self):
		m = self._run("de", "a@example.com")
		kwargs = m["sendmail"].call_args[1]
		self.assertEqual(kwargs["template"], "zahlungserinnerung")
		self.assertEqual(kwargs["subject"], "Zahlungserinnerung SINV-1")
		self.assertEqual(kwargs["recipients"], "a@example.com")
		self.assertEqual(kwargs["attachments"], [{"fname": "SINV-1"}, {"fname": "DUN-1"}])
		m["throw"].assert_not_called()

	def test_other_language_gets_english_template(self):
		m = self._run("en", "a@example.com")
		kwargs = m["sendmail"].call_args[1]
		self.assertEqual(kwargs["template"], "payment_reminder")
		self.assertEqual(kwargs["subject"], "Payment Reminder SINV-1")

	def test_missing_email_throws_and_sends_nothing(self):
		m = self._run("en", None)
		self.assertTrue(m.get("raised"), "frappe.throw must propagate")
		m["sendmail"].assert_not_called()
		m["throw"].assert_called_once()

	def test_requires_read_on_dunning_and_linked_invoice(self):
		m = self._run("en", "a@example.com")
		self.assertEqual(
			[(call.args[0], call.args[1]) for call in m["get_doc"].call_args_list],
			[("Dunning", "DUN-1"), ("Sales Invoice", "SINV-1")],
		)
		for doc in m["docs"]:
			doc.check_permission.assert_called_once_with("read")

	def test_missing_dunning_sends_nothing(self):
		m = self._call(get_doc=mock.Mock(side_effect=_Missing("gone")))
		self.assertIs(m["error"], _Missing)
		m["sendmail"].assert_not_called()
		m["attach_print"].assert_not_called()
		m["db"].get_value.assert_not_called()

	def test_blank_dunning_name_sends_nothing(self):
		m = self._call(doc_name="")
		self.assertIs(m["error"], _Thrown)
		m["get_doc"].assert_not_called()
		m["sendmail"].assert_not_called()
		self.assertIs(m["throw"].call_args[0][1], dunning.frappe.PermissionError)

	def test_unreadable_dunning_sends_nothing(self):
		def get_doc(doctype, name, *args, **kwargs):
			if doctype != "Dunning":
				raise AssertionError(doctype)
			doc = mock.Mock()
			doc.sales_invoice = "SINV-1"
			doc.check_permission.side_effect = _Denied("no")
			return doc

		m = self._call(get_doc=get_doc)
		self.assertIs(m["error"], _Denied)
		m["sendmail"].assert_not_called()
		m["attach_print"].assert_not_called()
		m["db"].get_value.assert_not_called()

	def test_invoice_not_linked_to_dunning_sends_nothing(self):
		def get_doc(doctype, name, *args, **kwargs):
			if doctype != "Dunning":
				raise AssertionError(doctype)
			doc = mock.Mock()
			doc.sales_invoice = "SINV-OTHER"
			return doc

		m = self._call(get_doc=get_doc, sales_invoice="SINV-1")
		self.assertIs(m["error"], _Thrown)
		m["get_doc"].assert_called_once_with("Dunning", "DUN-1")
		m["sendmail"].assert_not_called()
		m["attach_print"].assert_not_called()
		m["db"].get_value.assert_not_called()
		self.assertIs(m["throw"].call_args[0][1], dunning.frappe.PermissionError)

	def test_unreadable_invoice_sends_nothing(self):
		def get_doc(doctype, name, *args, **kwargs):
			doc = mock.Mock()
			if doctype == "Dunning":
				doc.sales_invoice = "SINV-1"
			elif doctype == "Sales Invoice":
				doc.check_permission.side_effect = _Denied("no")
			else:
				raise AssertionError(doctype)
			return doc

		m = self._call(get_doc=get_doc)
		self.assertIs(m["error"], _Denied)
		self.assertEqual(
			[(call.args[0], call.args[1]) for call in m["get_doc"].call_args_list],
			[("Dunning", "DUN-1"), ("Sales Invoice", "SINV-1")],
		)
		m["sendmail"].assert_not_called()
		m["attach_print"].assert_not_called()
		m["db"].get_value.assert_not_called()

	def _call(self, sales_invoice="SINV-1", doc_name="DUN-1", get_doc=None):
		patches = {
			"db": mock.DEFAULT, "attach_print": mock.DEFAULT, "sendmail": mock.DEFAULT,
			"msgprint": mock.DEFAULT, "throw": mock.DEFAULT, "get_doc": mock.DEFAULT,
		}
		with mock.patch.multiple(dunning.frappe, create=True, new_callable=mock.MagicMock, **patches) as m:
			m["throw"].side_effect = _Thrown
			if get_doc is not None:
				m["get_doc"].side_effect = get_doc
			m["error"] = None
			try:
				dunning.send_payment_reminder_email(sales_invoice, doc_name)
			except Exception as exc:
				m["error"] = type(exc)
			return m


class _Missing(Exception):
	"""Stand in for a missing Dunning."""


class _Denied(Exception):
	"""Stand in for a refused read permission."""


if __name__ == "__main__":
	unittest.main()
