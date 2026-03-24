"""Five core Nigerian legal document templates. No external dependencies."""
from __future__ import annotations

import re

# ── Template registry ──────────────────────────────────────────────────────────

_TEMPLATES: dict[str, dict] = {}


def _register(key: str, title: str, description: str, tier_required: str, body: str) -> None:
    _TEMPLATES[key] = {
        "key": key,
        "title": title,
        "description": description,
        "tier_required": tier_required,
        "body": body,
    }


# ── 1. CAC Pre-Incorporation Checklist ────────────────────────────────────────

_register(
    key="cac_checklist",
    title="CAC Pre-Incorporation Checklist (Private Ltd)",
    description="Step-by-step readiness checklist for registering a Private Company Limited by Shares at the CAC under CAMA 2020.",
    tier_required="starter",
    body="""CAC PRE-INCORPORATION CHECKLIST
Private Company Limited by Shares — CAMA 2020
Prepared: {date_prepared}
Prepared for: {founder_names}
Proposed company name: {company_name}
Entity type: {entity_type}
Sector: {sector}
Proposed registered address: {proposed_address}
Authorised share capital: ₦{share_capital}
Lawyer/Legal ops contact: {lawyer_name}

─────────────────────────────────────────────
DISCLAIMER: This checklist is a draft operational packet, not legal advice.
A licensed Nigerian lawyer must review and approve all items before filing.
─────────────────────────────────────────────

STEP 1 — COMPANY NAME AVAILABILITY SEARCH
☐ Search proposed name on CAC portal (search.cac.gov.ng)
☐ Confirm name is not identical or confusingly similar to existing entries
☐ Confirm name does not contain restricted words (Federal, National, Government, etc.) without approval
☐ Reserve name online — CAC name reservation valid for 60 days
☐ Record reservation reference number: ___________________________

STEP 2 — FOUNDER AND SHAREHOLDER DETAILS
Minimum: 1 director and 1 shareholder under CAMA 2020 (s.27 as amended)
For each founder/director, collect:
☐ Full legal name (as on NIN or International Passport)
☐ Nationality
☐ Date of birth
☐ Residential address
☐ Occupation
☐ Government-issued ID (NIN slip, International Passport, or Driver's License)
☐ Passport photograph
☐ Email address and phone number
☐ Proposed shareholding (must total 100%): {founder_ids}

STEP 3 — SHARE STRUCTURE CONFIRMATION
☐ Confirm total authorised share capital: ₦{share_capital}
☐ Confirm number of shares and par value per share
☐ Confirm allotment to each shareholder matches agreed percentages
☐ Confirm no bearer shares (prohibited under CAMA 2020)
☐ Confirm share structure does not trigger regulatory approvals (e.g., CBN, SEC)

STEP 4 — MEMORANDUM AND ARTICLES OF ASSOCIATION (MEMART)
Under CAMA 2020, the MEMART is a single document. Draft must cover:
☐ Company objects clause (can be general commercial purposes)
☐ Liability of members (limited by shares)
☐ Share capital clause
☐ Director powers and restrictions
☐ Dividend policy
☐ Meeting and quorum requirements
☐ Transmission of shares procedure
⚠ LAWYER SIGN-OFF REQUIRED before MEMART is filed. Mark as pending.

STEP 5 — REGISTERED ADDRESS
☐ Confirm Nigerian street address (P.O. Box not accepted by CAC)
☐ Confirm address is accessible for service of legal notices
☐ Obtain utility bill or tenancy agreement as address evidence

STEP 6 — CAC PORTAL FILING (accredited agent or Registered Agent)
☐ Create or log in to CAC company registration portal (pre-rc.cac.gov.ng)
☐ Enter entity type: Company Limited by Shares (Private)
☐ Upload name reservation reference
☐ Upload MEMART (signed and stamped)
☐ Upload director/shareholder forms and IDs
☐ Pay prescribed filing fees (CAC fee schedule current as of filing date)
☐ Submit and save filing reference number: ___________________________

STEP 7 — POST-INCORPORATION STEPS (after Certificate of Incorporation received)
☐ Collect Certificate of Incorporation (CI) and Certified True Copy (CTC) of MEMART
☐ Apply for Tax Identification Number (TIN) from FIRS (firs.gov.ng) within 6 months
☐ Apply for SCUML registration if sector requires AML/CFT compliance (fintech, real estate, legal, accounting)
☐ Open corporate bank account (present CI, CTC, MEMART, Board Resolution, director IDs)
☐ Register for VAT if projected annual turnover ≥ ₦25,000,000
☐ Register for PAYE with relevant State Internal Revenue Service before first hire
☐ Register employees with NSITF (Employee Compensation Scheme) before operations begin
☐ File CAC Annual Return: first return due 18 months after incorporation, then annually

OUTSTANDING ISSUES FOR LAWYER REVIEW
1. ___________________________________________
2. ___________________________________________
3. ___________________________________________

Prepared by AI Legal Ops System — LexPilot NG
Review and approval by: {lawyer_name}
Date of lawyer review: ___________________________
""",
)


