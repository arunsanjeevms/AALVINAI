#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds the product catalogue for aalvinai.in from the data in this file.

    python _tools/build_products.py              regenerate everything below
    python _tools/build_products.py --check      exit 1 if any generated file is stale
    python _tools/build_products.py --indexnow   after deploying, ping IndexNow (Bing, Yandex, ...)

Writes:
    products/<slug>/index.html   one search landing page per product
    products/index.html          redirect stub, so /products keeps resolving to the hub
    products.html                catalogue cards, filter chips and JSON-LD (between markers)
    sitemap.xml                  every public page, <lastmod> taken from git history
    llms.txt                     plain-text site summary for AI search tools
    <INDEXNOW_KEY>.txt           IndexNow ownership key

To add a product: append it to PRODUCTS (in display order), run the script, then
update the hand-written counts in products.html if the script warns about them.
Jekyll ignores this folder (leading underscore), so it is never published.
"""
import argparse
import datetime
import html
import io
import json
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://aalvinai.in"
INDEXNOW_KEY = "6bac4ddd55c0e526310d7f40dd721144"
TODAY = datetime.date.today().isoformat()

# ──────────────────────────────────────────────────────────────────────────────
# DATA
# ──────────────────────────────────────────────────────────────────────────────

# slug, title, one-line blurb, short chip label — in display order
CATEGORIES = [
    ("education", "Education & Campus", "Institution-wide systems for colleges, schools, hostels, labs and online learning.", "Education"),
    ("finance", "Finance, Accounting & Financial Services", "Ledgers, lending, collections, chit funds, billing and recurring revenue.", "Finance"),
    ("retail", "Retail, Inventory & Procurement", "Counter speed, stock accuracy and disciplined purchasing.", "Retail"),
    ("assets", "Construction & Assets", "Projects and equipment tracked from first day to last service.", "Assets"),
    ("transport", "Transport & Logistics", "Dispatch, trip tracking, cargo security and settlements for road-freight fleets.", "Transport"),
    ("business", "Business Management & Enterprise Productivity", "The operating layer: customers, people, documents, support and insight.", "Business"),
    ("services", "Consultancy, Healthcare & Professional Services", "Case-driven practices where every client file and appointment counts.", "Services"),
    ("community", "Events, Membership & Community", "Registrations, check-ins, memberships and volunteer coordination.", "Community"),
    ("commerce", "Digital Commerce & Custom Development", "Storefronts, bookings and bespoke platforms built to order.", "Commerce"),
]

# Every claim below is taken from the product briefs supplied by AALVINAI.
# Keep it that way: describe what a product covers, never invent numbers.
#
#   kicker    short label on catalogue cards
#   desc      catalogue card description
#   tags      three catalogue card tags
#   title     <title> for the landing page (keep under ~60 characters)
#   kw        the search phrase shown under the product name in the <h1>
#   is_a      completes "<Name> is ___ from AALVINAI Technologies"
#   audience  who it is built for
#   overview  landing-page overview (one or more paragraphs)
#   features  capability list on the landing page and in JSON-LD
#   related   three slugs to cross-link
#   deploy    optional; defaults to "Web · Mobile"
#   mobile    optional answer to "Is <Name> available on mobile?"
#   meta      optional hand-written meta description (<= 160 characters)
PRODUCTS = [
    dict(slug="campusos", name="CampusOS", kicker="College ERP", cat="education", icon="campus",
         desc="Complete college management covering admissions, student records, academics, examinations, fees, faculty, placements and institutional administration.",
         tags=["Admissions", "Examinations", "Placements"],
         title="CampusOS — College ERP Software in India | AALVINAI",
         kw="College ERP software", is_a="college ERP software",
         audience="Colleges and higher-education institutions",
         overview=["CampusOS runs a college’s administration from one system. Admissions, student records, academics, examinations, fees, faculty and placements share the same data, so every office works from a single, current record of each student instead of stitching together separate tools."],
         features=["Admissions", "Student records", "Academics", "Examinations", "Fees", "Faculty", "Placements", "Institutional administration"],
         related=["hostelsync", "labops", "skillforge"]),
    dict(slug="edunex", name="EduNex", kicker="School ERP", cat="education", icon="school",
         desc="School administration covering admissions, attendance, examinations, report cards, fees, teacher records, parent communication and transport.",
         tags=["Report cards", "Fees", "Transport"],
         title="EduNex — School ERP Software in India | AALVINAI",
         kw="School ERP software", is_a="school ERP software",
         audience="Schools — from the admissions office to teachers and parents",
         overview=["EduNex brings school administration into one place: admissions, attendance, examinations and report cards, fees, teacher records and transport. Office staff and teachers work from the same records, and parents stay informed through built-in parent communication."],
         features=["Admissions", "Attendance", "Examinations", "Report cards", "Fees", "Teacher records", "Parent communication", "Transport"],
         related=["skillforge", "campusos", "hostelsync"]),
    dict(slug="hostelsync", name="HostelSync", kicker="Hostel Management", cat="education", icon="hostel",
         desc="Hostel operations with biometric attendance integration, IVR-based parental leave approval, digital leave workflows and mess token management.",
         tags=["Biometric", "IVR approval", "Mess tokens"],
         title="HostelSync — Hostel Management Software | AALVINAI",
         kw="Hostel management software", is_a="hostel management software",
         audience="College and school hostels",
         overview=["HostelSync digitises day-to-day hostel operations. Attendance flows in from biometric devices, leave requests move through digital workflows with parental approval over an IVR phone call, and mess tokens are managed in the same system."],
         features=["Biometric attendance integration", "IVR-based parental leave approval", "Digital leave workflows", "Mess token management"],
         related=["campusos", "edunex", "labops"]),
    dict(slug="labops", name="LabOps", kicker="Computer Lab Management", cat="education", icon="lab",
         desc="Centralised PC status monitoring, remote screen access, power management, hardware change detection and timestamped audit reports.",
         tags=["Remote screen", "Power control", "Audit trail"],
         title="LabOps — Computer Lab Management Software | AALVINAI",
         kw="Computer lab management software", is_a="computer lab management software",
         audience="Institutions running computer labs",
         overview=["LabOps gives administrators one place to run every computer lab: the status of each PC, remote screen access, power management and hardware change detection, with timestamped audit reports that show what happened and when."],
         features=["Centralised PC status monitoring", "Remote screen access", "Power management", "Hardware change detection", "Timestamped audit reports"],
         related=["campusos", "assettrack", "helpnest"]),
    dict(slug="skillforge", name="SkillForge", kicker="Learning Management System", cat="education", icon="lms",
         desc="Online courses, assignments, quizzes, assessments, certificates, learning progress and instructor-led training.",
         tags=["Courses", "Assessments", "Certificates"],
         title="SkillForge — Learning Management System (LMS) | AALVINAI",
         kw="Learning management system (LMS)", is_a="a learning management system (LMS)",
         audience="Training teams, academies and institutions",
         overview=["SkillForge is a learning management system for courses delivered online and by instructors. Learners take courses, submit assignments and attempt quizzes and assessments; instructors follow each learner’s progress and issue certificates."],
         features=["Online courses", "Assignments", "Quizzes", "Assessments", "Certificates", "Learning progress", "Instructor-led training"],
         related=["campusos", "edunex", "peoplehub"]),

    dict(slug="credixa", name="Credixa", kicker="Finance Management", cat="finance", icon="ledger",
         desc="Enterprise finance management with daybook, ledger, loan processing, KYC, CIF, document management and full audit logging.",
         tags=["Daybook", "Loans", "KYC & CIF"],
         title="Credixa — Loan & Finance Management Software | AALVINAI",
         kw="Loan & finance management software", is_a="loan and finance management software",
         audience="Finance companies and lending institutions",
         overview=["Credixa is enterprise finance management for lending businesses: daybook and ledger accounting alongside loan processing, KYC and a customer information file (CIF). Documents are managed in the same system, and audit logging keeps a record of activity."],
         features=["Daybook", "Ledger", "Loan processing", "KYC", "Customer information file (CIF)", "Document management", "Audit logging"],
         related=["vasool", "chitflow", "docuflow"]),
    dict(slug="vasool", name="Vasool", kicker="Microfinance Collection App", cat="finance", icon="wallet",
         desc="Microfinance collection mobile app with customer payment tracking and Bluetooth POS receipt printing in the field.",
         tags=["Field app", "Bluetooth print", "Collections"],
         title="Vasool — Microfinance Collection App | AALVINAI",
         kw="Microfinance collection app", is_a="a microfinance collection app",
         audience="Microfinance field-collection teams",
         overview=["Vasool is a mobile collection app for microfinance field teams. Agents record customer payments as they collect them and print receipts on the spot from a Bluetooth POS printer, while payment tracking keeps each customer’s account up to date."],
         features=["Field collection on mobile", "Customer payment tracking", "Bluetooth POS receipt printing"],
         related=["credixa", "chitflow", "billora"],
         deploy="Mobile app",
         mobile="Yes — Vasool is a mobile app built for field collection, with Bluetooth POS receipt printing."),
    dict(slug="chitflow", name="ChitFlow", kicker="Chit Fund Management", cat="finance", icon="chit",
         desc="Chit fund administration, member records, contributions, installments, payment history and reporting.",
         tags=["Members", "Installments", "Reporting"],
         title="ChitFlow — Chit Fund Management Software | AALVINAI",
         kw="Chit fund management software", is_a="chit fund management software",
         audience="Chit fund companies",
         overview=["ChitFlow manages chit fund administration end to end — member records, contributions, installments, payment history and reporting — so every chit group and member account stays accurate and easy to report on."],
         features=["Chit fund administration", "Member records", "Contributions", "Installments", "Payment history", "Reporting"],
         related=["credixa", "vasool", "billora"]),
    dict(slug="billora", name="Billora", kicker="Billing & Invoicing", cat="finance", icon="invoice",
         desc="Billing, quotation creation, invoice generation, customer management and payment tracking.",
         tags=["Quotations", "Invoices", "Payments"],
         title="Billora — Billing & Invoicing Software | AALVINAI",
         kw="Billing & invoicing software", is_a="billing and invoicing software",
         audience="Businesses that quote, invoice and collect payments",
         overview=["Billora handles the billing cycle: create quotations and invoices, manage customers, and track payments until every bill is settled."],
         features=["Billing", "Quotation creation", "Invoice generation", "Customer management", "Payment tracking"],
         related=["payflow", "connectra", "pointops"]),
    dict(slug="payflow", name="PayFlow", kicker="Subscription Billing", cat="finance", icon="recur",
         desc="Subscription management, recurring billing cycles, renewals, invoices and payment status tracking.",
         tags=["Recurring", "Renewals", "Reminders"],
         title="PayFlow — Subscription Billing Software | AALVINAI",
         kw="Subscription billing software", is_a="subscription billing software",
         audience="Subscription and recurring-revenue businesses",
         overview=["PayFlow runs recurring revenue: it manages subscriptions and recurring billing cycles, handles renewals, produces invoices and tracks the payment status of every subscriber."],
         features=["Subscription management", "Recurring billing cycles", "Renewals", "Invoices", "Payment status tracking"],
         related=["billora", "connectra", "insightiq"]),

    dict(slug="pointops", name="PointOps", kicker="Point of Sale", cat="retail", icon="pos",
         desc="POS software for fast checkout, sales processing, product management and sales reporting.",
         tags=["Checkout", "Catalogue", "Day reports"],
         title="PointOps — POS Billing Software for Retail | AALVINAI",
         kw="POS billing software", is_a="point-of-sale (POS) billing software",
         audience="Retail stores and checkout counters",
         overview=["PointOps is point-of-sale software built for fast checkout. It processes sales at the counter, keeps products organised and turns each day’s transactions into sales reports."],
         features=["Checkout", "Sales processing", "Product management", "Sales reporting"],
         related=["stockwise", "medistock", "billora"]),
    dict(slug="medistock", name="MediStock", kicker="Pharmacy Management", cat="retail", icon="pharma",
         desc="Pharmacy management for medicine inventory, batch tracking, expiry monitoring, billing and supplier records.",
         tags=["Batch tracking", "Expiry alerts", "Suppliers"],
         title="MediStock — Pharmacy Management Software | AALVINAI",
         kw="Pharmacy management software", is_a="pharmacy management software",
         audience="Pharmacies and medical stores",
         overview=["MediStock is pharmacy management software that tracks medicine inventory batch by batch, monitors expiry dates, handles billing at the counter and keeps supplier records in one place."],
         features=["Medicine inventory", "Batch tracking", "Expiry monitoring", "Billing", "Supplier records"],
         related=["pointops", "stockwise", "carebridge"]),
    dict(slug="stockwise", name="StockWise", kicker="Inventory & Warehouse", cat="retail", icon="boxes",
         desc="Inventory and warehouse management covering stock movements, purchasing, transfers and multi-location inventory.",
         tags=["Movements", "Transfers", "Multi-location"],
         title="StockWise — Inventory & Warehouse Software | AALVINAI",
         kw="Inventory & warehouse management software", is_a="inventory and warehouse management software",
         audience="Warehouses and multi-location businesses",
         overview=["StockWise tracks inventory across warehouses and locations — every stock movement, purchase and transfer — for one accurate view of multi-location stock."],
         features=["Stock movements", "Purchasing", "Transfers", "Multi-location inventory"],
         related=["procureflow", "pointops", "assettrack"]),
    dict(slug="procureflow", name="ProcureFlow", kicker="Procurement & Vendors", cat="retail", icon="procure",
         desc="Procurement and vendor management covering purchase requests, supplier quotations, purchase orders and approval workflows.",
         tags=["Requisitions", "Quotations", "Approvals"],
         title="ProcureFlow — Procurement Management Software | AALVINAI",
         kw="Procurement & vendor management software", is_a="procurement and vendor management software",
         audience="Purchasing and procurement teams",
         overview=["ProcureFlow structures purchasing from request to order. Teams raise purchase requests, collect supplier quotations, issue purchase orders and route each step through approval workflows, with vendor records maintained alongside."],
         features=["Purchase requests", "Supplier quotations", "Purchase orders", "Approval workflows", "Vendor management"],
         related=["stockwise", "billora", "docuflow"]),

    dict(slug="buildora", name="Buildora", kicker="Construction Management", cat="assets", icon="build",
         desc="Construction project management for site activities, materials, labour, budgets, contractor payments and progress tracking.",
         tags=["Site activity", "Budgets", "Contractors"],
         title="Buildora — Construction Management Software | AALVINAI",
         kw="Construction project management software", is_a="construction project management software",
         audience="Construction companies and contractors",
         overview=["Buildora keeps construction projects on track by bringing site activities, materials, labour, budgets and contractor payments into one system, with progress tracking across every project."],
         features=["Site activities", "Materials", "Labour", "Budgets", "Contractor payments", "Progress tracking"],
         related=["procureflow", "assettrack", "stockwise"]),
    dict(slug="assettrack", name="AssetTrack", kicker="Asset Lifecycle", cat="assets", icon="asset",
         desc="Asset lifecycle management for equipment, computers, allocation, warranties, service records and maintenance schedules.",
         tags=["Allocation", "Warranty", "Service logs"],
         title="AssetTrack — Asset Management Software | AALVINAI",
         kw="Asset management software", is_a="asset lifecycle management software",
         audience="Organisations managing equipment and IT assets",
         overview=["AssetTrack follows every asset through its lifecycle — equipment and computers, who they are allocated to, warranties, service records and maintenance schedules — so service dates and warranty periods are not missed."],
         features=["Equipment & computers", "Allocation", "Warranties", "Service records", "Maintenance schedules"],
         related=["helpnest", "buildora", "stockwise"]),

    dict(slug="transaxis", name="TransAxis", kicker="Freight Operations Platform", cat="transport", icon="freight",
         desc="Fleet and transport-operations platform for Indian road-freight companies covering bookings, dispatch, trip tracking, cargo security, maintenance, GST invoicing, settlements, analytics and a document-grounded AI assistant.",
         tags=["Dispatch board", "GST & settlements", "Document AI"],
         title="TransAxis — Fleet & Transport Management | AALVINAI",
         kw="Fleet & transport management software", is_a="a fleet and transport-operations platform for road-freight companies",
         audience="Indian road-freight and transport companies",
         overview=["TransAxis is a fleet and transport-operations platform built for Indian road-freight companies. It covers vehicles and drivers, customers and vendors, bookings, trip planning and the full trip lifecycle on a dispatch board and calendar, cargo security, maintenance and fuel, GST invoicing and collections, expenses, crew settlements and a double-entry ledger.",
                   "Operations teams also get reports, a customer portal and a driver app, while a document library with an AI assistant answers questions with citations to the source documents."],
         features=["Vehicles & drivers", "Bookings & dispatch board", "Trip planning & lifecycle", "Cargo security", "Maintenance & fuel", "GST invoicing & collections", "Crew settlements & ledger", "Reports & analytics", "Customer portal & driver app", "Document AI assistant with citations", "Roles & audit log", "Two-step sign-in", "CSV import & export"],
         related=["assettrack", "insightiq", "billora"],
         deploy="Web · Driver app · Customer portal",
         meta="TransAxis is fleet and transport management software for Indian road-freight companies — bookings, dispatch, trip tracking, GST invoicing and settlements.",
         mobile="Yes. Alongside the web platform, TransAxis includes a driver app and a customer portal."),

    dict(slug="connectra", name="Connectra", kicker="Customer Relationship Management", cat="business", icon="crm",
         desc="CRM for customer profiles, lead tracking, sales pipelines, follow-ups and complete interaction history.",
         tags=["Leads", "Pipelines", "Follow-ups"],
         title="Connectra — CRM Software for Sales Teams | AALVINAI",
         kw="CRM software", is_a="CRM software",
         audience="Sales and customer-facing teams",
         overview=["Connectra is a CRM that keeps every customer relationship in one place: customer profiles, lead tracking, sales pipelines, follow-ups and a full history of every interaction."],
         features=["Customer profiles", "Lead tracking", "Sales pipelines", "Follow-ups", "Interaction history"],
         related=["billora", "helpnest", "insightiq"]),
    dict(slug="peoplehub", name="PeopleHub", kicker="HR & Workforce", cat="business", icon="hr",
         desc="HR and workforce management for employee records, recruitment, attendance, leave and payroll workflows.",
         tags=["Recruitment", "Attendance", "Payroll"],
         title="PeopleHub — HR & Payroll Software | AALVINAI",
         kw="HR & payroll software", is_a="HR and payroll software",
         audience="HR teams and growing workforces",
         overview=["PeopleHub brings HR into one system: employee records, recruitment, attendance and leave, and payroll workflows — from hiring through to payroll."],
         features=["Employee records", "Recruitment", "Attendance", "Leave", "Payroll workflows"],
         related=["docuflow", "helpnest", "skillforge"]),
    dict(slug="docuflow", name="DocuFlow", kicker="Document Management", cat="business", icon="doc",
         desc="Document management with version history, approval workflows, access permissions and expiry reminders.",
         tags=["Versions", "Permissions", "Reminders"],
         title="DocuFlow — Document Management System | AALVINAI",
         kw="Document management system", is_a="a document management system",
         audience="Teams that manage controlled documents",
         overview=["DocuFlow is a document management system with version history, approval workflows and access permissions, plus expiry reminders so renewals and reviews aren’t missed."],
         features=["Document management", "Version history", "Approval workflows", "Access permissions", "Expiry reminders"],
         related=["peoplehub", "procureflow", "helpnest"]),
    dict(slug="helpnest", name="HelpNest", kicker="Helpdesk & ITSM", cat="business", icon="help",
         desc="Helpdesk and IT service management for tickets, incidents, assignments, escalations and resolution history.",
         tags=["Tickets", "Escalations", "Resolution log"],
         title="HelpNest — Helpdesk & ITSM Software | AALVINAI",
         kw="Helpdesk & IT service management software", is_a="helpdesk and IT service management software",
         audience="IT and support teams",
         overview=["HelpNest is a helpdesk and IT service management tool. Tickets and incidents are logged, assigned and escalated, and every issue keeps a full resolution history."],
         features=["Tickets", "Incidents", "Assignments", "Escalations", "Resolution history"],
         related=["assettrack", "labops", "connectra"]),
    dict(slug="insightiq", name="InsightIQ", kicker="Business Intelligence", cat="business", icon="chart",
         desc="Business intelligence with dashboards, operational KPIs, trend analysis and management reporting.",
         tags=["Dashboards", "KPIs", "Trends"],
         title="InsightIQ — Business Intelligence Software | AALVINAI",
         kw="Business intelligence software", is_a="business intelligence and dashboard software",
         audience="Management teams tracking operations",
         overview=["InsightIQ turns operational data into decisions with dashboards, operational KPIs, trend analysis and management reports, so leadership can see how operations are performing at a glance."],
         features=["Dashboards", "Operational KPIs", "Trend analysis", "Management reports"],
         related=["connectra", "stockwise", "transaxis"]),

    dict(slug="globepath", name="GlobePath", kicker="Overseas Consultancy", cat="services", icon="globe",
         desc="Foreign consultancy management for clients, applications, documentation, follow-ups and case tracking.",
         tags=["Applications", "Documents", "Case stages"],
         title="GlobePath — Overseas Consultancy Software | AALVINAI",
         kw="Overseas consultancy management software", is_a="overseas consultancy management software",
         audience="Overseas and foreign consultancy firms",
         overview=["GlobePath manages foreign consultancy work — clients, their applications and documentation, follow-ups and case tracking — so the status of every case is visible at a glance."],
         features=["Client management", "Applications", "Documentation", "Follow-ups", "Case tracking"],
         related=["connectra", "docuflow", "bookora"]),
    dict(slug="docslot", name="DocSlot", kicker="Appointment Scheduling", cat="services", icon="slot",
         desc="Doctor appointment scheduling, patient registration, doctor availability and booking management.",
         tags=["Availability", "Bookings", "Registration"],
         title="DocSlot — Doctor Appointment Booking Software | AALVINAI",
         kw="Doctor appointment booking software", is_a="doctor appointment booking software",
         audience="Doctors, clinics and hospitals taking appointments",
         overview=["DocSlot handles doctor appointment scheduling, with patient registration, doctor availability and booking management in one place."],
         features=["Appointment scheduling", "Patient registration", "Doctor availability", "Booking management"],
         related=["carebridge", "medistock", "bookora"]),
    dict(slug="carebridge", name="CareBridge", kicker="Clinic Management", cat="services", icon="clinic",
         desc="Clinic administration for patient records, consultations, prescriptions, billing and follow-up scheduling.",
         tags=["Records", "Prescriptions", "Billing"],
         title="CareBridge — Clinic Management Software | AALVINAI",
         kw="Clinic management software", is_a="clinic management software",
         audience="Clinics and medical practices",
         overview=["CareBridge runs clinic administration in one system: patient records, consultations, prescriptions, billing and follow-up scheduling."],
         features=["Patient records", "Consultations", "Prescriptions", "Billing", "Follow-up scheduling"],
         related=["docslot", "medistock", "billora"]),

    dict(slug="eventora", name="Eventora", kicker="Event Management", cat="community", icon="event",
         desc="Event planning, registrations, attendee management, QR-code check-in, scheduling and event analytics.",
         tags=["Registrations", "QR check-in", "Analytics"],
         title="Eventora — Event Management Software | AALVINAI",
         kw="Event management software", is_a="event management software",
         audience="Event organisers and institutions running events",
         overview=["Eventora covers an event from planning to analytics: registrations, attendee management, scheduling, QR-code check-in at the venue and event analytics afterwards."],
         features=["Event planning", "Registrations", "Attendee management", "QR-code check-in", "Scheduling", "Event analytics"],
         related=["janconnect", "bookora", "connectra"]),
    dict(slug="janconnect", name="JanConnect", kicker="Membership Management", cat="community", icon="flag",
         desc="Political membership management, organisational units, membership records, volunteer coordination and authorised outreach.",
         tags=["Units", "Members", "Volunteers"],
         title="JanConnect — Political Membership Management | AALVINAI",
         kw="Political membership management software", is_a="membership management software for political organisations",
         audience="Political organisations and membership-based movements",
         overview=["JanConnect is membership management for political organisations, covering organisational units, membership records, volunteer coordination and authorised outreach in one system."],
         features=["Membership management", "Organisational units", "Membership records", "Volunteer coordination", "Authorised outreach"],
         related=["eventora", "connectra", "insightiq"],
         meta="JanConnect is political membership management software by AALVINAI Technologies — organisational units, membership records and volunteer coordination."),

    dict(slug="nexora", name="Nexora", kicker="Custom Development", cat="commerce", icon="code",
         desc="Custom e-commerce websites, business web applications, mobile applications and API integrations.",
         tags=["Web apps", "Mobile", "Integrations"],
         title="Nexora — Custom Web & Mobile App Development | AALVINAI",
         kw="Custom web & mobile app development", is_a="custom web, mobile and e-commerce development",
         audience="Businesses that need custom web, mobile or e-commerce builds",
         overview=["Nexora is AALVINAI’s custom development practice: e-commerce websites, business web applications, mobile applications and API integrations, built to your requirements by the same team that builds the rest of the portfolio."],
         features=["E-commerce websites", "Business web applications", "Mobile applications", "API integrations"],
         related=["shopnest", "bookora", "insightiq"],
         deploy="Web · Mobile · API",
         mobile="Yes — Nexora builds mobile applications as well as web applications and e-commerce websites."),
    dict(slug="shopnest", name="ShopNest", kicker="E-Commerce Platform", cat="commerce", icon="shop",
         desc="Online storefronts, product catalogues, shopping carts, orders, customer accounts and e-commerce administration.",
         tags=["Storefront", "Carts", "Orders"],
         title="ShopNest — E-commerce Store Platform | AALVINAI",
         kw="E-commerce platform", is_a="an e-commerce platform for online stores",
         audience="Brands and retailers selling online",
         overview=["ShopNest is an e-commerce platform for selling online, with storefronts, product catalogues, shopping carts, orders, customer accounts and store administration in one place."],
         features=["Online storefronts", "Product catalogues", "Shopping carts", "Orders", "Customer accounts", "E-commerce administration"],
         related=["stockwise", "pointops", "nexora"]),
    dict(slug="bookora", name="Bookora", kicker="Booking & Appointments", cat="commerce", icon="booking",
         desc="Booking and appointment management for service businesses, including availability, reservations, cancellations and notifications.",
         tags=["Slots", "Reservations", "Notifications"],
         title="Bookora — Booking & Appointment Software | AALVINAI",
         kw="Booking & appointment software", is_a="booking and appointment software for service businesses",
         audience="Service businesses that run on appointments",
         overview=["Bookora manages bookings and appointments for service businesses — availability, reservations, cancellations and notifications, all in one schedule."],
         features=["Availability", "Reservations", "Cancellations", "Notifications"],
         related=["docslot", "eventora", "payflow"]),
]

ICONS = {
    "campus": '<path d="M12 3.2 22 7.6 12 12 2 7.6Z"/><path d="M6 9.6v5.2c0 1.9 2.7 3.4 6 3.4s6-1.5 6-3.4V9.6"/><path d="M19.6 8.8v6.4"/>',
    "school": '<path d="M4 4.5h6a2 2 0 0 1 2 2v13"/><path d="M20 4.5h-6a2 2 0 0 0-2 2"/><path d="M4 4.5v13h6M20 4.5v13h-6"/>',
    "hostel": '<rect x="3" y="3.5" width="18" height="17" rx="2"/><path d="M7 8.5h3.5M7 12h3.5M7 15.5h3.5"/><path d="M14 20.5v-4.2a2 2 0 0 1 2-2h1a2 2 0 0 1 2 2v4.2"/>',
    "lab": '<rect x="2.5" y="4" width="19" height="12" rx="1.8"/><path d="M8.5 19.5h7M12 16v3.5"/><path d="M7 8h4M7 11h7"/>',
    "lms": '<path d="M3 6.2a18 18 0 0 1 9 2v11a16 16 0 0 0-9-2Z"/><path d="M21 6.2a18 18 0 0 0-9 2v11a16 16 0 0 1 9-2Z"/><path d="M16.5 3.5 19 5l-2.5 1.5"/>',
    "ledger": '<rect x="3.5" y="3" width="17" height="18" rx="2"/><path d="M8 3v18"/><path d="M11.5 8h5.5M11.5 12h5.5M11.5 16h3.5"/>',
    "wallet": '<path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H18a2 2 0 0 1 2 2v1"/><rect x="3" y="7.5" width="18" height="12" rx="2"/><circle cx="16.5" cy="13.5" r="1.3"/>',
    "chit": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.2"/><path d="M12 3.5v5.3M12 15.2v5.3M3.5 12h5.3M15.2 12h5.3"/>',
    "invoice": '<path d="M6 2.8h8.5L19 7.2v14H6Z"/><path d="M14 2.8v4.6h5"/><path d="M9 11.5h7M9 15h7M9 18h4"/>',
    "recur": '<path d="M20 11.5A8 8 0 0 0 6.2 6.4L4 8.6"/><path d="M4 4.6v4h4"/><path d="M4 12.5a8 8 0 0 0 13.8 5.1L20 15.4"/><path d="M20 19.4v-4h-4"/>',
    "pos": '<rect x="3.5" y="2.8" width="17" height="11" rx="1.8"/><path d="M7 6.2h10M7 9.6h5"/><path d="M5.5 17h13l1.5 4.2H4Z"/>',
    "pharma": '<path d="M9.4 5.6 5.6 9.4a4.5 4.5 0 0 0 6.4 6.4l3.8-3.8a4.5 4.5 0 0 0-6.4-6.4Z"/><path d="M7.5 7.5 14 14"/><path d="M18.5 15v5.5M15.8 17.8h5.4"/>',
    "boxes": '<path d="M3.5 7.6 12 3.6l8.5 4-8.5 4Z"/><path d="M3.5 7.6v8.8l8.5 4 8.5-4V7.6"/><path d="M12 11.6v8.8"/>',
    "procure": '<rect x="4.5" y="3.5" width="15" height="17.5" rx="2"/><path d="M9 3.5V2h6v1.5"/><path d="M8.5 12.2l2.2 2.2 4.6-4.6"/>',
    "build": '<path d="M3 20.5h18"/><path d="M6 20.5V8.5l9-3.6v15.6"/><path d="M15 11.5h4v9"/><path d="M9 11.5h3M9 15h3"/>',
    "asset": '<path d="M11 2.8h8a2 2 0 0 1 2 2v8L11.8 21.6a1.6 1.6 0 0 1-2.3 0L2.6 14.7a1.6 1.6 0 0 1 0-2.3Z"/><circle cx="16.8" cy="7.2" r="1.5"/>',
    "freight": '<path d="M2.5 15.8V7h9v8.8"/><path d="M11.5 10.2h3.6l3.4 3.1v2.5h-7"/><circle cx="6" cy="17.3" r="1.7"/><circle cx="15.8" cy="17.3" r="1.7"/><path d="M1.2 19.6h21.6"/>',
    "crm": '<circle cx="9" cy="8" r="3.2"/><path d="M3.5 20c0-3.3 2.5-5.8 5.5-5.8s5.5 2.5 5.5 5.8"/><circle cx="17.5" cy="7" r="2.3"/><path d="M15.8 14.6c2.7.4 4.7 2.6 4.7 5.4"/>',
    "hr": '<rect x="2.8" y="4.5" width="18.4" height="15" rx="2"/><circle cx="9" cy="11" r="2.4"/><path d="M5.4 16.6c0-1.9 1.6-3.2 3.6-3.2s3.6 1.3 3.6 3.2"/><path d="M15.5 10h3.2M15.5 13.4h3.2"/>',
    "doc": '<path d="M8.5 2.8H16l4 4v11.4H8.5Z"/><path d="M15.5 2.8v4.4H20"/><path d="M5.5 6.4v14.8h11"/>',
    "help": '<path d="M4 13.5v-1.8a8 8 0 0 1 16 0v1.8"/><rect x="2.2" y="12.6" width="4" height="6" rx="1.6"/><rect x="17.8" y="12.6" width="4" height="6" rx="1.6"/><path d="M19.8 18.6v.6a2.4 2.4 0 0 1-2.4 2.4H13"/>',
    "chart": '<path d="M3.5 3.5v17h17"/><path d="M7 16.5v-4M11.3 16.5V8.4M15.6 16.5v-6M19.9 16.5V5.6"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.6 2.6 2.6 15 0 18-2.6-3-2.6-15.4 0-18Z"/>',
    "slot": '<rect x="3.2" y="4.8" width="17.6" height="16" rx="2"/><path d="M3.2 9.6h17.6M8 2.8v3.6M16 2.8v3.6"/><path d="M12 12.4v3l2.2 1.3"/>',
    "clinic": '<rect x="3" y="3.5" width="18" height="17" rx="2.5"/><path d="M12 8.4v7.2M8.4 12h7.2"/>',
    "event": '<path d="M3 8.6V6.4h18v2.2a2 2 0 0 0 0 4v2.2"/><path d="M21 14.8v2.8H3v-2.8a2 2 0 0 0 0-4V8.6"/><path d="M9.5 6.4v11.2"/>',
    "flag": '<path d="M5.5 21V3.5"/><path d="M5.5 4.2h10.8l-1.6 3.8 1.6 3.8H5.5"/><path d="M5.5 15.4h8"/>',
    "code": '<path d="M8.6 7.5 4.2 12l4.4 4.5"/><path d="M15.4 7.5 19.8 12l-4.4 4.5"/><path d="M13.2 4.5l-2.4 15"/>',
    "shop": '<path d="M3.2 8.4 5 3.8h14l1.8 4.6"/><path d="M4.4 8.4v11.8h15.2V8.4"/><path d="M3.2 8.4a2.6 2.6 0 0 0 4.4 1.8 2.6 2.6 0 0 0 4.4-1.8 2.6 2.6 0 0 0 4.4 1.8 2.6 2.6 0 0 0 4.4-1.8"/>',
    "booking": '<rect x="3.2" y="4.8" width="17.6" height="16" rx="2"/><path d="M3.2 9.6h17.6M8 2.8v3.6M16 2.8v3.6"/><path d="M8.8 14.6l2.2 2.2 4.2-4.4"/>',
}

ORG = {
    "@type": "Organization",
    "@id": SITE + "/#organization",
    "name": "AALVINAI Technologies",
    "url": SITE + "/",
    "logo": SITE + "/logo-mark-512.png",
    "email": "hello@aalvinai.in",
    "telephone": "+91-94926-33000",
    "address": {"@type": "PostalAddress", "addressRegion": "Tamil Nadu", "addressCountry": "IN"},
}

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

SVG_ATTR = 'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"'
CHECK_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.2 4.2L19 7"/></svg>'

CAT_BY_SLUG = {c[0]: c for c in CATEGORIES}
PROD_BY_SLUG = {p["slug"]: p for p in PRODUCTS}

_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def number_words(n):
    """1..99 -> 'thirty-one'."""
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + ("-" + _ONES[ones] if ones else "")


def esc(s):
    """Escape text content (apostrophes and quotes stay literal)."""
    return html.escape(s, quote=False)


def attr(s):
    """Escape an attribute value."""
    return html.escape(s, quote=True)


def lower_first(s):
    """'Student records' -> 'student records', but leave 'KYC' / 'GST invoicing' alone."""
    if len(s) > 1 and s[1].isupper():
        return s
    return s[:1].lower() + s[1:]


def join_list(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def icon_svg(key):
    return '<svg %s>%s</svg>' % (SVG_ATTR, ICONS[key])


def render(template, **values):
    out = template
    for key, value in values.items():
        out = out.replace("@@%s@@" % key, value)
    leftover = re.findall(r"@@[A-Z_]+@@", out)
    if leftover:
        raise ValueError("unfilled placeholders: %s" % sorted(set(leftover)))
    return out


def product_url(p):
    return "%s/products/%s/" % (SITE, p["slug"])


def numbered():
    """Products in display order (category order, then list order) with their catalogue number."""
    ordered = []
    for slug, *_ in CATEGORIES:
        ordered += [p for p in PRODUCTS if p["cat"] == slug]
    missing = [p["slug"] for p in PRODUCTS if p["cat"] not in CAT_BY_SLUG]
    if missing:
        raise ValueError("unknown category for: %s" % missing)
    return [(i + 1, p) for i, p in enumerate(ordered)]


def meta_description(p):
    """A <=160 character description built from the product's own capability list."""
    if p.get("meta"):
        return p["meta"]
    head = "%s is %s by AALVINAI Technologies" % (p["name"], p["is_a"])
    feats = [lower_first(f) for f in p["features"]]
    for n in range(len(feats), 0, -1):
        body = "%s — %s." % (head, join_list(feats[:n]))
        if len(body) <= 145:
            tail = " Built in India."
            return body + tail if len(body + tail) <= 160 else body
    return head + "."


