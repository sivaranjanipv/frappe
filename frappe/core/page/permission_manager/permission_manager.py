# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
from frappe.modules.import_file import get_file_path, read_doc_from_file
from frappe.translate import send_translations
from frappe.permissions import (reset_perms, get_linked_doctypes, get_all_perms,
	setup_custom_perms, add_permission)
from frappe.core.doctype.doctype.doctype import (clear_permissions_cache,
	validate_permissions_for_doctype)
from frappe import _

@frappe.whitelist()
def get_roles_and_doctypes():
	frappe.only_for("System Manager")
	send_translations(frappe.get_lang_dict("doctype", "DocPerm"))

	active_domains = frappe.get_active_domains()

	doctypes = frappe.get_all("DocType", filters={
		"istable": 0,
		"name": ("not in", "DocType"),
	}, or_filters={
		"ifnull(restrict_to_domain, '')": "",
		"restrict_to_domain": ("in", active_domains)
	}, fields=["name"])

	roles = frappe.get_all("Role", filters={
		"name": ("not in", "Administrator"),
		"disabled": 0,
	}, or_filters={
		"ifnull(restrict_to_domain, '')": "",
		"restrict_to_domain": ("in", active_domains)
	}, fields=["name"])

	return {
		"doctypes": [d.get("name") for d in doctypes],
		"roles": [d.get("name") for d in roles]
	}

@frappe.whitelist()
def get_permissions(doctype=None, role=None):
	frappe.only_for("System Manager")
	if role:
		out = get_all_perms(role)
		if doctype:
			out = [p for p in out if p.parent == doctype]
	else:
		out = frappe.get_all('Custom DocPerm', fields='*', filters=dict(parent = doctype), order_by="permlevel")
		if not out:
			out = frappe.get_all('DocPerm', fields='*', filters=dict(parent = doctype), order_by="permlevel")

	linked_doctypes = {}
	for d in out:
		if not d.parent in linked_doctypes:
			linked_doctypes[d.parent] = get_linked_doctypes(d.parent)
		d.linked_doctypes = linked_doctypes[d.parent]

	return out

@frappe.whitelist()
def add(parent, role, permlevel):
	frappe.only_for("System Manager")
	add_permission(parent, role, permlevel)

@frappe.whitelist()
def update(doctype, role, permlevel, ptype, value=None):
	frappe.only_for("System Manager")

	out = None
	if setup_custom_perms(doctype):
		out = 'refresh'

	name = frappe.get_value('Custom DocPerm', dict(parent=doctype, role=role, permlevel=permlevel))

	frappe.db.sql("""update `tabCustom DocPerm` set `%s`=%s where name=%s"""\
	 	% (frappe.db.escape(ptype), '%s', '%s'), (value, name))
	validate_permissions_for_doctype(doctype)

	return out

@frappe.whitelist()
def remove(doctype, role, permlevel):
	frappe.only_for("System Manager")
	setup_custom_perms(doctype)

	name = frappe.get_value('Custom DocPerm', dict(parent=doctype, role=role, permlevel=permlevel))

	frappe.db.sql('delete from `tabCustom DocPerm` where name=%s', name)
	if not frappe.get_all('Custom DocPerm', dict(parent=doctype)):
		frappe.throw(_('There must be atleast one permission rule.'), title=_('Cannot Remove'))

	validate_permissions_for_doctype(doctype, for_remove=True)

@frappe.whitelist()
def reset(doctype):
	frappe.only_for("System Manager")
	reset_perms(doctype)
	clear_permissions_cache(doctype)


@frappe.whitelist()
def get_users_with_role(role):
	frappe.only_for("System Manager")
	return [p[0] for p in frappe.db.sql("""select distinct tabUser.name
		from `tabHas Role`, tabUser where
			`tabHas Role`.role=%s
			and tabUser.name != "Administrator"
			and `tabHas Role`.parent = tabUser.name
			and tabUser.enabled=1""", role)]

@frappe.whitelist()
def get_standard_permissions(doctype):
	frappe.only_for("System Manager")
	module = frappe.db.get_value("DocType", doctype, "module")
	path = get_file_path(module, "DocType", doctype)
	return read_doc_from_file(path).get("permissions")
