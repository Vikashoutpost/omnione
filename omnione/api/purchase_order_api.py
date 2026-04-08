import frappe
from frappe import _
import json
from frappe.utils import add_days, nowdate

@frappe.whitelist(allow_guest=False)
def create_purchase_order(data=None):
    """
    API endpoint to create a Purchase Order.
    Expected data format (JSON string or dict):
    {
        "supplier": "Supplier Name",
        "company": "Company Name",           # Optional
        "transaction_date": "2023-10-01",   # Optional, defaults to today
        "schedule_date": "2023-10-05",      # Optional, defaults to today + 7
        "order_confirmation_no": "SO-1234", #optional
        "order_id": "SO-1234", #optional
        "supplier_so_no": "SO-1234", #optional
        "payment_terms_template": "Terms",  # Optional
        "department": "Department Name",    # Optional
        "channel": "Channel Name",          # Optional (custom field)
        "cost_center": "Cost Center",       # Optional
        "set_warehouse": "Warehouse Name",  # Optional - sets default warehouse for all items
        "shipment_id": "SHIP-0001",         # Optional (custom field)
        "items": [
            {
                "item_code": "Item Code",
                "qty": 10,
                "rate": 100, # Optional, will fetch from price list if available
                "schedule_date": "2023-10-05" # Optional
            }
        ]
    }
    """
    try:
        if data is None:
            data = frappe.form_dict

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                frappe.throw(_("Invalid JSON data provided."))


        if not data.get("supplier"):
            frappe.throw(_("Supplier is required."))
            
        if not data.get("items") or not isinstance(data.get("items"), list):
            frappe.throw(_("At least one item is required in the 'items' list."))

        po = frappe.new_doc("Purchase Order")
        po.supplier = data.get("supplier")
        
        po.transaction_date = data.get("transaction_date") or nowdate()
        po.schedule_date = data.get("schedule_date") or add_days(po.transaction_date, 7)
        
        if data.get("company"):
            po.company = data.get("company")
        if data.get("currency"):
            po.currency = data.get("currency")
        if data.get("order_confirmation_no"):
            po.order_confirmation_no = data.get("order_confirmation_no")
        if data.get("payment_terms_template"):
            po.payment_terms_template = data.get("payment_terms_template")
        if data.get("department"):
            po.department = data.get("department")
        if data.get("channel"):
            po.channel = data.get("channel")
        if data.get("cost_center"):
            po.cost_center = data.get("cost_center")
        if data.get("set_warehouse"):
            po.set_warehouse = data.get("set_warehouse")
        if data.get("shipment_id"):
            po.shipment_id = data.get("shipment_id")
        if data.get("supplier_so_no"):
            po.supplier_so_no = data.get("supplier_so_no")
        if data.get("order_id"):
            po.order_id = data.get("order_id")
        if data.get("omnione"):
            po.omnione = data.get("omnione")
            
        
        for item in data.get("items"):
            child = po.append("items", {})
            child.update(item)

            if not child.schedule_date:
                child.schedule_date = po.schedule_date

            if not child.get("channel") and data.get("channel"):
                child.channel = data.get("channel")
            if not child.get("cost_center") and data.get("cost_center"):
                child.cost_center = data.get("cost_center")
                
        po.set_missing_values()

        for item in po.items:
            item.department = po.department

        if not po.get("taxes"):
            tax_accounts_added = {}
            for item in po.items:
                if item.item_tax_template:
                    try:
                        tax_template = frappe.get_doc("Item Tax Template", item.item_tax_template)
                        for tax_row in tax_template.taxes:
                            account = tax_row.tax_type
                            if account not in tax_accounts_added:
                                po.append("taxes", {
                                    "category": "Total",
                                    "add_deduct_tax": "Add",
                                    "charge_type": "On Net Total",
                                    "account_head": account,
                                    "description": account,
                                    "rate": tax_row.tax_rate,
                                    "cost_center": po.cost_center or ""
                                })
                                tax_accounts_added[account] = tax_row.tax_rate
                    except Exception:
                        pass  

        po.calculate_taxes_and_totals()

        po.flags.ignore_links = True

        po.insert(ignore_permissions=True)
        
        po.submit()
        
        return {
            "status": "success",
            "message": _("Purchase Order {0} created and submitted successfully.").format(po.name),
            "purchase_order": po.name
        }

    except Exception as e:
        frappe.db.rollback()
        error_msg = str(e)
        if hasattr(e, "message") and e.message:
            error_msg = e.message
        
        if frappe.local.message_log:
            try:
                messages = [json.loads(msg).get("message") for msg in frappe.local.message_log]
                error_msg = "\n".join(filter(None, messages))
            except Exception:
                pass
                
        frappe.log_error(title="Create Purchase Order Error", message=frappe.get_traceback())
        
        frappe.response["http_status_code"] = 400
        return {
            "status": "error",
            "message": error_msg or "An error occurred while creating the Purchase Order."
        }