def validate():
    problems = []
    slugs = [p["slug"] for p in PRODUCTS]
    if len(slugs) != len(set(slugs)):
        problems.append("duplicate slugs")
    for p in PRODUCTS:
        for r in p["related"]:
            if r not in PROD_BY_SLUG or r == p["slug"]:
                problems.append("%s: bad related slug %r" % (p["slug"], r))
        if p["icon"] not in ICONS:
            problems.append("%s: unknown icon %r" % (p["slug"], p["icon"]))
        if len(p["title"]) > 60:
            problems.append("%s: title is %d chars (keep <= 60)" % (p["slug"], len(p["title"])))
        if not re.fullmatch(r"[a-z0-9-]+", p["slug"]):
            problems.append("%s: slug must be lowercase letters, digits and hyphens" % p["slug"])
    if problems:
        raise SystemExit("data problems:\n  " + "\n  ".join(problems))


# ──────────────────────────────────────────────────────────────────────────────
# PRODUCTS.HTML  (the catalogue hub)
# ──────────────────────────────────────────────────────────────────────────────

def hub_card(num, p, i):
    url = "products/%s/" % p["slug"]
    search = " ".join([p["name"], p["kicker"], p["desc"]] + p["tags"]).lower()
    delay = round(0.04 * (i % 3) + 0.04, 2)
    tags = "".join("<li>%s</li>" % esc(t) for t in p["tags"])
    return (
        '        <article class="prod rv" style="--d:%ss" data-cat="%s" data-search="%s">\n'
        '          <span class="prod-accent" aria-hidden="true"></span>\n'
        '          <header class="prod-head">\n'
        '            <span class="prod-icon" aria-hidden="true">%s</span>\n'
        '            <span class="prod-num">%02d</span>\n'
        '          </header>\n'
        '          <h3 class="prod-name"><a href="%s">%s</a></h3>\n'
        '          <p class="prod-kicker">%s</p>\n'
        '          <p class="prod-desc">%s</p>\n'
        '          <ul class="prod-tags">%s</ul>\n'
        '          <div class="prod-actions">\n'
        '            <a class="prod-cta" href="%s"><span>Explore %s</span><i aria-hidden="true">&#8594;</i></a>\n'
        '            <button type="button" class="prod-cta-alt" data-modal-open="contactModal" data-product="%s">Request a walkthrough</button>\n'
        '          </div>\n'
        '        </article>'
    ) % (delay, p["cat"], attr(search), icon_svg(p["icon"]), num, url, esc(p["name"]),
         esc(p["kicker"]), esc(p["desc"]), tags, url, esc(p["name"]), attr(p["name"]))