# ── 2. Employment Contract ────────────────────────────────────────────────────

_register(
    key="employment_contract",
    title="Nigerian Employment Contract (Standard)",
    description="Labour Act-compliant employment contract for use by Nigerian SMEs. Covers compensation, duties, termination, and PENCOM/NSITF obligations.",
    tier_required="growth",
    body="""EMPLOYMENT CONTRACT
Federal Republic of Nigeria
Date: {date_prepared}

PARTIES
Employer: {employer_name} ("the Employer")
Employee: {employee_name} ("the Employee")

─────────────────────────────────────────────
DISCLAIMER: This is a draft employment contract prepared by an AI legal operations
system. It must be reviewed and approved by a licensed Nigerian lawyer before use.
─────────────────────────────────────────────

1. APPOINTMENT
The Employer appoints the Employee as {job_title}, effective {start_date}. The Employee
accepts this appointment on the terms set out in this Contract.

2. DUTIES AND REPORTING
2.1 The Employee shall perform the duties associated with the role of {job_title} and
such other duties as the Employer may reasonably assign from time to time.
2.2 The Employee shall devote their full working time and attention to the Employer's
business during working hours and shall not, without prior written consent, engage in
any other employment or business activity that conflicts with their duties.

3. COMPENSATION
3.1 Gross monthly salary: ₦{gross_salary_ngn} payable {pay_frequency}.
3.2 The Employer shall deduct and remit applicable PAYE tax under the Personal Income
Tax Act (Cap P8 LFN 2004, as amended) and shall provide the Employee with a monthly
payslip showing deductions.
3.3 Salary shall be reviewed annually at the Employer's discretion, having regard to
performance and business conditions.

4. STATUTORY CONTRIBUTIONS
4.1 PENSION: The Employer and Employee shall each contribute to a Pension Fund
Administrator (PFA) of the Employee's choice in accordance with the Pension Reform
Act 2014: Employer contribution 10%, Employee contribution 8% of monthly emoluments.
4.2 NSITF: The Employer shall register the Employee with the Nigeria Social Insurance
Trust Fund (NSITF) and remit the mandatory Employee Compensation Scheme contribution.
4.3 NHF: Where applicable, the Employer shall deduct and remit the Employee's National
Housing Fund contribution at 2.5% of basic salary.

5. WORKING HOURS
Standard working hours are Monday to Friday, {working_hours}. Overtime work authorised
by management shall be compensated in accordance with the Employee's contract rate or
applicable policy.

6. LEAVE
6.1 Annual leave: minimum 6 working days per year (Labour Act, s.18) plus public holidays.
6.2 Sick leave: up to 12 working days per year on full pay, subject to a medical certificate.
6.3 Maternity leave: 12 weeks for female employees as required under the Labour Act.

7. CONFIDENTIALITY
The Employee shall not, during or after employment, disclose confidential information of
the Employer (including business plans, client data, financial information, trade secrets)
except as required by law or with the Employer's prior written consent.

8. INTELLECTUAL PROPERTY
All work product, inventions, software, and creative works produced by the Employee in
the course of employment shall be the property of the Employer. The Employee assigns all
rights in such works to the Employer with effect from the date of creation.

9. TERMINATION
9.1 Either party may terminate this Contract by giving {notice_period_days} days written
notice to the other party, or payment in lieu of notice.
9.2 The Employer may terminate without notice for gross misconduct, including but not
limited to: fraud, theft, wilful damage to property, or serious breach of this Contract.
9.3 On termination, the Employee shall return all Employer property and data, and final
salary (pro-rated) shall be paid within 30 days of the last working day.
9.4 Redundancy: where termination is by reason of redundancy, the Employer shall comply
with applicable provisions of the Labour Act regarding notice and severance.

10. DISPUTE RESOLUTION
10.1 Any dispute arising under this Contract shall first be subject to good-faith
negotiation between the parties for 30 days.
10.2 If unresolved, disputes shall be referred to the National Industrial Court of Nigeria
or such State Labour Court as has jurisdiction, in accordance with the Labour Act and the
Trade Disputes Act.

11. GOVERNING LAW
This Contract is governed by the laws of the Federal Republic of Nigeria and the {governing_state}
State, and the parties submit to the exclusive jurisdiction of the Nigerian courts.

12. ENTIRE AGREEMENT
This Contract constitutes the entire agreement between the parties regarding employment
and supersedes all prior representations or agreements.

SIGNATURES
Employer: ___________________________ Date: ___________
Name: {employer_name}

Employee: ___________________________ Date: ___________
Name: {employee_name}

Witness: ___________________________ Date: ___________

─────────────────────────────────────────────
Drafted by AI Legal Ops System — LexPilot NG
Reviewed by: {lawyer_name}
Date of lawyer review: ___________________________
─────────────────────────────────────────────
""",
)


