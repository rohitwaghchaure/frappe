# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from six import iteritems
from frappe.utils import get_link_to_form
from frappe.config import get_modules_from_app
from frappe.permissions import add_permission, add_user_permission
from frappe.model.document import Document

class UserType(Document):
	def validate(self):
		self.set_modules()

	def on_update(self):
		if self.is_standard: return

		self.validate_document_type_limit()
		self.validate_role()
		self.add_role_permissions_for_user_doctypes()
		self.add_role_permissions_for_select_doctypes()
		self.update_users()
		get_non_standard_user_type_details()
		self.remove_permission_for_deleted_doctypes()

	def on_trash(self):
		if self.is_standard:
			frappe.throw(_('Standard user type {0} can not be deleted.')
				.format(frappe.bold(self.name)))

	def set_modules(self):
		if not self.user_doctypes: return

		modules = frappe.get_all('DocType', fields=['distinct module as module'],
			filters={'name': ('in', [d.document_type for d in self.user_doctypes])})

		self.set('user_type_modules', [])
		for row in modules:
			self.append('user_type_modules', {
				'module': row.module
			})

	def validate_document_type_limit(self):
		limit = frappe.conf.get('user_type_doctype_limit').get(frappe.scrub(self.name)) or 10

		if self.user_doctypes and len(self.user_doctypes) > limit:
			frappe.throw(_('The total number of user document types limit has been crossed.'),
				title=_('User Document Types Limit Exceeded'))

		custom_doctypes = [row.document_type for row in self.user_doctypes if row.is_custom]
		if custom_doctypes and len(custom_doctypes) > 3:
			frappe.throw(_('You can only set the 3 custom doctypes in the Document Types table.'),
				title=_('Custom Document Types Limit Exceeded'))

	def validate_role(self):
		if not self.role:
			frappe.throw(_("The field {0} is mandatory")
				.format(frappe.bold(_('Role'))))

		if not frappe.db.get_value('Role', self.role, 'is_custom'):
			frappe.throw(_("The role {0} should be a custom role.")
				.format(frappe.bold(get_link_to_form('Role', self.role))))

	def update_users(self):
		for row in frappe.get_all('User', filters = {'user_type': self.name}):
			user = frappe.get_cached_doc('User', row.name)
			self.update_roles_in_user(user)
			self.update_modules_in_user(user)
			user.update_children()

	def update_roles_in_user(self, user):
		user.set('roles', [])
		user.append('roles', {
			'role': self.role
		})

	def update_modules_in_user(self, user):
		block_modules = frappe.get_all('Module Def', fields = ['name as module'],
			filters={'name': ['not in', [d.module for d in self.user_type_modules]]})

		if block_modules:
			user.set('block_modules', block_modules)

	def add_role_permissions_for_user_doctypes(self):
		perms = ['read', 'write', 'create']
		for row in self.user_doctypes:
			docperm = add_role_permissions(row.document_type, self.role)

			values = {perm:row.get(perm) for perm in perms}
			for perm in ['print', 'email', 'share']:
				values[perm] = 1

			frappe.db.set_value('Custom DocPerm', docperm, values)

	def add_role_permissions_for_select_doctypes(self):
		for row in self.select_doctypes:
			docperm = add_role_permissions(row.document_type, self.role)
			frappe.db.set_value('Custom DocPerm', docperm,
				{'select': 1, 'read': 0, 'create': 0, 'write': 0})

	def remove_permission_for_deleted_doctypes(self):
		doctypes = [d.document_type for d in self.user_doctypes]

		for dt in self.select_doctypes:
			doctypes.append(dt.document_type)

		for perm in frappe.get_all('Custom DocPerm',
			filters = {'role': self.role, 'parent': ['not in', doctypes]}):
			frappe.delete_doc('Custom DocPerm', perm.name)

def add_role_permissions(doctype, role):
	name = frappe.get_value('Custom DocPerm', dict(parent=doctype,
		role=role, permlevel=0))

	if not name:
		name = add_permission(doctype, role, 0)

	return name