def hub_blocks(items):
    out = []
    for idx, (slug, title, blurb, _short) in enumerate(CATEGORIES, start=1):
        in_cat = [(n, p) for n, p in items if p["cat"] == slug]
        cards = "\n".join(hub_card(n, p, i) for i, (n, p) in enumerate(in_cat))
        out.append(
            '    <section class="cat" id="%s" data-cat-block="%s">\n'
            '      <div class="cat-head rv">\n'
            '        <span class="cat-idx">%02d</span>\n'
            '        <div class="cat-head-text">\n'
            '          <h2 class="cat-title">%s</h2>\n'
            '          <p class="cat-blurb">%s</p>\n'
            '        </div>\n'
            '        <span class="cat-count">%d product%s</span>\n'
            '      </div>\n'
            '      <div class="prod-grid">\n%s\n      </div>\n'
            '    </section>' % (slug, slug, idx, esc(title), esc(blurb), len(in_cat),
                                "" if len(in_cat) == 1 else "s", cards))
    return "\n\n".join(out)


def hub_chips():
    chips = ['      <button type="button" class="chip is-active" data-filter="all" aria-pressed="true">All <span>%d</span></button>' % len(PRODUCTS)]
    for slug, _title, _blurb, short in CATEGORIES:
        n = len([p for p in PRODUCTS if p["cat"] == slug])
        chips.append('      <button type="button" class="chip" data-filter="%s" aria-pressed="false">%s <span>%d</span></button>' % (slug, esc(short), n))
    return "\n".join(chips)