# ── 3. Service / Consultancy Agreement ───────────────────────────────────────

_register(
    key="service_agreement",
    title="Service / Consultancy Agreement",
    description="Nigerian-law governed service agreement covering scope, fees, IP, confidentiality, and dispute resolution by arbitration.",
    tier_required="growth",
    body="""SERVICE AGREEMENT
Federal Republic of Nigeria
Date: {date_prepared}

PARTIES
Client:     {client_name} ("the Client")
Consultant: {consultant_name} ("the Consultant")

─────────────────────────────────────────────
DISCLAIMER: Draft document prepared by an AI legal operations system.
Must be reviewed by a licensed Nigerian lawyer before execution.
─────────────────────────────────────────────

RECITALS
The Client wishes to engage the Consultant to provide certain services, and the Consultant
agrees to provide those services, on the terms set out in this Agreement.

1. SCOPE OF SERVICES
1.1 The Consultant shall provide the following services ("Services"):
{service_description}

1.2 The Consultant shall perform the Services with reasonable skill and care, and in
accordance with any specifications or deliverables agreed in writing.
1.3 The Consultant is an independent contractor. Nothing in this Agreement creates an
employment, partnership, or agency relationship between the parties.

2. TERM
This Agreement commences on {start_date} and, unless terminated earlier, continues until
{end_date}. Extensions require written agreement of both parties.

3. FEES AND PAYMENT
3.1 The Client shall pay the Consultant ₦{fee_ngn} for the Services as follows:
{payment_terms}
3.2 Invoices are payable within 14 days of receipt unless otherwise agreed in writing.
3.3 Late payment: overdue amounts accrue interest at 5% per annum above the CBN base
lending rate from the due date until actual payment.
3.4 VAT: where applicable, VAT at 7.5% shall be added to all invoices.
3.5 WHT: where withholding tax is applicable on consultancy fees (currently 5%), the Client
shall deduct WHT and remit to FIRS, providing the Consultant with WHT credit notes.

4. INTELLECTUAL PROPERTY
{ip_clause}
[OPTION A — Assign to Client]: All work product, reports, software, designs, and other
deliverables created under this Agreement ("Work Product") shall be the exclusive property
of the Client. The Consultant hereby assigns all intellectual property rights in the Work
Product to the Client with full title guarantee.
[OPTION B — License to Client]: The Consultant retains ownership of all pre-existing IP
("Background IP"). The Consultant grants the Client a perpetual, non-exclusive licence to
use any Background IP incorporated into the deliverables for the Client's internal purposes.

5. CONFIDENTIALITY
5.1 Each party shall keep confidential all Confidential Information received from the other
party and shall not disclose it to any third party without prior written consent.
5.2 "Confidential Information" means all non-public business, financial, technical, or
operational information disclosed in connection with this Agreement.
5.3 These obligations do not apply to information that is or becomes publicly known through
no breach of this Agreement, or is required to be disclosed by law or court order.

6. WARRANTIES
6.1 Each party warrants that it has full authority to enter into this Agreement.
6.2 The Consultant warrants that the Services will be performed with reasonable skill and
care and that the deliverables will not infringe the intellectual property rights of any
third party.

7. LIMITATION OF LIABILITY
7.1 Neither party shall be liable for indirect, consequential, or special losses.
7.2 The total aggregate liability of the Consultant under this Agreement shall not exceed
the total fees paid in the 3 months preceding the claim.

8. TERMINATION
8.1 Either party may terminate this Agreement on 14 days' written notice to the other.
8.2 Either party may terminate immediately if the other commits a material breach and
fails to remedy it within 14 days of written notice.
8.3 On termination, the Client shall pay for all Services performed up to the termination
date, and the Consultant shall deliver all work in progress.

9. DISPUTE RESOLUTION
9.1 Any dispute shall first be subject to good-faith negotiation for 21 days.
9.2 If unresolved, disputes shall be referred to arbitration under the Arbitration and
Conciliation Act (Cap A18 LFN 2004, as amended) with a sole arbitrator appointed by
agreement or, failing agreement, by the Chairman of the {governing_state} State branch
of the Chartered Institute of Arbitrators Nigeria.
9.3 The seat of arbitration shall be {governing_state}, Nigeria.

10. GOVERNING LAW
This Agreement is governed by the laws of the Federal Republic of Nigeria.

SIGNATURES
Client: ___________________________ Date: ___________
Name: {client_name}

Consultant: ___________________________ Date: ___________
Name: {consultant_name}

─────────────────────────────────────────────
Drafted by AI Legal Ops System — LexPilot NG
Reviewed by: {lawyer_name}
Date of lawyer review: ___________________________
─────────────────────────────────────────────
""",
)


