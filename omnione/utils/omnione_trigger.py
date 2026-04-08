# Copyright (c) 2026, Outpost.Work LLP and contributors
# For license information, please see license.txt

"""
OmniOne trigger utility
-----------------------
Fires a configuration-driven POST API call to the linked OmniOne Entity
whenever a supported Frappe document (e.g. Purchase Order) is submitted.

Entry point hooked via hooks.py → doc_events → on_submit.
"""

import json
import requests
import frappe


# ---------------------------------------------------------------------------
# Public hook entry point
# ---------------------------------------------------------------------------

def trigger_omnione_on_po_submit(doc, method=None):
    """
    Called automatically by Frappe on Purchase Order on_submit event.
    Delegates to the shared trigger handler for 'Purchase Order'.
    """
    _trigger_omnione(doc, doctype_name="Purchase Order")


# ---------------------------------------------------------------------------
# Core trigger logic
# ---------------------------------------------------------------------------

def _trigger_omnione(doc, doctype_name):
    """
    Full configuration-driven OmniOne trigger flow:

    1.  Read OmniOne Settings → check enable_omnione.
    2.  Find an enabled entity via omnione_link_doctype child table.
    3.  In that entity's create_for_doctypes child table, find the row
        matching the doctype_name.
    4.  Validate required fields (method, party_type, enabled_party).
    5.  Fetch the party/supplier details from OmniOne via GET.
    6.  POST the document payload to OmniOne.
    7.  Log the outcome in Omnione Logging.
    """
    try:
        # ------------------------------------------------------------------
        # Step 1 – Check OmniOne Settings
        # ------------------------------------------------------------------
        settings = frappe.get_single("Omnione Settings")

        if not settings.get("enable_omnione"):
            frappe.logger("omnione").debug(
                f"OmniOne is disabled in Omnione Settings. Skipping trigger for {doctype_name} {doc.name}."
            )
            return

        linked_items = settings.get("omnione_link_doctype") or []
        if not linked_items:
            frappe.logger("omnione").debug(
                "No entities configured in Omnione Settings. Skipping."
            )
            return

        # ------------------------------------------------------------------
        # Step 2 – Find an enabled entity that matches the document's party
        # ------------------------------------------------------------------
        entity_name = None
        doc_party = doc.get("supplier") or doc.get("customer")
        
        for link_row in linked_items:
            if link_row.get("enable") == "Yes" and link_row.get("entity"):
                temp_entity = frappe.get_cached_doc("Omnione Entity", link_row.get("entity"))
                if temp_entity.company_name == doc_party:
                    entity_name = link_row.get("entity")
                    break

        if not entity_name:
            frappe.logger("omnione").debug(
                "No enabled OmniOne Entity found in Omnione Settings. Skipping."
            )
            return

        entity = frappe.get_doc("Omnione Entity", entity_name)

        # ------------------------------------------------------------------
        # Step 3 – Find the matching row in create_for_doctypes
        # ------------------------------------------------------------------
        doctype_row = None
        for row in entity.get("create_for_doctypes") or []:
            if row.get("doctypes") == doctype_name:
                doctype_row = row
                break

        if not doctype_row:
            frappe.logger("omnione").debug(
                f"No create_for_doctypes entry for '{doctype_name}' in entity '{entity_name}'. Skipping."
            )
            return

        # ------------------------------------------------------------------
        # Step 4 – Validate required configuration fields
        # ------------------------------------------------------------------
        method_path   = doctype_row.get("method")       # URL path / endpoint
        party_type    = doctype_row.get("party_type")   # e.g. "Supplier"
        enabled_party = doctype_row.get("enabled_party") # party name on OmniOne

        missing = []
        if not method_path:
            missing.append("method")
        if not party_type:
            missing.append("party_type")
        if not enabled_party:
            missing.append("enabled_party")

        if missing:
            frappe.logger("omnione").warning(
                f"OmniOne config incomplete for '{doctype_name}' in entity '{entity_name}'. "
                f"Missing fields: {', '.join(missing)}. Skipping."
            )
            return

        site_url       = entity.site_url.rstrip("/")
        api_key        = entity.api_key
        api_secret_key = entity.get_password("api_secret_key")

        auth_header = {
            "Authorization": f"token {api_key}:{api_secret_key}",
            "Content-Type": "application/json",
        }

        # ------------------------------------------------------------------
        # Step 5 – Fetch party/supplier details dynamically from OmniOne
        # ------------------------------------------------------------------
        party_details = _fetch_party_from_omnione(
            site_url, party_type, enabled_party, auth_header, entity_name, doctype_name, doc.name
        )

        # ------------------------------------------------------------------
        # Step 6 – Build payload and POST to OmniOne
        # ------------------------------------------------------------------
        payload = _build_po_payload(doc, party_type, party_details, doctype_row)

        full_url = f"{site_url}{method_path}"
        frappe.logger("omnione").info(
            f"POSTing {doctype_name} '{doc.name}' to OmniOne URL: {full_url}"
        )

        response = requests.post(
            full_url,
            json=payload,
            headers=auth_header,
            timeout=30,
        )

        response_text = _safe_response_text(response)
        status = "Success" if response.ok else "Failed"

        frappe.logger("omnione").info(
            f"OmniOne response for {doctype_name} '{doc.name}': [{response.status_code}] {response_text[:200]}"
        )

        # ------------------------------------------------------------------
        # Step 7 – Log the outcome in Omnione Logging
        # ------------------------------------------------------------------
        _log_omnione(
            method="POST",
            doctype_name=doctype_name,
            doctype_id=doc.name,
            entity_name=entity_name,
            response=response_text,
            status=status,
        )

        if not response.ok:
            frappe.log_error(
                title=f"OmniOne POST Failed – {doctype_name} {doc.name}",
                message=(
                    f"URL: {full_url}\n"
                    f"Status code: {response.status_code}\n"
                    f"Response: {response_text}"
                ),
            )

    except Exception:
        frappe.log_error(
            title=f"OmniOne Trigger Error – {doctype_name} {getattr(doc, 'name', 'unknown')}",
            message=frappe.get_traceback(),
        )
        # Log the failure in Omnione Logging without re-raising so the PO
        # submission itself is not rolled back.
        try:
            _log_omnione(
                method="POST",
                doctype_name=doctype_name,
                doctype_id=getattr(doc, "name", ""),
                entity_name="",
                response=frappe.get_traceback(),
                status="Failed",
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_party_from_omnione(site_url, party_type, enabled_party, auth_header,
                               entity_name, doctype_name, doc_name):
    """
    Fetch the party (Supplier / Customer) record from OmniOne via REST API.
    Returns a dict with party details, or an empty dict if the request fails.
    """
    resource_url = f"{site_url}/api/resource/{party_type}/{requests.utils.quote(enabled_party, safe='')}"
    try:
        resp = requests.get(resource_url, headers=auth_header, timeout=15)
        if resp.ok:
            data = resp.json()
            return data.get("data") or data
        else:
            frappe.logger("omnione").warning(
                f"Could not fetch {party_type} '{enabled_party}' from OmniOne "
                f"[{resp.status_code}]: {_safe_response_text(resp)}"
            )
            _log_omnione(
                method="GET",
                doctype_name=doctype_name,
                doctype_id=doc_name,
                entity_name=entity_name,
                response=_safe_response_text(resp),
                status="Failed",
            )
            return {}
    except Exception:
        frappe.log_error(
            title=f"OmniOne – Failed to fetch {party_type} '{enabled_party}'",
            message=frappe.get_traceback(),
        )
        return {}


def _build_po_payload(doc, party_type, party_details, doctype_row):
    """
    Build the payload dictionary for the OmniOne POST request.
    Merges the Purchase Order fields with dynamically fetched party details
    and mapping accounts from the OmniOne Items configuration.
    """
    items = []
    for item in doc.get("items") or []:
        items.append({
            "item_code":     item.item_code,
            "item_name":     item.item_name,
            "qty":           item.qty,
            "rate":          item.rate,
            "amount":        item.amount,
            "uom":           item.uom,
            "schedule_date": str(item.schedule_date) if item.schedule_date else None,
            "warehouse":     item.warehouse,
        })

    payload = {
        "doctype":            "Purchase Order",
        "name":               doc.name,
        "supplier":           doctype_row.get("party_name") or doc.supplier,
        "supplier_account":   doctype_row.get("party_account"),
        "income_account":     doctype_row.get("income_account"),
        "expense_account":    doctype_row.get("expense_account"),
        "omnione":            1, # Mark this as 1 for the destination ERP
        # "company":            doc.company, # Omitted to allow destination to use its default company
        "transaction_date":   str(doc.transaction_date) if doc.transaction_date else None,
        "schedule_date":      str(doc.schedule_date)    if doc.schedule_date    else None,
        "grand_total":        doc.grand_total,
        "net_total":          doc.net_total,
        "status":             doc.status,
        "currency":           doc.currency,
        "party_type":         party_type,
        "party_details":      party_details,
        "items":              items,
    }

    # Include optional custom fields if present on the document
    for field in ("department", "cost_center", "order_id", "supplier_so_no",
                  "order_confirmation_no", "shipment_id", "channel"):
        if doc.get(field):
            payload[field] = doc.get(field)

    return payload


def _log_omnione(method, doctype_name, doctype_id, entity_name, response, status):
    """
    Insert a record in the Omnione Logging doctype.
    """
    try:
        log = frappe.new_doc("Omnione Logging")
        log.method      = method
        log.doctypes    = doctype_name
        log.doctype_id  = doctype_id
        log.entity      = entity_name or None
        log.response    = (response or "")[:500]   # Small Text – cap at 500 chars
        log.status      = status
        log.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(
            title="OmniOne – Failed to write Omnione Logging",
            message=frappe.get_traceback(),
        )


def _safe_response_text(response):
    """Return response text truncated to 1000 chars to avoid memory issues."""
    try:
        return (response.text or "")[:1000]
    except Exception:
        return ""