def hub_jsonld(items):
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": SITE + "/products.html#webpage",
                "url": SITE + "/products.html",
                "name": "Business Software Products — AALVINAI Technologies",
                "description": "%d business software products built in-house in Tamil Nadu, India — ERP, finance, billing, POS, inventory, transport, CRM, HR, healthcare and e-commerce." % len(PRODUCTS),
                "inLanguage": "en-IN",
                "isPartOf": {"@id": SITE + "/#website"},
                "about": {"@id": SITE + "/#organization"},
                "breadcrumb": {"@id": SITE + "/products.html#breadcrumb"},
                "mainEntity": {"@id": SITE + "/products.html#catalogue"},
            },
            {
                "@type": "ItemList",
                "@id": SITE + "/products.html#catalogue",
                "name": "AALVINAI Products Portfolio",
                "numberOfItems": len(items),
                "itemListOrder": "https://schema.org/ItemListOrderAscending",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": n,
                        "url": product_url(p),
                        "name": "%s — %s" % (p["name"], p["kw"]),
                    }
                    for n, p in items
                ],
            },
            {
                "@type": "BreadcrumbList",
                "@id": SITE + "/products.html#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                    {"@type": "ListItem", "position": 2, "name": "Products", "item": SITE + "/products.html"},
                ],
            },
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def splice(text, start, end, new, label):
    a = text.find(start)
    b = text.find(end, a + len(start)) if a != -1 else -1
    if a == -1 or b == -1:
        raise SystemExit("products.html: markers for %s not found (%r ... %r)" % (label, start, end))
    return text[:a + len(start)] + new + text[b:]


def build_hub(text, items):
    text = splice(text, '<script type="application/ld+json" id="catalogue-jsonld">', "</script>",
                  "\n" + hub_jsonld(items) + "\n", "JSON-LD")
    text = splice(text, "<!-- chips:start -->", "<!-- chips:end -->", "\n" + hub_chips() + "\n      ", "chips")
    text = splice(text, "<!-- catalogue:start -->", "<!-- catalogue:end -->", "\n" + hub_blocks(items) + "\n  ", "catalogue")
    return text


def hub_count_warnings(text):
    n, cats = len(PRODUCTS), len(CATEGORIES)
    checks = [
        (r'<b>(\d+)</b><span>Products</span>', n, "hero product count"),
        (r'<b>(\d+)</b><span>Domains</span>', cats, "hero domain count"),
        (r'Showing all (\d+) products', n, "toolbar count"),
    ]
    warnings = []
    for pattern, want, label in checks:
        m = re.search(pattern, text)
        if m and int(m.group(1)) != want:
            warnings.append("%s says %s, data has %d" % (label, m.group(1), want))
    m = re.search(r'class="hero-h1[^>]*>([A-Za-z-]+) ', text)
    if m and m.group(1).lower() != number_words(n):
        warnings.append('hero heading says "%s", data has %d (%s)' % (m.group(1), n, number_words(n).capitalize()))
    return warnings


# ──────────────────────────────────────────────────────────────────────────────
# PRODUCT LANDING PAGES
# ──────────────────────────────────────────────────────────────────────────────

