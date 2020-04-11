# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest, frappe
from frappe.utils import getdate, formatdate
from frappe.desk.doctype.dashboard_chart.dashboard_chart import (get,
	get_period_ending)

from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

class TestDashboardChart(unittest.TestCase):
	def test_period_ending(self):
		self.assertEqual(get_period_ending('2019-04-10', 'Daily'),
			getdate('2019-04-10'))

		# fun fact: week ends on the day before 1st Jan of the year.
		# for 2019 it is Monday
		self.assertEqual(get_period_ending('2019-04-10', 'Weekly'),
			getdate('2019-04-15'))

		self.assertEqual(get_period_ending('2019-04-10', 'Monthly'),
			getdate('2019-04-30'))
		self.assertEqual(get_period_ending('2019-04-30', 'Monthly'),
			getdate('2019-04-30'))
		self.assertEqual(get_period_ending('2019-03-31', 'Monthly'),
			getdate('2019-03-31'))

		self.assertEqual(get_period_ending('2019-04-10', 'Quarterly'),
			getdate('2019-06-30'))
		self.assertEqual(get_period_ending('2019-06-30', 'Quarterly'),
			getdate('2019-06-30'))
		self.assertEqual(get_period_ending('2019-10-01', 'Quarterly'),
			getdate('2019-12-31'))

		self.assertEqual(get_period_ending('2019-10-01', 'Yearly'),
			getdate('2019-12-31'))

	def test_dashboard_chart(self):
		if frappe.db.exists('Dashboard Chart', 'Test Dashboard Chart'):
			frappe.delete_doc('Dashboard Chart', 'Test Dashboard Chart')

		frappe.get_doc(dict(
			doctype = 'Dashboard Chart',
			chart_name = 'Test Dashboard Chart',
			chart_type = 'Count',
			document_type = 'DocType',
			based_on = 'creation',
			timespan = 'Last Year',
			time_interval = 'Monthly',
			filters_json = '[]',
			timeseries = 1
		)).insert()

		cur_date = datetime.now() - relativedelta(years=1)

		result = get(chart_name ='Test Dashboard Chart', refresh = 1)
		for idx in range(13):
			month = datetime(int(cur_date.year), int(cur_date.strftime('%m')), int(calendar.monthrange(cur_date.year, cur_date.month)[1]))
			month = formatdate(month.strftime('%Y-%m-%d'))
			self.assertEqual(result.get('labels')[idx], month)
			cur_date += relativedelta(months=1)

		# self.assertEqual(result.get('datasets')[0].get('values')[:-1],
		# 	[44, 28, 8, 11, 2, 6, 18, 6, 4, 5, 15, 13])

		frappe.db.rollback()

	def test_empty_dashboard_chart(self):
		if frappe.db.exists('Dashboard Chart', 'Test Empty Dashboard Chart'):
			frappe.delete_doc('Dashboard Chart', 'Test Empty Dashboard Chart')

		frappe.db.sql('delete from `tabError Log`')

		frappe.get_doc(dict(
			doctype = 'Dashboard Chart',
			chart_name = 'Test Empty Dashboard Chart',
			chart_type = 'Count',
			document_type = 'Error Log',
			based_on = 'creation',
			timespan = 'Last Year',
			time_interval = 'Monthly',
			filters_json = '[]',
			timeseries = 1
		)).insert()

		cur_date = datetime.now() - relativedelta(years=1)

		result = get(chart_name ='Test Empty Dashboard Chart', refresh = 1)
		for idx in range(13):
			month = datetime(int(cur_date.year), int(cur_date.strftime('%m')), int(calendar.monthrange(cur_date.year, cur_date.month)[1]))
			month = formatdate(month.strftime('%Y-%m-%d'))
			self.assertEqual(result.get('labels')[idx], month)
			cur_date += relativedelta(months=1)

		frappe.db.rollback()

	def test_chart_wih_one_value(self):
		if frappe.db.exists('Dashboard Chart', 'Test Empty Dashboard Chart 2'):
			frappe.delete_doc('Dashboard Chart', 'Test Empty Dashboard Chart 2')

		frappe.db.sql('delete from `tabError Log`')

		# create one data point
		frappe.get_doc(dict(doctype = 'Error Log', creation = '2018-06-01 00:00:00')).insert()

		frappe.get_doc(dict(
			doctype = 'Dashboard Chart',
			chart_name = 'Test Empty Dashboard Chart 2',
			chart_type = 'Count',
			document_type = 'Error Log',
			based_on = 'creation',
			timespan = 'Last Year',
			time_interval = 'Monthly',
			filters_json = '[]',
			timeseries = 1
		)).insert()

		cur_date = datetime.now() - relativedelta(years=1)

		result = get(chart_name ='Test Empty Dashboard Chart 2', refresh = 1)
		for idx in range(13):
			month = datetime(int(cur_date.year), int(cur_date.strftime('%m')), int(calendar.monthrange(cur_date.year, cur_date.month)[1]))
			month = formatdate(month.strftime('%Y-%m-%d'))
			self.assertEqual(result.get('labels')[idx], month)
			cur_date += relativedelta(months=1)

		# only 1 data point with value
		self.assertEqual(result.get('datasets')[0].get('values')[2], 0)

		frappe.db.rollback()

	def test_group_by_chart_type(self):
		if frappe.db.exists('Dashboard Chart', 'Test Group By Dashboard Chart'):
			frappe.delete_doc('Dashboard Chart', 'Test Group By Dashboard Chart')

		frappe.get_doc({"doctype":"ToDo", "description": "test"}).insert()

		frappe.get_doc(dict(
			doctype = 'Dashboard Chart',
			chart_name = 'Test Group By Dashboard Chart',
			chart_type = 'Group By',
			document_type = 'ToDo',
			group_by_based_on = 'status',
			filters_json = '[]',
		)).insert()

		result = get(chart_name ='Test Group By Dashboard Chart', refresh = 1)
		todo_status_count = frappe.db.count('ToDo', {'status': result.get('labels')[0]})

		self.assertEqual(result.get('datasets')[0].get('values')[0], todo_status_count)

		frappe.db.rollback()

	def test_dashboard_with_single_doctype(self):
		if frappe.db.exists('Dashboard Chart', 'Test Single DocType In Dashboard Chart'):
			frappe.delete_doc('Dashboard Chart', 'Test Single DocType In Dashboard Chart')

		chart_doc = frappe.get_doc(dict(
			doctype = 'Dashboard Chart',
			chart_name = 'Test Single DocType In Dashboard Chart',
			chart_type = 'Count',
			document_type = 'System Settings',
			group_by_based_on = 'Created On',
			filters_json = '{}',
		))

		self.assertRaises(frappe.ValidationError, chart_doc.insert)
