from . import __version__ as app_version

app_name = "omnione"
app_title = "Omni One"
app_publisher = "Outpost.Work LLP"
app_description = "Omni One"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "anas@outpost.work"
app_license = "MIT"

app_required=["frappe/erpnext"]


after_install="omnione.customizations.purchase_order_custom.create_custom_fields"
after_uninstall="omnione.customizations.purchase_order_custom.delete_custom_fields"
after_migrate="omnione.customizations.purchase_order_custom.create_custom_fields"
# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/omnione/css/omnione.css"
# app_include_js = "/assets/omnione/js/omnione.js"

# include js, css files in header of web template
# web_include_css = "/assets/omnione/css/omnione.css"
# web_include_js = "/assets/omnione/js/omnione.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "omnione/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "omnione.install.before_install"
# after_install = "omnione.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "omnione.uninstall.before_uninstall"
# after_uninstall = "omnione.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "omnione.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Purchase Order": {
		"on_submit": "omnione.utils.omnione_trigger.trigger_omnione_on_po_submit"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"omnione.tasks.all"
#	],
#	"daily": [
#		"omnione.tasks.daily"
#	],
#	"hourly": [
#		"omnione.tasks.hourly"
#	],
#	"weekly": [
#		"omnione.tasks.weekly"
#	]
#	"monthly": [
#		"omnione.tasks.monthly"
#	]
# }

# Testing
# -------

# before_tests = "omnione.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "omnione.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "omnione.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Request Events
# ----------------
# before_request = ["omnione.utils.before_request"]
# after_request = ["omnione.utils.after_request"]

# Job Events
# ----------
# before_job = ["omnione.utils.before_job"]
# after_job = ["omnione.utils.after_job"]

# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"omnione.auth.validate"
# ]