PAGE_CSS = r"""
:root{
  --ink:#fafafa; --muted:#a7a6a6; --nav:#b6b5b5; --strip:#8b8a8a;
  --pill:#ffffff; --pill-ink:#050505; --stage:#050505; --surface:#0a0a0a;
  --warm:#c9a274; --warm-dim:rgba(201,162,116,.5);
  --line:rgba(255,255,255,.09); --line-soft:rgba(255,255,255,.05);
  --edge:clamp(20px, 5vw, 64px); --section-y:clamp(48px, 6.5vw, 92px);
  --maxw:1280px; --head-h:66px; --ease:cubic-bezier(.22,1,.36,1);
}
*,*::before,*::after{ box-sizing:border-box; }
html{ background:var(--stage); scroll-padding-top:calc(var(--head-h) + 24px); }
@media (prefers-reduced-motion: no-preference){ html{ scroll-behavior:smooth; } }
html,body{ margin:0; padding:0; min-height:100%; overflow-x:hidden; }
body{
  background:var(--stage); color:var(--muted);
  font-family:'Poppins',system-ui,-apple-system,'Segoe UI',sans-serif;
  -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale;
  text-rendering:geometricPrecision; position:relative;
}
body::after{
  content:""; position:fixed; inset:0; z-index:999; pointer-events:none;
  opacity:.05; mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
a{ color:inherit; text-decoration:none; }
button{ font:inherit; color:inherit; background:none; border:0; cursor:pointer; }
:focus-visible{ outline:1px solid var(--warm); outline-offset:3px; }
.wrap{ max-width:var(--maxw); margin-inline:auto; padding-inline:var(--edge); position:relative; }
.visually-hidden{ position:absolute; width:1px; height:1px; margin:-1px; padding:0; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; border:0; }

/* header */
.header{
  position:sticky; top:0; z-index:60; min-height:var(--head-h);
  display:flex; align-items:center; border-bottom:1px solid var(--line);
  background:rgba(5,5,5,.82);
  -webkit-backdrop-filter:blur(14px) saturate(140%); backdrop-filter:blur(14px) saturate(140%);
}
.header-in{ display:flex; align-items:center; justify-content:space-between; gap:18px; width:100%; }
.brand{
  display:inline-flex; align-items:center; gap:11px; color:var(--ink);
  font-family:'Space Grotesk','Poppins',sans-serif; font-weight:700; font-size:14px; letter-spacing:.03em; white-space:nowrap;
}
.brand img{ width:27px; height:27px; display:block; flex:none; }
.brand span i{ font-style:normal; font-weight:400; color:var(--strip); letter-spacing:.14em; font-size:10.5px; display:block; margin-top:1px; }
.hnav{ display:flex; align-items:center; gap:clamp(16px, 2.2vw, 34px); }
.hnav a, .hnav button{ font-size:13.5px; color:var(--nav); transition:color .28s var(--ease); }
.hnav a:hover, .hnav button:hover{ color:#fff; }
.hnav a[aria-current]{ color:var(--ink); }
.hnav a[aria-current]::after{ content:""; display:block; height:1px; margin-top:5px; background:var(--warm); }
.pill{
  display:inline-flex; align-items:center; gap:7px; background:var(--pill); color:var(--pill-ink);
  border-radius:999px; padding:10px 20px; font-size:13px; font-weight:500; white-space:nowrap;
  transition:transform .3s var(--ease), box-shadow .3s var(--ease), opacity .3s var(--ease);
}
.pill:hover{ transform:translateY(-1px); box-shadow:0 10px 30px rgba(255,255,255,.14); }
.pill i{ font-style:normal; }
.pill-ghost{ background:transparent; color:var(--ink); border:1px solid var(--line); }
.pill-ghost:hover{ border-color:var(--nav); background:rgba(255,255,255,.05); box-shadow:none; }
@media (max-width:900px){ .hnav{ display:none; } }
@media (max-width:420px){ .pill{ padding:9px 16px; font-size:12.5px; } }

.eyebrow{
  display:inline-flex; align-items:center; gap:10px; margin:0;
  font-size:11px; font-weight:600; letter-spacing:.2em; text-transform:uppercase; color:var(--strip);
}
.eyebrow::before{ content:""; width:22px; height:1px; background:var(--warm-dim); flex:none; }
.marks{ position:absolute; inset:0; pointer-events:none; }
.marks i{ position:absolute; width:13px; height:13px; border:1px solid var(--line); }
.marks i:nth-child(1){ top:-1px; left:-1px; border-right:0; border-bottom:0; }
.marks i:nth-child(2){ top:-1px; right:-1px; border-left:0; border-bottom:0; }
.marks i:nth-child(3){ bottom:-1px; left:-1px; border-right:0; border-top:0; }
.marks i:nth-child(4){ bottom:-1px; right:-1px; border-left:0; border-top:0; }

/* hero */
.pd-hero{ position:relative; padding-block:clamp(34px, 5.5vw, 80px) clamp(44px, 6vw, 88px); overflow:clip; border-bottom:1px solid var(--line); }
.pd-hero::before{
  content:""; position:absolute; inset:0; z-index:0; pointer-events:none;
  background:radial-gradient(70% 120% at 82% 0%, rgba(201,162,116,.11), transparent 62%),
             radial-gradient(55% 90% at 8% 8%, rgba(255,255,255,.035), transparent 60%);
}
.pd-hero::after{
  content:""; position:absolute; inset:0; z-index:0; pointer-events:none;
  background-image:linear-gradient(to right, rgba(255,255,255,.04) 1px, transparent 1px),
                   linear-gradient(to bottom, rgba(255,255,255,.04) 1px, transparent 1px);
  background-size:72px 72px, 72px 72px;
  -webkit-mask-image:radial-gradient(130% 100% at 50% 0%, #000 12%, transparent 76%);
  mask-image:radial-gradient(130% 100% at 50% 0%, #000 12%, transparent 76%);
}
.pd-hero > .wrap{ z-index:1; }
.crumb{ margin:0 0 28px; font-size:11.5px; letter-spacing:.06em; color:var(--strip); }
.crumb ol{ list-style:none; margin:0; padding:0; display:flex; flex-wrap:wrap; align-items:center; gap:8px; }
.crumb li{ display:inline-flex; align-items:center; gap:8px; }
.crumb li + li::before{ content:"/"; opacity:.5; }
.crumb a{ color:var(--nav); transition:color .25s var(--ease); }
.crumb a:hover{ color:var(--warm); }
.pd-hero-in{ display:grid; grid-template-columns:minmax(0, 1.35fr) minmax(280px, .85fr); gap:clamp(30px, 5vw, 76px); align-items:center; }
.pd-h1{ margin:18px 0 0; font-family:'Space Grotesk','Poppins',sans-serif; font-weight:600; color:var(--ink); line-height:1.02; letter-spacing:-.035em; }
.pd-name{ display:block; font-size:clamp(40px, 6.6vw, 78px); }
.pd-kw{ display:block; margin-top:14px; font-size:clamp(18px, 2.3vw, 28px); line-height:1.2; letter-spacing:-.02em; font-weight:500; color:var(--warm); }
.pd-lead{ margin:22px 0 0; max-width:60ch; font-size:clamp(14px, 1.2vw, 16px); line-height:1.75; color:var(--muted); }
.pd-actions{ margin-top:clamp(24px, 3vw, 32px); display:flex; flex-wrap:wrap; gap:12px; }
.pd-actions .pill{ padding:13px 24px; font-size:13.5px; }

.pd-card{
  position:relative; border:1px solid var(--line); padding:clamp(22px, 2.4vw, 30px);
  background:linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,.006));
}
.pd-card::before{ content:""; position:absolute; inset:0; pointer-events:none; background:radial-gradient(90% 70% at 100% 0%, rgba(201,162,116,.12), transparent 60%); }
.pd-card-head{ position:relative; display:flex; align-items:center; justify-content:space-between; gap:12px; }
.pd-card-icon{ width:64px; height:64px; border-radius:50%; border:1px solid var(--warm-dim); color:var(--warm); display:grid; place-items:center; }
.pd-card-icon svg{ width:30px; height:30px; display:block; }
.pd-card-num{ font-family:'Space Grotesk','Poppins',sans-serif; font-size:11px; letter-spacing:.12em; color:var(--strip); }
.pd-facts{ position:relative; margin:22px 0 0; }
.pd-facts div{ display:grid; grid-template-columns:104px 1fr; gap:14px; padding:13px 0; border-top:1px solid var(--line-soft); }
.pd-facts dt{ padding-top:2px; font-size:10.5px; letter-spacing:.14em; text-transform:uppercase; color:var(--strip); }
.pd-facts dd{ margin:0; font-size:13.5px; line-height:1.5; color:var(--ink); }
@media (max-width:900px){ .pd-hero-in{ grid-template-columns:1fr; } }

/* sections */
.pd-sec{ position:relative; padding-block:var(--section-y); border-bottom:1px solid var(--line); }
.pd-h2{ margin:14px 0 0; font-family:'Space Grotesk','Poppins',sans-serif; font-size:clamp(22px, 2.6vw, 34px); line-height:1.18; font-weight:600; letter-spacing:-.025em; color:var(--ink); }
.pd-split{ display:grid; grid-template-columns:minmax(0, .8fr) minmax(0, 1.2fr); gap:clamp(24px, 5vw, 80px); align-items:start; }
@media (max-width:820px){ .pd-split{ grid-template-columns:1fr; } }
.pd-prose p{ margin:0; font-size:clamp(14.5px, 1.3vw, 17px); line-height:1.8; color:var(--muted); }
.pd-prose p + p{ margin-top:18px; }
.pd-prose a{ color:var(--ink); border-bottom:1px solid var(--warm-dim); transition:color .25s var(--ease); }
.pd-prose a:hover{ color:var(--warm); }

.pd-features{ list-style:none; margin:clamp(22px, 3vw, 32px) 0 0; padding:0; display:grid; grid-template-columns:repeat(auto-fill, minmax(230px, 1fr)); gap:10px; }
.pd-features li{
  display:flex; align-items:flex-start; gap:12px; padding:18px 20px; border:1px solid var(--line);
  background:linear-gradient(180deg, rgba(255,255,255,.02), transparent);
  font-size:14px; line-height:1.5; color:var(--ink);
}
.pd-features svg{ flex:none; width:16px; height:16px; margin-top:2px; color:var(--warm); }
@media (max-width:560px){
  .pd-features{ grid-template-columns:1fr 1fr; gap:8px; }
  .pd-features li{ padding:14px; gap:9px; font-size:13px; }
}

.pd-why{ margin-top:clamp(22px, 3vw, 32px); display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:10px; }
.pd-why > div{ border:1px solid var(--line); padding:22px; }
.pd-why-num{ font-family:'Space Grotesk','Poppins',sans-serif; font-size:11px; letter-spacing:.1em; color:var(--warm); }
.pd-why h3{ margin:12px 0 0; font-family:'Space Grotesk','Poppins',sans-serif; font-size:16px; font-weight:600; color:var(--ink); letter-spacing:-.01em; }
.pd-why p{ margin:8px 0 0; font-size:13px; line-height:1.65; color:var(--muted); }
@media (max-width:1000px){ .pd-why{ grid-template-columns:1fr 1fr; } }
@media (max-width:560px){ .pd-why{ grid-template-columns:1fr; } }

.pd-related{ margin-top:clamp(22px, 3vw, 32px); display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:12px; }
.pd-rel{
  position:relative; display:flex; flex-direction:column; padding:22px; border:1px solid var(--line);
  background:linear-gradient(180deg, rgba(255,255,255,.022), rgba(255,255,255,.004));
  transition:border-color .45s var(--ease), transform .45s var(--ease);
}
.pd-rel:hover, .pd-rel:focus-visible{ border-color:rgba(255,255,255,.17); transform:translateY(-3px); }
.pd-rel-icon{ width:34px; height:34px; display:grid; place-items:center; border:1px solid var(--line); border-radius:50%; color:var(--nav); transition:color .4s var(--ease), border-color .4s var(--ease); }
.pd-rel-icon svg{ width:18px; height:18px; display:block; }
.pd-rel:hover .pd-rel-icon{ color:var(--warm); border-color:var(--warm-dim); }
.pd-rel-name{ margin-top:16px; font-family:'Space Grotesk','Poppins',sans-serif; font-size:18px; font-weight:600; color:var(--ink); letter-spacing:-.015em; }
.pd-rel-kicker{ margin-top:5px; font-size:10.5px; letter-spacing:.14em; text-transform:uppercase; color:var(--warm); }
.pd-rel-desc{ margin-top:12px; font-size:12.8px; line-height:1.62; color:var(--muted); }
.pd-rel-go{ margin-top:auto; padding-top:16px; font-size:10.5px; letter-spacing:.11em; text-transform:uppercase; color:var(--nav); }
.pd-rel-go i{ font-style:normal; display:inline-block; margin-left:6px; transition:transform .4s var(--ease); }
.pd-rel:hover .pd-rel-go{ color:var(--ink); }
.pd-rel:hover .pd-rel-go i{ transform:translateX(5px); }
@media (max-width:900px){ .pd-related{ grid-template-columns:1fr; } }

.pd-faq details{ border-top:1px solid var(--line); }
.pd-faq details:last-child{ border-bottom:1px solid var(--line); }
.pd-faq summary{
  list-style:none; cursor:pointer; display:flex; align-items:center; justify-content:space-between; gap:18px; padding:20px 0;
  font-family:'Space Grotesk','Poppins',sans-serif; font-size:clamp(15px, 1.4vw, 18px); font-weight:600; color:var(--ink);
}
.pd-faq summary::-webkit-details-marker{ display:none; }
.pd-faq summary::after{ content:"+"; flex:none; font-size:22px; font-weight:400; line-height:1; color:var(--warm); transition:transform .3s var(--ease); }
.pd-faq details[open] summary::after{ transform:rotate(45deg); }
.pd-faq p{ margin:0 0 22px; max-width:64ch; font-size:14px; line-height:1.75; color:var(--muted); }
.pd-faq a{ color:var(--ink); border-bottom:1px solid var(--warm-dim); }

/* cta + footer */
.cta{ position:relative; border-bottom:1px solid var(--line); padding-block:clamp(50px, 7vw, 94px); overflow:clip; text-align:center; }
.cta::before{ content:""; position:absolute; inset:0; pointer-events:none; background:radial-gradient(60% 110% at 50% 100%, rgba(201,162,116,.12), transparent 62%); }
.cta > .wrap{ z-index:1; }
.cta .eyebrow{ justify-content:center; }
.cta-h{ margin:17px 0 0; font-family:'Space Grotesk','Poppins',sans-serif; font-size:clamp(23px, 3.4vw, 42px); line-height:1.1; letter-spacing:-.03em; font-weight:600; color:var(--ink); }
.cta-p{ margin:16px auto 0; max-width:52ch; font-size:13.6px; line-height:1.7; color:var(--muted); }
.cta-actions{ margin-top:clamp(26px, 3.4vw, 38px); display:flex; align-items:center; justify-content:center; gap:12px; flex-wrap:wrap; }
.cta-actions .pill{ padding:14px 27px; font-size:13.5px; }

.site-footer{ position:relative; padding-block:clamp(40px,6vw,62px) 0; background:linear-gradient(180deg, #060606 0%, #030303 100%); }
.footer-grid{ display:grid; grid-template-columns:minmax(300px, 1.5fr) minmax(130px, .85fr) minmax(150px, .9fr) minmax(170px, 1fr); gap:30px; }
.footer-col{ display:flex; flex-direction:column; gap:14px; }
.footer-col-h{ margin:0 0 3px; font-size:11px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:var(--ink); }
.footer-col a, .footer-col button, .footer-col span{ font-size:13.5px; line-height:1.4; color:var(--nav); transition:color .3s var(--ease); text-align:left; }
.footer-col a:hover, .footer-col button:hover{ color:var(--ink); }
.footer-col a[aria-current]{ color:var(--ink); }
.footer-col span{ color:var(--strip); }
.footer-col-brand{ gap:18px; }
.footer-brand{ display:flex; align-items:center; gap:10px; }
.footer-brand img{ width:24px; height:auto; flex:none; }
.footer-brand-name{ font-size:15px; color:var(--ink); font-weight:700; }
.footer-desc{ margin:0; font-size:13.5px; line-height:1.62; color:var(--nav); max-width:36ch; }
.footer-social{ display:flex; gap:8px; flex-wrap:wrap; }
.footer-social a{
  display:inline-flex; align-items:center; gap:6px; padding:7px 13px; border:1px solid var(--line); border-radius:999px;
  font-size:12px; color:var(--nav); white-space:nowrap;
  transition:color .3s var(--ease), border-color .3s var(--ease), background-color .3s var(--ease);
}
.footer-social svg{ width:13px; height:13px; flex:none; }
.footer-social a:hover{ color:var(--ink); border-color:var(--nav); background:rgba(255,255,255,.05); }
@media (max-width:1040px){ .footer-grid{ grid-template-columns:1fr 1fr; row-gap:34px; } .footer-col-brand{ grid-column:1 / -1; } }
@media (max-width:640px){ .footer-grid{ grid-template-columns:1fr; gap:28px; } .footer-col-brand{ grid-column:auto; } }
.footer-bottom{ margin-top:clamp(30px,5vw,46px); padding-block:18px; border-top:1px solid var(--line-soft); display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; }
.footer-bottom p{ margin:0; font-size:11px; color:var(--strip); }
.footer-legal{ display:flex; gap:22px; }
.footer-legal a{ font-size:12px; color:var(--nav); transition:color .3s var(--ease); }
.footer-legal a:hover{ color:var(--ink); }

/* reveal */
.rv{ opacity:0; transform:translateY(24px); transition:opacity .85s var(--ease), transform .85s var(--ease); transition-delay:var(--d, 0s); }
.rv.is-in{ opacity:1; transform:translateY(0); }
.no-js .rv{ opacity:1; transform:none; }
@media (prefers-reduced-motion: reduce){
  .rv{ opacity:1; transform:none; transition:none; }
  .pill:hover, .pd-rel:hover{ transform:none; }
}
@media (pointer:coarse){ .hnav a, .hnav button{ min-height:34px; display:inline-flex; align-items:center; } }

/* contact modal */
.modal{ position:fixed; inset:0; z-index:200; display:flex; align-items:center; justify-content:center; padding:24px; visibility:hidden; opacity:0; transition:opacity .35s var(--ease), visibility .35s var(--ease); }
.modal.is-open{ visibility:visible; opacity:1; }
.modal-backdrop{ position:absolute; inset:0; background:rgba(5,5,5,.72); -webkit-backdrop-filter:blur(6px); backdrop-filter:blur(6px); }
.modal-panel{
  position:relative; width:100%; max-width:900px; max-height:88vh; overflow-y:auto; scrollbar-width:none;
  background:var(--surface); border:1px solid var(--line); padding:clamp(28px,4vw,52px);
  transform:translateY(16px) scale(.98); opacity:0; transition:transform .4s var(--ease), opacity .4s var(--ease);
}
.modal-panel::-webkit-scrollbar{ display:none; width:0; height:0; }
.modal.is-open .modal-panel{ transform:translateY(0) scale(1); opacity:1; }
.modal-close{ position:absolute; top:20px; right:20px; display:grid; place-items:center; width:34px; height:34px; border:1px solid var(--line); border-radius:50%; color:var(--nav); transition:color .3s var(--ease), border-color .3s var(--ease); }
.modal-close:hover, .modal-close:focus-visible{ color:var(--warm); border-color:var(--warm-dim); }
.modal-close svg{ width:14px; height:14px; }
.modal-title{ margin:14px 0 0; font-family:'Space Grotesk','Poppins',sans-serif; font-size:clamp(28px,3.6vw,42px); line-height:1.08; font-weight:600; letter-spacing:-.02em; color:var(--ink); }
.modal-sub{ margin:14px 0 0; font-size:15px; line-height:1.6; color:var(--muted); max-width:50ch; }
.modal-body{ margin-top:clamp(30px,4vw,44px); display:grid; grid-template-columns:1.15fr 1fr; gap:clamp(28px,4vw,56px); align-items:start; }
.contact-field{ display:flex; flex-direction:column; gap:9px; margin-bottom:18px; }
.contact-field label{ font-size:13px; font-weight:600; color:var(--ink); }
.contact-field input, .contact-field textarea{
  width:100%; font-family:inherit; font-size:14px; color:var(--ink); background:rgba(255,255,255,.035);
  border:1px solid var(--line); border-radius:6px; padding:14px 16px; resize:vertical;
  transition:border-color .3s var(--ease), background-color .3s var(--ease);
}
.contact-field input::placeholder, .contact-field textarea::placeholder{ color:var(--strip); }
.contact-field input:focus, .contact-field textarea:focus{ outline:none; border-color:var(--warm-dim); background:rgba(255,255,255,.06); }
.contact-form .pill{ width:100%; height:54px; margin-top:8px; font-size:15px; justify-content:center; }
.contact-form .pill:disabled{ opacity:.6; cursor:wait; transform:none; box-shadow:none; }
.form-status{ margin:12px 0 0; font-size:13px; line-height:1.5; display:none; }
.form-status.is-ok{ display:block; color:#8fd19e; }
.form-status.is-err{ display:block; color:#e2938f; }
.contact-info{ display:flex; flex-direction:column; }
.info-row{ display:grid; grid-template-columns:22px 1fr; column-gap:16px; align-items:start; padding-block:22px; border-top:1px solid var(--line); }
.info-row:first-child{ border-top:0; padding-top:4px; }
.info-icon{ color:var(--nav); padding-top:2px; }
.info-icon svg{ display:block; width:17px; height:17px; }
.info-label{ display:block; font-size:11px; font-weight:600; letter-spacing:.16em; text-transform:uppercase; color:var(--nav); }
.info-value{ margin:10px 0 0; font-size:14.5px; line-height:1.75; color:var(--muted); }
.info-value a{ color:var(--muted); border-bottom:1px solid var(--line); transition:color .3s var(--ease), border-color .3s var(--ease); }
.info-value a:hover{ color:var(--warm); border-color:var(--warm-dim); }
@media (max-width:820px){ .modal-body{ grid-template-columns:1fr; gap:32px; } }
@supports (height:100dvh){ @media (max-width:1024px){ .modal-panel{ max-height:88dvh; } } }
@media (max-width:760px){
  .contact-field input, .contact-field textarea{ font-size:16px; }
  .modal{ padding:16px; }
  .modal-panel{ padding:clamp(22px, 5vw, 32px); }
  .modal-close{ top:14px; right:14px; }
  .modal-title{ padding-right:40px; }
}
@media (prefers-reduced-motion: reduce){ .modal, .modal-panel{ transition:none; } }
""".strip()