# ── 4. Non-Disclosure Agreement ───────────────────────────────────────────────

_register(
    key="nda",
    title="Non-Disclosure Agreement (Mutual)",
    description="Mutual NDA governed by Nigerian law. Covers definition of confidential information, obligations, exclusions, and remedies.",
    tier_required="growth",
    body="""NON-DISCLOSURE AGREEMENT (MUTUAL)
Federal Republic of Nigeria
Date: {date_prepared}

PARTIES
Disclosing Party: {disclosing_party} ("Party A")
Receiving Party:  {receiving_party} ("Party B")

Collectively referred to as "the Parties."

─────────────────────────────────────────────
DISCLAIMER: Draft NDA prepared by an AI legal operations system.
Must be reviewed by a licensed Nigerian lawyer before execution.
─────────────────────────────────────────────

BACKGROUND
The Parties wish to explore a potential business relationship or transaction described as:
{purpose}
In connection with this, each Party may disclose or receive Confidential Information
belonging to the other. This Agreement sets out the terms on which Confidential
Information shall be protected.

1. DEFINITION OF CONFIDENTIAL INFORMATION
1.1 "Confidential Information" means any non-public information disclosed by one Party
("Disclosing Party") to the other ("Receiving Party"), whether orally, in writing, or
by any other means, that is designated as confidential or that reasonably should be
understood to be confidential given the nature of the information and the circumstances
of disclosure. This includes, without limitation: business plans, financial data, customer
lists, technical specifications, pricing, trade secrets, software, and know-how.
1.2 Confidential Information does not include information that:
(a) is or becomes generally available to the public through no act or omission of the
Receiving Party;
(b) was rightfully in the Receiving Party's possession before disclosure by the Disclosing
Party, free of any obligation of confidence;
(c) is rightfully received by the Receiving Party from a third party without restriction
on disclosure; or
(d) is independently developed by the Receiving Party without reference to the Disclosing
Party's Confidential Information.

2. OBLIGATIONS OF RECEIVING PARTY
2.1 The Receiving Party shall:
(a) keep the Confidential Information strictly confidential;
(b) not disclose it to any third party without the Disclosing Party's prior written consent;
(c) use it solely for the purpose described in the Background above;
(d) protect it using at least the same degree of care it uses for its own confidential
information, and in any case no less than reasonable care.
2.2 Disclosure to employees or advisers is permitted only on a need-to-know basis and
subject to obligations of confidence at least as protective as this Agreement.

3. COMPELLED DISCLOSURE
If the Receiving Party is required by law, regulation, or court order to disclose any
Confidential Information, it shall: (i) notify the Disclosing Party promptly; (ii)
cooperate with the Disclosing Party in seeking a protective order; and (iii) disclose only
the minimum information required to comply.

4. TERM
This Agreement is effective from the date above and the confidentiality obligations
continue for {duration_years} years from the date of last disclosure of Confidential
Information.

5. RETURN OF INFORMATION
On request or on termination of discussions, the Receiving Party shall promptly return or
destroy all Confidential Information (including copies) and certify such destruction in
writing, except where retention is required by applicable law.

6. NO LICENCE OR RIGHTS GRANTED
Nothing in this Agreement grants any licence, right, or interest in any Confidential
Information, intellectual property, or other asset of the Disclosing Party.

7. REMEDIES
The Parties acknowledge that breach of this Agreement may cause irreparable harm for
which monetary damages would be inadequate, and that the Disclosing Party shall be
entitled to seek injunctive or other equitable relief in addition to any other remedies
available at law or in equity under Nigerian courts.

8. GOVERNING LAW AND JURISDICTION
This Agreement is governed by the laws of the Federal Republic of Nigeria. The Parties
submit to the exclusive jurisdiction of the courts of {governing_state} State, Nigeria
for all disputes arising under this Agreement.

9. ENTIRE AGREEMENT
This Agreement constitutes the entire agreement between the Parties regarding
confidentiality of the subject matter hereof and supersedes all prior agreements.

SIGNATURES
Party A: ___________________________ Date: ___________
Name: {disclosing_party}

Party B: ___________________________ Date: ___________
Name: {receiving_party}

─────────────────────────────────────────────
Drafted by AI Legal Ops System — LexPilot NG
Reviewed by: {lawyer_name}
Date of lawyer review: ___________________________
─────────────────────────────────────────────
""",
)


