# -*- coding: utf-8 -*-
# Copyright (c) 2019, Alyf and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
import json
from six import string_types

class Dunning(Document):
	pass

@frappe.whitelist()
def get_text_block(dunning_type, language, doc):	
	"""
		This allows the rendering of parsed fields in the jinja template
	"""
	if isinstance(doc, string_types):
		doc = json.loads(doc)

	text_block = frappe.db.get_value('Dunning Type Text Block', 
			{'parent': dunning_type, 'language': language}, 
			['top_text_block', 'bottom_text_block'], as_dict = 1)

	if text_block:
		return {
			'top_text_block': frappe.render_template(text_block.top_text_block, doc),
			'bottom_text_block': frappe.render_template(text_block.bottom_text_block, doc)
		}
	

@frappe.whitelist()
def send_payment_reminder_email(sales_invoice, doc_name):
	"""Send the reminder only when the caller may read this Dunning and its invoice."""
	if not isinstance(doc_name, string_types) or not doc_name:
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	dunning = frappe.get_doc("Dunning", doc_name)
	dunning.check_permission("read")
	if not dunning.sales_invoice or dunning.sales_invoice != sales_invoice:
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	invoice = frappe.get_doc("Sales Invoice", dunning.sales_invoice)
	invoice.check_permission("read")

	si = frappe.db.get_value("Sales Invoice", sales_invoice, ["customer", "contact_person"], as_dict=1)
	lang = frappe.db.get_value("Customer", si.customer, "language")
	if lang == 'de':
		template = 'zahlungserinnerung'
		subject = "Zahlungserinnerung "+ sales_invoice
	else:
		template = 'payment_reminder'
		subject = 'Payment Reminder ' + sales_invoice

	sales_invoice_attachment = frappe.attach_print("Sales Invoice", sales_invoice, file_name=sales_invoice, lang=lang)
	dunning_attachment = frappe.attach_print("Dunning", doc_name, file_name=doc_name, lang=lang)
	recipients = frappe.db.get_value("Contact", si.contact_person, "email_id")
	if recipients:
		frappe.sendmail(recipients=recipients,
							subject=subject,
							template=template,
							args=dict(
								sales_invoice=sales_invoice,
								doc_name=doc_name
							),
							attachments=[sales_invoice_attachment, dunning_attachment]
							)
		frappe.msgprint(_("Payment Reminder Email Sent to {0}").format(recipients))
	else:
		frappe.throw(_("No Email ID found in {0} check customer sales invoice contact person").format(sales_invoice))