PAGE_JS = r"""
(function () {
  'use strict';
  document.body.classList.remove('no-js');

  /* scroll reveal */
  var rv = document.querySelectorAll('.rv');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add('is-in'); obs.unobserve(entry.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    rv.forEach(function (el) { io.observe(el); });
  } else {
    rv.forEach(function (el) { el.classList.add('is-in'); });
  }

  /* contact modal */
  var lastFocused = null;
  function openModal(modal) {
    lastFocused = document.activeElement;
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    var firstField = modal.querySelector('input:not([type="hidden"]):not([name="_honey"]), textarea');
    if (firstField) firstField.focus();
  }
  function closeModal(modal) {
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    if (lastFocused && lastFocused.focus) lastFocused.focus();
  }
  document.querySelectorAll('[data-modal-open]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var modal = document.getElementById(btn.getAttribute('data-modal-open'));
      if (modal) openModal(modal);
    });
  });
  document.querySelectorAll('.modal').forEach(function (modal) {
    modal.querySelectorAll('[data-modal-close]').forEach(function (el) {
      el.addEventListener('click', function () { closeModal(modal); });
    });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var open = document.querySelector('.modal.is-open');
    if (open) closeModal(open);
  });

  /* contact form (FormSubmit) */
  var form = document.getElementById('contactForm');
  if (!form) return;
  var status = document.getElementById('cfStatus');
  var button = form.querySelector('button[type="submit"]');
  var label = button.innerHTML;
  function setStatus(msg, kind) {
    status.textContent = msg;
    status.classList.remove('is-ok', 'is-err');
    if (kind) status.classList.add(kind === 'ok' ? 'is-ok' : 'is-err');
  }
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (form.querySelector('[name="_honey"]').value) return;
    button.disabled = true;
    button.innerHTML = '<span>Sending…</span>';
    setStatus('', null);
    fetch(form.action, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(Object.fromEntries(new FormData(form)))
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.success === true || data.success === 'true') {
          setStatus('Thanks — your message is on its way. We’ll be in touch shortly.', 'ok');
          form.reset();
        } else {
          setStatus(data.message || 'Something went wrong. Please try again or email us directly.', 'err');
        }
      })
      .catch(function () {
        setStatus('Network error — please try again or email hello@aalvinai.in directly.', 'err');
      })
      .finally(function () {
        button.disabled = false;
        button.innerHTML = label;
      });
  });
})();
""".strip()

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>@@TITLE@@</title>
<meta name="description" content="@@META@@">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<link rel="canonical" href="@@URL@@">
<meta name="author" content="AALVINAI Technologies">
<meta name="theme-color" content="#050505">
<meta name="geo.region" content="IN-TN">
<meta name="geo.placename" content="Tamil Nadu, India">
<link rel="icon" href="../../favicon.ico" sizes="48x48">
<link rel="icon" type="image/svg+xml" href="../../logo-mark.svg">
<link rel="apple-touch-icon" href="../../logo-mark-512.png">

<meta property="og:type" content="website">
<meta property="og:site_name" content="AALVINAI Technologies">
<meta property="og:locale" content="en_IN">
<meta property="og:url" content="@@URL@@">
<meta property="og:title" content="@@TITLE@@">
<meta property="og:description" content="@@META@@">
<meta property="og:image" content="https://aalvinai.in/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="AALVINAI Technologies — @@NAME_ATTR@@">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="@@TITLE@@">
<meta name="twitter:description" content="@@META@@">
<meta name="twitter:image" content="https://aalvinai.in/og-image.png">

<script type="application/ld+json">
@@JSONLD@@
</script>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<style>
@@CSS@@
</style>
</head>
<body class="no-js">

<a class="visually-hidden" href="#main">Skip to content</a>

<header class="header">
  <div class="wrap header-in">
    <a class="brand" href="../../" aria-label="AALVINAI Technologies — home">
      <img src="../../logo-mark.svg" width="27" height="27" alt="" aria-hidden="true">
      <span><strong>AALVINAI</strong><i>TECHNOLOGIES</i></span>
    </a>
    <nav class="hnav" aria-label="Primary">
      <a href="../../">Home</a>
      <a href="../../#about">About</a>
      <a href="../../#solutions">Solutions</a>
      <a href="../../products.html" aria-current="true">Products</a>
      <a href="../../#industries">Industries</a>
      <button type="button" data-modal-open="contactModal">Contact</button>
    </nav>
    <button type="button" class="pill" data-modal-open="contactModal"><span>Get Started</span></button>
  </div>