# ── 5. Shareholders Agreement ─────────────────────────────────────────────────

_register(
    key="shareholders_agreement",
    title="Shareholders Agreement (2–5 Founders)",
    description="Basic SHA for Nigerian private limited companies with 2–5 founders. Covers share structure, board, pre-emption, tag/drag, and deadlock.",
    tier_required="scale",
    body="""SHAREHOLDERS AGREEMENT
{company_name}
(A Private Company Limited by Shares incorporated under CAMA 2020)
Date: {date_prepared}

PARTIES
{shareholder_names}

─────────────────────────────────────────────
DISCLAIMER: Draft Shareholders Agreement prepared by an AI legal operations system.
A licensed Nigerian corporate lawyer MUST review this document before execution.
This draft does not constitute legal advice.
─────────────────────────────────────────────

BACKGROUND
A. The Company is {company_name}, incorporated in Nigeria under CAMA 2020.
B. The Shareholders hold shares in the Company in the proportions set out below.
C. The Shareholders wish to regulate their relationship and the management of the Company
on the terms of this Agreement.

1. SHARE STRUCTURE
1.1 The current shareholding of the Company is as follows:
{shareholding_percentages}
1.2 The Shareholders acknowledge this Agreement is supplemental to, and shall be read
together with, the Company's Memorandum and Articles of Association (MEMART).
In case of conflict, this Agreement prevails as between the Shareholders.

2. BOARD COMPOSITION AND MANAGEMENT
2.1 The Board of Directors shall comprise:
{board_seats}
2.2 Each Shareholder holding 10% or more of the shares shall be entitled to nominate one
director to the Board, subject to the MEMART and applicable law.
2.3 Board decisions shall be by simple majority, except for Reserved Matters (clause 3).
2.4 Quorum for Board meetings: a majority of directors including at least one director
nominated by each Shareholder holding 20% or more of the shares.

3. RESERVED MATTERS (SUPERMAJORITY)
The following actions require approval of Shareholders holding at least 75% of the shares:
(a) amendment of the MEMART;
(b) issue of new shares or change in share capital;
(c) declaration of dividends;
(d) disposal of all or substantially all the Company's assets;
(e) entering into any transaction with a Shareholder or related party outside ordinary
    course of business;
(f) commencement, settlement, or abandonment of material litigation;
(g) change in the principal business of the Company;
(h) winding up or dissolution of the Company.

4. PRE-EMPTION RIGHTS
{pre_emption}
[Where pre_emption = yes]:
4.1 Before transferring any shares to a third party, a Shareholder ("Selling Shareholder")
must first offer those shares to the other Shareholders pro rata to their existing
shareholdings ("Pre-Emption Right"), at the same price and on the same terms as the
proposed third-party transfer.
4.2 The other Shareholders have 21 days to exercise their Pre-Emption Right. Any shares
not taken up may then be transferred to the third party on no better terms.

5. TAG-ALONG RIGHTS
{tag_along}
[Where tag_along = yes]:
5.1 If a Shareholder or group of Shareholders (holding in aggregate 50% or more) agrees
to sell shares to a third party ("Acquirer"), each other Shareholder has the right to
require the Acquirer to purchase their shares on the same terms (pro rata to their
holding) before the sale completes ("Tag-Along Right").

6. DRAG-ALONG RIGHTS
{drag_along}
[Where drag_along = yes]:
6.1 If Shareholders holding at least 75% of the shares ("Dragging Shareholders") agree
to sell all their shares to a bona fide third party, they may require the remaining
Shareholders to sell their shares on the same terms ("Drag-Along Right"), provided the
price per share is the same for all Shareholders.

7. DEADLOCK
{deadlock_mechanism}
7.1 A deadlock occurs when the Board or Shareholders cannot pass a resolution on a
Reserved Matter after two duly convened meetings.
7.2 On a deadlock, either party may serve a written notice ("Deadlock Notice").
7.3 The parties shall attempt to resolve the deadlock by senior management escalation
for 30 days.
7.4 If unresolved, a Shareholder may invoke a buy-sell (Texas Shoot-Out) mechanism:
the initiating Shareholder names a price per share; the other Shareholder must either
(a) buy the initiating Shareholder's shares at that price, or (b) sell their own shares
to the initiating Shareholder at that same price.

8. DIVIDENDS
The Board may declare dividends from distributable profits, subject to the Reserved
Matters approval threshold. Dividends shall be distributed pro rata to shareholding.

9. CONFIDENTIALITY
Each Shareholder shall keep confidential all information relating to the Company's
business and shall not disclose it to third parties except as required by law or agreed
in writing.

10. DISPUTE RESOLUTION
10.1 Disputes shall first be subject to good-faith negotiation for 30 days.
10.2 If unresolved, disputes shall be referred to arbitration under the Arbitration and
Conciliation Act (Cap A18 LFN 2004, as amended), with a sole arbitrator agreed between
the parties or, failing agreement, appointed by the Lagos Court of Arbitration.

11. GOVERNING LAW
This Agreement is governed by the laws of the Federal Republic of Nigeria.
The parties submit to the exclusive jurisdiction of the Nigerian courts.

12. DURATION
This Agreement continues in force until the Company is wound up or until all parties
agree in writing to terminate it.

SIGNATURES
{shareholder_names}

Each Shareholder: ___________________________ Date: ___________

─────────────────────────────────────────────
Drafted by AI Legal Ops System — LexPilot NG
Reviewed by: {lawyer_name}
Date of lawyer review: ___________________________
─────────────────────────────────────────────
""",
)


# ── Public API ─────────────────────────────────────────────────────────────────

def list_templates() -> list[dict]:
    """Return template metadata (no body_text) for the API."""
    return [
        {
            "key": t["key"],
            "title": t["title"],
            "description": t["description"],
            "tier_required": t["tier_required"],
            "required_variables": extract_required_variables(t["key"]),
        }
        for t in _TEMPLATES.values()
    ]


def get_template(template_key: str) -> dict:
    if template_key not in _TEMPLATES:
        raise LookupError(f"Template '{template_key}' not found.")
    return _TEMPLATES[template_key]


def extract_required_variables(template_key: str) -> list[str]:
    """Return list of placeholder variable names from the template body."""
    body = _TEMPLATES[template_key]["body"]
    return sorted(set(re.findall(r"\{(\w+)\}", body)))


def fill_template(template_key: str, variables: dict) -> str:
    """Fill a template with the provided variables. Missing vars → '[NOT PROVIDED]'."""
    tmpl = get_template(template_key)
    required = extract_required_variables(template_key)
    safe_vars = {k: (str(variables.get(k, "")) or "[NOT PROVIDED]") for k in required}
    return tmpl["body"].format(**safe_vars)