def get_non_standard_user_type_details():
	user_types = frappe.get_all('User Type',
		fields=['apply_user_permission_on', 'name', 'user_id_field'],
		filters={'is_standard': 0})

	if user_types:
		user_type_details = {d.name: [d.apply_user_permission_on, d.user_id_field] for d in user_types}

		frappe.cache().set_value('non_standard_user_types', user_type_details)

		return user_type_details

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_user_linked_doctypes(doctype, txt, searchfield, start, page_len, filters):
	modules = [d.get('module_name') for d in get_modules_from_app('frappe')]

	filters = [['DocField', 'options', '=', 'User'], ['DocType', 'is_submittable', '=', 0],
		['DocType', 'issingle', '=', 0], ['DocType', 'module', 'not in', modules],
		['DocType', 'read_only', '=', 0], ['DocType', 'name', 'like', '%{0}%'.format(txt)]]

	doctypes = frappe.get_all('DocType', fields = ['`tabDocType`.`name`'], filters=filters,
		order_by = '`tabDocType`.`idx` desc', limit_start=start, limit_page_length=page_len, as_list=1, debug=1)

	custom_dt_filters = [['Custom Field', 'dt', 'like', '%{0}%'.format(txt)],
		['Custom Field', 'options', '=', 'User'], ['Custom Field', 'fieldtype', '=', 'Link']]

	custom_doctypes = frappe.get_all('Custom Field', fields = ['dt as name'],
		filters= custom_dt_filters, as_list=1)

	return doctypes + custom_doctypes

@frappe.whitelist()
def get_user_id(parent):
	data = frappe.get_all('DocField', fields = ['label', 'fieldname as value'],
		filters= {'options': 'User', 'fieldtype': 'Link', 'parent': parent}) or []

	data.extend(frappe.get_all('Custom Field', fields = ['label', 'fieldname as value'],
		filters= {'options': 'User', 'fieldtype': 'Link', 'dt': parent}))

	return data

def user_linked_with_permission_on_doctype(doc, user):
	if not doc.apply_user_permission_on: return True

	if not doc.user_id_field:
		frappe.throw(_('User Id Field is mandatory in the user type {0}')
			.format(frappe.bold(doc.name)))

	if frappe.db.get_value(doc.apply_user_permission_on,
		{doc.user_id_field: user}, 'name'):
		return True
	else:
		label = frappe.get_meta(doc.apply_user_permission_on).get_field(doc.user_id_field).label

		frappe.msgprint(_("To set the role {0} in the user {1}, kindly set the {2} field as {3} in one of the {4} record.")
			.format(frappe.bold(doc.role), frappe.bold(user), frappe.bold(label),
				frappe.bold(user), frappe.bold(doc.apply_user_permission_on)))

		return False

def apply_permissions_for_non_standard_user_type(doc, method=None):
	'''Create user permission for the non standard user type'''
	user_types = frappe.cache().get_value('non_standard_user_types')

	if not user_types:
		user_types = get_non_standard_user_type_details()

	for user_type, data in iteritems(user_types):
		if doc.doctype != data[0]: continue
		if frappe.get_cached_value('User', doc.get(data[1]), 'user_type') != user_type:
			return

		if (doc.get(data[1]) and (doc.get(data[1]) != doc._doc_before_save.get(data[1])
			or not frappe.db.get_value('User Permission',
				{'user': doc.get(data[1]), 'allow': data[0], 'for_value': doc.name}, 'name'))):

			perm_data = frappe.db.get_value('User Permission',
				{'allow': doc.doctype, 'for_value': doc.name}, ['name', 'user'])

			if not perm_data:
				user_doc = frappe.get_cached_doc('User', doc.get(data[1]))
				user_doc.set_roles_and_modules_based_on_user_type()
				user_doc.update_children()
				add_user_permission(doc.doctype, doc.name, doc.get(data[1]))
			else:
				frappe.db.set_value('User Permission', perm_data[0], 'user', doc.get(data[1]))