</header>

<main id="main">

<section class="pd-hero">
  <div class="wrap">
    <nav class="crumb" aria-label="Breadcrumb">
      <ol>
        <li><a href="../../">Home</a></li>
        <li><a href="../../products.html">Products</a></li>
        <li><span aria-current="page">@@NAME@@</span></li>
      </ol>
    </nav>
    <div class="pd-hero-in">
      <div>
        <p class="eyebrow rv">@@CAT_TITLE@@</p>
        <h1 class="pd-h1 rv" style="--d:.05s"><span class="pd-name">@@NAME@@</span><span class="pd-kw"><span class="visually-hidden"> — </span>@@KW@@</span></h1>
        <p class="pd-lead rv" style="--d:.1s">@@DESC@@</p>
        <div class="pd-actions rv" style="--d:.15s">
          <button type="button" class="pill" data-modal-open="contactModal">Request a walkthrough <i aria-hidden="true">&#8594;</i></button>
          <a class="pill pill-ghost" href="../../products.html#@@CAT_SLUG@@">More in @@CAT_SHORT@@</a>
        </div>
      </div>
      <aside class="pd-card rv" style="--d:.2s" aria-label="@@NAME_ATTR@@ at a glance">
        <span class="marks" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <div class="pd-card-head">
          <span class="pd-card-icon" aria-hidden="true">@@ICON@@</span>
          <span class="pd-card-num">No. @@NUM@@ of @@TOTAL@@</span>
        </div>
        <dl class="pd-facts">
          <div><dt>Category</dt><dd>@@CAT_TITLE@@</dd></div>
          <div><dt>Built for</dt><dd>@@AUDIENCE@@</dd></div>
          <div><dt>Deployment</dt><dd>@@DEPLOY@@</dd></div>
          <div><dt>Support</dt><dd>In-house team, Tamil Nadu</dd></div>
        </dl>
      </aside>
    </div>
  </div>
</section>

<section class="pd-sec" aria-labelledby="overview-h">
  <div class="wrap pd-split">
    <div>
      <p class="eyebrow rv">Overview</p>
      <h2 class="pd-h2 rv" style="--d:.05s" id="overview-h">What @@NAME@@ does</h2>
    </div>
    <div class="pd-prose rv" style="--d:.1s">
@@OVERVIEW@@
    </div>
  </div>
</section>

<section class="pd-sec" aria-labelledby="features-h">
  <div class="wrap">
    <p class="eyebrow rv">Capabilities</p>
    <h2 class="pd-h2 rv" style="--d:.05s" id="features-h">Inside @@NAME@@</h2>
    <ul class="pd-features rv" style="--d:.1s">
@@FEATURES@@
    </ul>
  </div>
</section>

<section class="pd-sec" aria-labelledby="why-h">
  <div class="wrap">
    <p class="eyebrow rv">Why AALVINAI</p>
    <h2 class="pd-h2 rv" style="--d:.05s" id="why-h">Engineered, deployed and supported in-house</h2>
    <div class="pd-why rv" style="--d:.1s">
      <div><span class="pd-why-num">01</span><h3>Built in-house</h3><p>Designed, engineered, deployed and supported by AALVINAI’s own team in Tamil Nadu, India.</p></div>
      <div><span class="pd-why-num">02</span><h3>One shared architecture</h3><p>Run @@NAME@@ on its own or alongside other AALVINAI products, with one shared security posture.</p></div>
      <div><span class="pd-why-num">03</span><h3>Web and mobile</h3><p>Delivered for web and mobile, with the deployment matched to how your team works.</p></div>
      <div><span class="pd-why-num">04</span><h3>Shaped to your workflow</h3><p>Configured around how your operation actually runs — and where something is missing, we engineer it.</p></div>
    </div>
  </div>
</section>

<section class="pd-sec" aria-labelledby="related-h">
  <div class="wrap">
    <p class="eyebrow rv">Related products</p>
    <h2 class="pd-h2 rv" style="--d:.05s" id="related-h">Works well with @@NAME@@</h2>
    <div class="pd-related rv" style="--d:.1s">
@@RELATED@@
    </div>
  </div>
</section>

<section class="pd-sec" aria-labelledby="faq-h">
  <div class="wrap pd-split">
    <div>
      <p class="eyebrow rv">FAQ</p>
      <h2 class="pd-h2 rv" style="--d:.05s" id="faq-h">Questions about @@NAME@@</h2>
    </div>
    <div class="pd-faq rv" style="--d:.1s">
@@FAQ@@
    </div>
  </div>
</section>

<section class="cta">
  <div class="wrap">
    <p class="eyebrow rv">Next step</p>
    <h2 class="cta-h rv" style="--d:.06s">See @@NAME@@ on your own workflow.</h2>
    <p class="cta-p rv" style="--d:.12s">Book a walkthrough and we’ll map @@NAME@@ to how your team operates — or engineer what’s missing.</p>
    <div class="cta-actions rv" style="--d:.18s">
      <button type="button" class="pill" data-modal-open="contactModal">Request a walkthrough <i aria-hidden="true">&#8594;</i></button>
      <a class="pill pill-ghost" href="tel:+919492633000">+91 94926 33000</a>
    </div>
  </div>
</section>

</main>

<footer class="site-footer">
  <div class="wrap">
    <div class="footer-grid">
      <div class="footer-col footer-col-brand">
        <div class="footer-brand">
          <img src="../../logo-mark.svg" alt="" aria-hidden="true">
          <span class="footer-brand-name">AALVINAI TECHNOLOGIES</span>
        </div>
        <p class="footer-desc">Delivering intelligent AI, enterprise and financial technology solutions for forward-thinking businesses worldwide.</p>
        <div class="footer-social">
          <a href="mailto:hello@aalvinai.in" aria-label="Email">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M3.5 6.5 12 13l8.5-6.5"/></svg>
            <span>Email</span>
          </a>
          <a href="tel:+919492633000" aria-label="Phone">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 3.5h3.2l1.6 4-2 1.4a10.5 10.5 0 0 0 5.8 5.8l1.4-2 4 1.6V19a1.5 1.5 0 0 1-1.6 1.5A16.5 16.5 0 0 1 3.5 5.1A1.5 1.5 0 0 1 5 3.5Z"/></svg>
            <span>Call</span>
          </a>
        </div>
      </div>
      <div class="footer-col">
        <p class="footer-col-h">Quick Links</p>
        <a href="../../#about">About</a>
        <a href="../../#solutions">Solutions</a>
        <a href="../../products.html">All products</a>
        <a href="../../#industries">Industries</a>
        <button type="button" data-modal-open="contactModal">Contact</button>
      </div>
      <div class="footer-col">
        <p class="footer-col-h">@@CAT_SHORT@@</p>
@@FOOTER_CAT@@
      </div>
      <div class="footer-col">
        <p class="footer-col-h">Contact</p>
        <a href="mailto:hello@aalvinai.in">hello@aalvinai.in</a>
        <a href="mailto:careers@aalvinai.in">careers@aalvinai.in</a>
        <a href="tel:+919492633000">+91 94926 33000</a>
        <span>Tamil Nadu, India</span>
      </div>
    </div>
  </div>
  <div class="footer-bottom wrap">
    <p>&copy; AALVINAI Technologies. All rights reserved.</p>
    <nav class="footer-legal" aria-label="Legal">
      <a href="../../privacy.html">Privacy Policy</a>
      <a href="../../terms.html">Terms of Service</a>
    </nav>
  </div>
</footer>

<div class="modal" id="contactModal" aria-hidden="true">
  <div class="modal-backdrop" data-modal-close></div>
  <div class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="contactModalTitle">
    <button type="button" class="modal-close" data-modal-close aria-label="Close">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M5 5L19 19M19 5L5 19"/></svg>
    </button>
    <p class="eyebrow">Walkthrough</p>
    <h2 id="contactModalTitle" class="modal-title">See @@NAME@@ in action</h2>
    <p class="modal-sub">Tell us a little about your team and we’ll set up a walkthrough of @@NAME@@.</p>
    <div class="modal-body">
      <form class="contact-form" id="contactForm" action="https://formsubmit.co/ajax/msarunsanjeev@gmail.com" method="POST">
        <input type="hidden" name="_subject" value="Walkthrough request: @@NAME_ATTR@@ — AALVINAI website">
        <input type="hidden" name="_cc" value="sahithyamani074@gmail.com">
        <input type="hidden" name="_template" value="table">
        <input type="hidden" name="product" value="@@NAME_ATTR@@">
        <input type="text" name="_honey" style="display:none" tabindex="-1" autocomplete="off" aria-hidden="true">
        <div class="contact-field">
          <label for="cf-name">Name</label>
          <input id="cf-name" name="name" type="text" placeholder="Your full name" autocomplete="name" required>
        </div>
        <div class="contact-field">
          <label for="cf-email">Email</label>
          <input id="cf-email" name="email" type="email" placeholder="your@email.com" autocomplete="email" required>
        </div>
        <div class="contact-field">
          <label for="cf-message">Message</label>
          <textarea id="cf-message" name="message" rows="5" placeholder="Tell us about your team and what you need from @@NAME_ATTR@@…" required></textarea>
        </div>
        <button type="submit" class="pill"><span>Send Message &nbsp;→</span></button>
        <p class="form-status" id="cfStatus" role="status" aria-live="polite"></p>
      </form>
      <div class="contact-info">
        <div class="info-row">
          <span class="info-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M3.5 6.5L12 13L20.5 6.5"/></svg></span>
          <div><span class="info-label">Email</span><p class="info-value"><a href="mailto:hello@aalvinai.in">hello@aalvinai.in</a></p></div>
        </div>
        <div class="info-row">
          <span class="info-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.5 10.5C7.8 13.2 9.8 15.2 12.5 16.5L14.5 14.5C14.8 14.2 15.2 14.1 15.6 14.2C16.8 14.6 18.1 14.8 19.5 14.8C20.1 14.8 20.5 15.2 20.5 15.8V19.5C20.5 20.1 20.1 20.5 19.5 20.5C10.9 20.5 3.5 13.1 3.5 4.5C3.5 3.9 3.9 3.5 4.5 3.5H8.2C8.8 3.5 9.2 3.9 9.2 4.5C9.2 5.9 9.4 7.2 9.8 8.4C9.9 8.8 9.8 9.2 9.5 9.5L7.5 11.5"/></svg></span>
          <div><span class="info-label">Phone</span><p class="info-value"><a href="tel:+919492633000">+91 94926 33000</a></p></div>
        </div>
        <div class="info-row">
          <span class="info-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21.5C12 21.5 19 15.3 19 9.8C19 5.9 15.9 2.5 12 2.5C8.1 2.5 5 5.9 5 9.8C5 15.3 12 21.5 12 21.5Z"/><circle cx="12" cy="9.8" r="2.8"/></svg></span>
          <div><span class="info-label">Location</span><p class="info-value">Tamil Nadu, India</p></div>
        </div>
        <div class="info-row">
          <span class="info-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7V12L15.5 14.5"/></svg></span>
          <div><span class="info-label">Support</span><p class="info-value">24/7 service available</p></div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
@@JS@@
</script>
</body>
</html>
"""


def faq_items(p):
    name = p["name"]
    rel = [PROD_BY_SLUG[s] for s in p["related"]]
    listed = [lower_first(f) for f in p["features"]]
    feats = join_list(listed) if len(listed) <= 8 else ", ".join(listed[:7]) + " and more"
    mobile = p.get("mobile") or (
        "AALVINAI builds its products for web and mobile. Tell us how your team works and we’ll recommend the right setup for %s." % name)
    # (question, plain-text answer, html answer)
    return [
        ("What is %s?" % name,
         "%s is %s from AALVINAI Technologies, a software company based in Tamil Nadu, India. It covers %s." % (name, p["is_a"], feats),
         None),
        ("Can %s be customised to our workflow?" % name,
         "Yes. AALVINAI builds, deploys and supports %s in-house, so it can be configured around how your team actually works — and if something you need is missing, we can engineer it." % name,
         None),
        ("Does %s work with other AALVINAI products?" % name,
         "Yes. Every AALVINAI product shares one architecture, so %s can run on its own or alongside modules such as %s." % (name, join_list(r["name"] for r in rel)),
         "Yes. Every AALVINAI product shares one architecture, so %s can run on its own or alongside modules such as %s." % (
             esc(name), join_list('<a href="../%s/">%s</a>' % (r["slug"], esc(r["name"])) for r in rel))),
        ("Is %s available on mobile?" % name, mobile, None),
        ("How can I see a demo of %s?" % name,
         "Request a walkthrough from this page, email hello@aalvinai.in or call +91 94926 33000, and we’ll take you through %s for your use case." % name,
         'Request a walkthrough from this page, email <a href="mailto:hello@aalvinai.in">hello@aalvinai.in</a> or call <a href="tel:+919492633000">+91 94926 33000</a>, and we’ll take you through %s for your use case.' % esc(name)),
    ]


def page_jsonld(num, p, meta):
    url = product_url(p)
    cat = CAT_BY_SLUG[p["cat"]]
    graph = [
        {
            "@type": "WebPage",
            "@id": url + "#webpage",
            "url": url,
            "name": p["title"],
            "description": meta,
            "inLanguage": "en-IN",
            "isPartOf": {"@type": "WebSite", "@id": SITE + "/#website", "url": SITE + "/", "name": "AALVINAI Technologies"},
            "about": {"@id": url + "#software"},
            "breadcrumb": {"@id": url + "#breadcrumb"},
            "primaryImageOfPage": {"@type": "ImageObject", "url": SITE + "/og-image.png", "width": 1200, "height": 630},
        },
        {
            "@type": "SoftwareApplication",
            "@id": url + "#software",
            "name": p["name"],
            "alternateName": p["kw"],
            "description": p["desc"],
            "url": url,
            "applicationCategory": "BusinessApplication",
            "applicationSubCategory": p["kicker"],
            "operatingSystem": "Web, Mobile",
            "featureList": p["features"],
            "audience": {"@type": "BusinessAudience", "audienceType": p["audience"]},
            "publisher": {"@id": SITE + "/#organization"},
            "provider": {"@id": SITE + "/#organization"},
            "isPartOf": {"@id": SITE + "/products.html#catalogue"},
        },
        ORG,
        {
            "@type": "BreadcrumbList",
            "@id": url + "#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": "Products", "item": SITE + "/products.html"},
                {"@type": "ListItem", "position": 3, "name": p["name"], "item": url},
            ],
        },
        {
            "@type": "FAQPage",
            "@id": url + "#faq",
            "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a, _ in faq_items(p)
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=2, ensure_ascii=False)


def build_page(num, p, total):
    cat = CAT_BY_SLUG[p["cat"]]
    meta = meta_description(p)
    siblings = [q for q in PRODUCTS if q["cat"] == p["cat"]]
    others = [q for q in siblings if q is not p]

    # overview + a line placing the product among its siblings (internal links)
    paras = ['      <p>%s</p>' % esc(t) for t in p["overview"]]
    if others:
        links = join_list('<a href="../%s/">%s</a>' % (q["slug"], esc(q["name"])) for q in others)
        paras.append('      <p>%s is one of %s products in AALVINAI’s %s line-up, alongside %s — and like every AALVINAI product it can run on its own or with the rest of the stack.</p>'
                     % (esc(p["name"]), number_words(len(siblings)), esc(cat[1]), links))
    else:
        paras.append('      <p>%s leads AALVINAI’s %s line-up, and like every AALVINAI product it can run on its own or alongside the rest of the stack.</p>'
                     % (esc(p["name"]), esc(cat[1])))

    features = "\n".join('      <li>%s<span>%s</span></li>' % (CHECK_SVG, esc(f)) for f in p["features"])

    related = []
    for s in p["related"]:
        r = PROD_BY_SLUG[s]
        related.append(
            '      <a class="pd-rel" href="../%s/">\n'
            '        <span class="pd-rel-icon" aria-hidden="true">%s</span>\n'
            '        <span class="pd-rel-name">%s</span>\n'
            '        <span class="pd-rel-kicker">%s</span>\n'
            '        <span class="pd-rel-desc">%s</span>\n'
            '        <span class="pd-rel-go">Explore %s<i aria-hidden="true">&#8594;</i></span>\n'
            '      </a>' % (r["slug"], icon_svg(r["icon"]), esc(r["name"]), esc(r["kicker"]), esc(r["desc"]), esc(r["name"])))

    faq = []
    for i, (q, a_text, a_html) in enumerate(faq_items(p)):
        faq.append('      <details%s>\n        <summary>%s</summary>\n        <p>%s</p>\n      </details>'
                   % (" open" if i == 0 else "", esc(q), a_html if a_html else esc(a_text)))

    footer_cat = []
    for q in siblings:
        cur = ' aria-current="page"' if q is p else ""
        footer_cat.append('        <a href="../%s/"%s>%s</a>' % (q["slug"], cur, esc(q["name"])))
    footer_cat.append('        <a href="../../products.html#%s">View all in %s</a>' % (cat[0], esc(cat[3])))

    return render(
        PAGE_TEMPLATE,
        TITLE=esc(p["title"]),
        META=attr(meta),
        URL=product_url(p),
        NAME=esc(p["name"]),
        NAME_ATTR=attr(p["name"]),
        JSONLD=page_jsonld(num, p, meta),
        CSS=PAGE_CSS,
        JS=PAGE_JS,
        CAT_SLUG=cat[0],
        CAT_TITLE=esc(cat[1]),
        CAT_SHORT=esc(cat[3]),
        KW=esc(p["kw"]),
        DESC=esc(p["desc"]),
        ICON=icon_svg(p["icon"]),
        NUM="%02d" % num,
        TOTAL="%02d" % total,
        AUDIENCE=esc(p["audience"]),
        DEPLOY=esc(p.get("deploy", "Web · Mobile")),
        OVERVIEW="\n".join(paras),
        FEATURES=features,
        RELATED="\n".join(related),
        FAQ="\n".join(faq),
        FOOTER_CAT="\n".join(footer_cat),
    )


REDIRECT_STUB = """<!DOCTYPE html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<title>Products — AALVINAI Technologies</title>
<link rel="canonical" href="https://aalvinai.in/products.html">
<meta http-equiv="refresh" content="0; url=../products.html">
</head>
<body>
<p><a href="../products.html">AALVINAI Technologies — all products</a></p>
</body>
</html>
"""


# ──────────────────────────────────────────────────────────────────────────────
# SITEMAP, LLMS.TXT
# ──────────────────────────────────────────────────────────────────────────────

def git(*args):
    try:
        return subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True, text=True, check=False).stdout
    except OSError:
        return ""


def lastmod(rel_path):
    """Today if the file has uncommitted changes, else the date of its last commit."""
    if git("status", "--porcelain", "--", rel_path).strip():
        return TODAY
    return git("log", "-1", "--format=%cs", "--", rel_path).strip() or TODAY


def sitemap_entries(items):
    entries = [("/", "index.html"), ("/products.html", "products.html")]
    entries += [("/products/%s/" % p["slug"], "products/%s/index.html" % p["slug"]) for _, p in items]
    entries += [("/privacy.html", "privacy.html"), ("/terms.html", "terms.html")]
    return entries


def build_sitemap(items):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, path in sitemap_entries(items):
        lines += ["  <url>",
                  "    <loc>%s%s</loc>" % (SITE, loc),
                  "    <lastmod>%s</lastmod>" % lastmod(path),
                  "  </url>"]
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def build_llms(items):
    out = [
        "# AALVINAI Technologies",
        "",
        "> AALVINAI Technologies is a software company based in Tamil Nadu, India. It builds, deploys and supports "
        "%d business software products in-house — ERP for colleges and schools, finance and lending, billing, POS, "
        "pharmacy, inventory, procurement, construction, transport, CRM, HR, documents, helpdesk, BI, healthcare, "
        "events and e-commerce — and takes on custom web, mobile and AI development." % len(items),
        "",
        "Every product shares one architecture and can run on its own or alongside the others. "
        "Contact: hello@aalvinai.in · +91 94926 33000 · Tamil Nadu, India.",
        "",
        "## Products",
        "",
    ]
    for slug, title, _blurb, _short in CATEGORIES:
        out.append("### %s" % title)
        out.append("")
        for _, p in [(n, p) for n, p in items if p["cat"] == slug]:
            out.append("- [%s — %s](%s): %s" % (p["name"], p["kw"], product_url(p), p["desc"]))
        out.append("")
    out += [
        "## Company",
        "",
        "- [Home](%s/): who AALVINAI is, its solutions and the industries it serves" % SITE,
        "- [All products](%s/products.html): the full catalogue with search and category filters" % SITE,
        "- [Privacy Policy](%s/privacy.html)" % SITE,
        "- [Terms of Service](%s/terms.html)" % SITE,
        "",
    ]
    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def write_if_changed(rel, content, check, stale):
    path = os.path.join(ROOT, rel)
    current = None
    if os.path.exists(path):
        with io.open(path, encoding="utf-8") as f:
            current = f.read()
    if current == content:
        return False
    if check:
        stale.append(rel)
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return True


def submit_indexnow(items):
    urls = [SITE + loc for loc, _ in sitemap_entries(items)]
    body = json.dumps({"host": "aalvinai.in", "key": INDEXNOW_KEY,
                       "keyLocation": "%s/%s.txt" % (SITE, INDEXNOW_KEY), "urlList": urls}).encode("utf-8")
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=30) as res:
        print("IndexNow: HTTP %s for %d URLs" % (res.status, len(urls)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--check", action="store_true", help="report stale generated files and exit 1 (no writes)")
    ap.add_argument("--indexnow", action="store_true", help="submit every public URL to IndexNow (run after deploying)")
    args = ap.parse_args()

    validate()
    items = numbered()
    total = len(items)

    if args.indexnow:
        submit_indexnow(items)
        return

    stale, changed = [], []
    for num, p in items:
        rel = "products/%s/index.html" % p["slug"]
        if write_if_changed(rel, build_page(num, p, total), args.check, stale):
            changed.append(rel)
    for rel, content in (("products/index.html", REDIRECT_STUB),
                         ("llms.txt", build_llms(items)),
                         ("%s.txt" % INDEXNOW_KEY, INDEXNOW_KEY + "\n")):
        if write_if_changed(rel, content, args.check, stale):
            changed.append(rel)

    hub = read("products.html")
    if write_if_changed("products.html", build_hub(hub, items), args.check, stale):
        changed.append("products.html")

    # generated pages that no longer exist in the data
    pages_dir = os.path.join(ROOT, "products")
    known = {p["slug"] for p in PRODUCTS}
    orphans = sorted(d for d in os.listdir(pages_dir) if os.path.isdir(os.path.join(pages_dir, d)) and d not in known) \
        if os.path.isdir(pages_dir) else []

    if args.check:
        for rel in stale:
            print("stale: %s" % rel)
        for d in orphans:
            print("orphan: products/%s/ (not in PRODUCTS)" % d)
        sys.exit(1 if stale or orphans else 0)

    # sitemap last, so <lastmod> sees this run's changes in git status
    if write_if_changed("sitemap.xml", build_sitemap(items), False, stale):
        changed.append("sitemap.xml")

    print("%d products in %d categories; %d file(s) updated" % (total, len(CATEGORIES), len(changed)))
    for rel in changed:
        print("  wrote %s" % rel)
    for d in orphans:
        print("WARNING: products/%s/ is not in PRODUCTS any more — delete it if the product was retired" % d)
    for w in hub_count_warnings(read("products.html")):
        print("WARNING: products.html %s — update it by hand" % w)


if __name__ == "__main__":
    main()
