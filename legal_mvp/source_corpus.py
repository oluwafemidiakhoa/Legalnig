"""Substantive Nigerian legal corpus — counsel-reviewed operational summaries.

Each document summarises one statute, regulation, or practice area in plain operational
language suitable for citation in AI-generated guidance. These are NOT legal opinions;
they are structured operational summaries that a lawyer should verify before delivery.
"""
from __future__ import annotations

from legal_mvp.models import SourceDocument

SEED_SOURCE_DOCUMENTS = [
    # ── Company Formation ──────────────────────────────────────────────────────
    SourceDocument(
        source_key="nigeria-cama-2020-business-names",
        title="CAMA 2020 — Business Name Registration",
        issuer="Companies and Allied Matters Act 2020 (Part B)",
        jurisdiction="Nigeria",
        area="company formation",
        citation_label="CAMA 2020, Part B — Business Name Registration",
        production_ready=True,
        body_text=(
            "Under Part B of the Companies and Allied Matters Act 2020 (CAMA 2020), any individual, "
            "firm, or partnership carrying on business in Nigeria under a name other than the true "
            "surname(s) of all individuals involved must register that business name with the Corporate "
            "Affairs Commission (CAC) within 60 days of commencing business. "
            "\n\nRegistration is done via the CAC online portal (pre-rc.cac.gov.ng). Required particulars "
            "include: (i) the proposed business name; (ii) the general nature of the business; "
            "(iii) the registered address; (iv) names, nationalities, addresses and occupations of all "
            "proprietors or partners; and (v) government-issued identification. "
            "\n\nOnce registered, the business receives a Certificate of Registration. Business names must "
            "be renewed every two years from the date of initial registration; failure to renew attracts "
            "penalties. A registered business name is not a separate legal entity — the proprietor(s) "
            "remain personally liable for all business debts and obligations. For liability protection, "
            "founders should consider incorporating a Private Limited Company instead. "
            "\n\nKey restriction: A business name cannot contain words implying government connection "
            "(Federal, National, State, Municipal) without prior ministerial approval (s.869 CAMA 2020). "
            "\n\nPost-registration obligations include: filing annual returns to the CAC confirming the "
            "continuing existence and particulars of the business. Non-compliance may result in striking "
            "off. Founders must also obtain a Tax Identification Number (TIN) from FIRS and comply with "
            "applicable tax obligations from the date of commencement of business."
        ),
    ),
    SourceDocument(
        source_key="nigeria-cama-2020-ltd-formation",
        title="CAMA 2020 — Private Company Limited by Shares",
        issuer="Companies and Allied Matters Act 2020 (Part A)",
        jurisdiction="Nigeria",
        area="company formation",
        citation_label="CAMA 2020, Part A — Private Company Formation (LTD)",
        production_ready=True,
        body_text=(
            "Under Part A of CAMA 2020, a Private Company Limited by Shares (LTD) can be incorporated "
            "by a minimum of one person acting as both sole shareholder and sole director (s.27 CAMA 2020, "
            "as amended). This removed the prior requirement for two subscribers, making single-founder "
            "incorporation possible. "
            "\n\nKey formation documents: (i) a Memorandum and Articles of Association (MEMART) — under "
            "CAMA 2020 this is a single combined document; (ii) pre-incorporation forms (CAC 1.1); "
            "(iii) government-issued ID and passport photographs for each director and shareholder; "
            "(iv) evidence of registered address (utility bill or tenancy agreement). "
            "\n\nThe MEMART must state: company name (ending 'Limited' or 'Ltd'); objects (can be "
            "general commercial purposes); share capital; subscriber details; director details. Bearer "
            "shares are prohibited. "
            "\n\nFiling fees are prescribed by CAC and are based on the authorised share capital. For a "
            "₦100,000 share capital company the fee is minimal; for larger capitals fees increase on a "
            "sliding scale. Name reservation must be obtained first (valid 60 days). "
            "\n\nUpon incorporation, the company receives a Certificate of Incorporation (CI) and a "
            "Certified True Copy (CTC) of the MEMART. Post-incorporation requirements: "
            "(i) TIN registration with FIRS within 6 months; "
            "(ii) opening a corporate bank account (requires CI, CTC, MEMART, Board Resolution, director IDs); "
            "(iii) SCUML registration for sectors requiring AML/CFT compliance; "
            "(iv) first Annual Return due 18 months after the CI date; "
            "(v) VAT registration if annual turnover will exceed ₦25,000,000; "
            "(vi) PAYE registration before first hire. "
            "\n\nA private company must restrict share transfers in its MEMART and must not invite the "
            "public to subscribe for its shares or debentures."
        ),
    ),
    SourceDocument(
        source_key="nigeria-cac-filing-readiness",
        title="CAC Filing Readiness — Operational Checklist",
        issuer="Counsel-curated operations summary",
        jurisdiction="Nigeria",
        area="company formation",
        citation_label="Counsel summary: CAC filing readiness checklist",
        production_ready=True,
        body_text=(
            "Before a matter can be moved to filing-ready status at the CAC, the following facts must be "
            "confirmed: (i) company name availability (search cac.gov.ng); (ii) entity type selected "
            "(Business Name, LTD, PLC, or Partnership); (iii) full particulars of all founders/directors "
            "including NIN or passport number; (iv) ownership percentages agreed and documented; "
            "(v) registered address confirmed with evidence; (vi) share capital structure agreed. "
            "\n\nThe most common filing errors that cause CAC rejection: name already taken or too similar "
            "to existing companies; missing signatures on MEMART; addresses inconsistent across documents; "
            "photocopied IDs instead of clear originals; share totals not adding up to 100%; incorrect "
            "filing fees. "
            "\n\nFor regulated sectors (fintech, health, education, energy), the founders must confirm "
            "whether sector-specific pre-incorporation approvals are required. For example, CBN does not "
            "require a separate letter for standard LTD formation but will require it before licensing "
            "a fintech as a Payment Service Provider. NAFDAC does not block incorporation but requires "
            "product registration before market launch. "
            "\n\nOperationally: CAC company registration currently takes 2-5 business days via the online "
            "portal when the file is complete. Paper filings at CAC offices take significantly longer. "
            "Accredited CAC filing agents can be engaged for ₦15,000–₦50,000 depending on complexity. "
            "\n\nPost-filing: the assistant should record the filing reference number, the date filed, "
            "and the expected collection date. The matter should not be closed until the CI and CTC are "
            "physically collected and stored."
        ),
    ),
    # ── Tax ───────────────────────────────────────────────────────────────────
    SourceDocument(
        source_key="nigeria-firs-company-income-tax",
        title="FIRS — Company Income Tax (CIT)",
        issuer="Companies Income Tax Act (CITA) Cap C21 LFN 2004 as amended",
        jurisdiction="Nigeria",
        area="tax",
        citation_label="CITA — Company Income Tax obligations",
        production_ready=True,
        body_text=(
            "Company Income Tax (CIT) is levied on the profits of Nigerian companies under the Companies "
            "Income Tax Act (CITA) as amended by the Finance Acts 2019, 2020, and 2021. "
            "\n\nRates (as of Finance Act 2021): "
            "• Small companies (annual gross turnover ≤ ₦25,000,000): 0% CIT rate. "
            "• Medium companies (turnover ₦25m–₦100m): 20% CIT rate. "
            "• Large companies (turnover > ₦100m): 30% CIT rate. "
            "\n\nFiling deadline: CIT returns must be filed with FIRS by June 30 of each year for the "
            "immediately preceding financial year (for companies with a December 31 financial year-end). "
            "Companies with a different financial year-end must file within 6 months of their year-end. "
            "\n\nNew companies: a company filing its first CIT return must do so within 18 months of "
            "incorporation or 6 months after the financial year-end, whichever is earlier. "
            "\n\nMinimum tax: where a company has no taxable profit, a minimum tax may apply (currently "
            "0.5% of gross turnover), subject to exceptions for new companies in their first 4 years. "
            "\n\nEDT (Tertiary Education Tax): an additional 2.5% of assessable profits is payable "
            "alongside CIT. "
            "\n\nPayment: CIT can be paid in instalments — 50% upfront with the return, balance in two "
            "equal instalments within the tax year. Late payment attracts 10% additional tax plus interest. "
            "\n\nSelf-assessment: companies are expected to self-assess their tax liability, compute the "
            "tax payable, and remit to any FIRS-designated bank. A tax clearance certificate (TCC) is "
            "required for government contracts, import/export licenses, and various regulatory approvals."
        ),
    ),
    SourceDocument(
        source_key="nigeria-firs-vat",
        title="FIRS — Value Added Tax (VAT)",
        issuer="Value Added Tax Act Cap V1 LFN 2004 as amended (Finance Act 2020)",
        jurisdiction="Nigeria",
        area="tax",
        citation_label="VAT Act (as amended) — VAT obligations for Nigerian SMEs",
        production_ready=True,
        body_text=(
            "Value Added Tax (VAT) in Nigeria is levied at 7.5% (increased from 5% by the Finance Act "
            "2019) on the supply of taxable goods and services. "
            "\n\nRegistration threshold: businesses with annual taxable turnover of ₦25,000,000 or above "
            "must register for VAT with FIRS. Registration is done on the FIRS TaxPro-Max portal "
            "(taxpromax.firs.gov.ng). Smaller businesses may register voluntarily. "
            "\n\nMontly returns: registered businesses must file a VAT return by the 21st day of the "
            "month following the reporting month and remit the net VAT collected (output VAT minus input "
            "VAT) to FIRS. Late filing attracts a ₦50,000 monthly penalty for the first month and "
            "₦25,000 per month thereafter. "
            "\n\nInput VAT recovery: businesses can recover input VAT on goods and services acquired for "
            "use in taxable activities. Input VAT on capital goods must be recovered over 2 financial years. "
            "\n\nExemptions: certain supplies are VAT-exempt including medical and pharmaceutical products, "
            "basic food items, books and educational materials, baby products, fertilisers, and services "
            "rendered by micro businesses with turnover below ₦25m. "
            "\n\nWithholding VAT: certain government agencies and companies designated by FIRS must "
            "withhold VAT from supplier payments and remit directly to FIRS. "
            "\n\nFor fintech and SaaS companies: VAT applies to digital/electronic services supplied "
            "to Nigerian customers regardless of where the supplier is based (as of Finance Act 2021). "
            "Non-resident suppliers of digital services above the ₦25m threshold must register for "
            "VAT in Nigeria through the non-resident registration process on TaxPro-Max."
        ),
    ),
    SourceDocument(
        source_key="nigeria-firs-paye-wht",
        title="FIRS — PAYE and Withholding Tax (WHT)",
        issuer="Personal Income Tax Act (PITA) Cap P8 LFN 2004 as amended",
        jurisdiction="Nigeria",
        area="tax",
        citation_label="PITA — PAYE and WHT obligations for employers",
        production_ready=True,
        body_text=(
            "Pay-As-You-Earn (PAYE) is the mechanism through which employers deduct personal income tax "
            "from employees' salaries and remit to the relevant State Internal Revenue Service (SIRS). "
            "\n\nPAYE rates (consolidated relief allowance of ₦200,000 or 1% of gross income, whichever "
            "is higher, plus 20% of gross income, is deductible before tax): "
            "• First ₦300,000: 7% "
            "• Next ₦300,000: 11% "
            "• Next ₦500,000: 15% "
            "• Next ₦500,000: 19% "
            "• Next ₦1,600,000: 21% "
            "• Above ₦3,200,000: 24% "
            "\n\nEmployer obligations: Register with the relevant SIRS before hiring. Deduct PAYE from "
            "every employee each pay period. Remit all deductions to the SIRS by the 10th day of the "
            "following month. File annual employer declaration (Form H1) by January 31 each year. Issue "
            "individual employee tax receipts (Form A) by February 28. Failure to remit PAYE makes the "
            "employer jointly liable for the tax plus a 10% penalty and interest at CBN MPR + 5%. "
            "\n\nJurisdiction: The SIRS with authority is the one where the employer's business premises "
            "are located (not where the employee lives). Lagos State IRS (LIRS), FCT IRS, and Rivers "
            "State IRS are the most common for tech/SME companies. "
            "\n\nWithholding Tax (WHT): Companies making certain payments must deduct WHT at source and "
            "remit to FIRS by the 21st of the following month. Key rates: "
            "• Dividends: 10% "
            "• Interest: 10% "
            "• Royalties: 10% "
            "• Consultancy/professional fees: 5% "
            "• Construction contracts: 5% "
            "• Director fees: 10% "
            "• Rent: 10% "
            "WHT credit notes must be issued to payees and can be used to offset CIT liability. "
            "Non-resident WHT for dividends, interest, and royalties is 10% (subject to tax treaties)."
        ),
    ),
    # ── Data Protection ────────────────────────────────────────────────────────
    SourceDocument(
        source_key="nigeria-ndpa-2023-ndpr-2019",
        title="NDPA 2023 and NDPR 2019 — Data Protection",
        issuer="Nigeria Data Protection Act 2023; NITDA NDPR 2019",
        jurisdiction="Nigeria",
        area="data protection",
        citation_label="NDPA 2023 / NDPR 2019 — Nigerian data protection obligations",
        production_ready=True,
        body_text=(
            "Nigeria's primary data protection framework is now the Nigeria Data Protection Act 2023 "
            "(NDPA 2023), which repealed and replaced most of the NITDA Data Protection Regulation 2019 "
            "(NDPR 2019). The Nigeria Data Protection Commission (NDPC) is the supervisory authority. "
            "\n\nKey obligations under NDPA 2023: "
            "\n• Lawful basis: personal data may only be processed if at least one of the following "
            "applies: (i) consent; (ii) contract performance; (iii) legal obligation; (iv) vital "
            "interests; (v) public task; (vi) legitimate interests (with data subject rights override). "
            "\n• Data subject rights: right of access, rectification, erasure, restriction of processing, "
            "data portability, and objection. Requests must be responded to within 30 days. "
            "\n• Data Protection Officer (DPO): organisations that are major data controllers "
            "(processing data of more than 10,000 data subjects or processing sensitive data) must "
            "designate a DPO and register with the NDPC. "
            "\n• DPIA: a Data Protection Impact Assessment must be conducted before high-risk processing, "
            "including large-scale processing of sensitive data or systematic public monitoring. "
            "\n• Breach notification: data breaches likely to result in risk to data subjects must be "
            "reported to the NDPC within 72 hours of becoming aware, and to affected data subjects "
            "without undue delay. "
            "\n• Cross-border transfers: personal data may only be transferred to countries with adequate "
            "protection or subject to appropriate safeguards (SCCs, BCRs, or NDPC approval). "
            "\n• Penalties: administrative fines up to 2% of annual gross revenue or ₦10,000,000 "
            "(whichever is higher) for general violations; up to 2% of global annual turnover for "
            "systematic violations. Criminal penalties may also apply. "
            "\n\nPractical impact for SMEs: any Nigerian company with a website collecting personal data "
            "(names, emails, phone numbers) must: publish a compliant privacy policy; obtain valid consent "
            "or identify a lawful basis; restrict data retention; and ensure any cloud processors are "
            "contractually bound to NDPA-equivalent standards via a Data Processing Agreement (DPA)."
        ),
    ),
    # ── Employment ────────────────────────────────────────────────────────────
    SourceDocument(
        source_key="nigeria-labour-act-employment",
        title="Labour Act — Employment Contracts and Obligations",
        issuer="Labour Act Cap L1 LFN 2004",
        jurisdiction="Nigeria",
        area="employment",
        citation_label="Labour Act Cap L1 — Nigerian employment obligations",
        production_ready=True,
        body_text=(
            "The Labour Act (Cap L1 LFN 2004) governs the employment relationship for workers in Nigeria, "
            "with the National Industrial Court (NIC) as the specialist employment court. The Act applies "
            "to employees earning less than a prescribed salary threshold; senior management employees are "
            "typically governed by their contract and general common law. "
            "\n\nKey provisions: "
            "\n• Written contract: every employment for more than 3 months must be documented in writing "
            "and provided to the employee within 3 months of commencement (s.7). The written terms must "
            "include: nature of employment, commencement date, wages and payment intervals, hours of "
            "work, leave entitlements, and termination notice period. "
            "\n• Minimum wage: the National Minimum Wage is ₦30,000 per month (as of 2024; subject to "
            "periodic review). Private employers with 25+ employees must comply. "
            "\n• Annual leave: minimum 6 working days of paid annual leave per year (s.18). In practice "
            "most employers provide 10–20 days. "
            "\n• Maternity leave: 12 weeks of paid maternity leave for female employees (s.54). An "
            "employer cannot give notice of dismissal to a female employee during maternity leave. "
            "\n• Termination notice: for monthly-paid employees, minimum 1 month's notice; for weekly- "
            "paid employees, 1 week's notice. Either party may pay salary in lieu of notice. "
            "\n• Wrongful dismissal: an employee may seek redress at the NIC for unfair dismissal. "
            "Courts look at whether the procedure was fair and whether there was a substantive reason. "
            "\n• Redundancy: where employees are made redundant, an employer should: give early notice "
            "to the union or employee representatives; use objective selection criteria; pay all accrued "
            "wages, leave pay, and any contractual redundancy payment. "
            "\n• Restrictive covenants: non-compete clauses are valid under Nigerian law but must be "
            "reasonable in duration, geographic scope, and the interests they protect. Nigerian courts "
            "will strike out unreasonable restraints as void for being in restraint of trade. "
            "\n• Pension: employers with 3+ employees must register with PENCOM and contribute to the "
            "Contributory Pension Scheme: 10% employer / 8% employee of monthly emoluments (Pension "
            "Reform Act 2014, s.4)."
        ),
    ),
    SourceDocument(
        source_key="nigeria-pencom-pension",
        title="Pension Reform Act 2014 — Pension Obligations",
        issuer="Pension Reform Act 2014 (as amended)",
        jurisdiction="Nigeria",
        area="employment",
        citation_label="Pension Reform Act 2014 — employer pension obligations",
        production_ready=True,
        body_text=(
            "The Pension Reform Act 2014 (PRA 2014) establishes the Contributory Pension Scheme (CPS) "
            "administered by the National Pension Commission (PENCOM). "
            "\n\nCoverage: all employers with 3 or more employees must register with PENCOM and enrol "
            "employees in the CPS. Employers with fewer than 3 employees may also voluntarily participate. "
            "\n\nContribution rates: the employer contributes a minimum of 10% and the employee 8% of the "
            "employee's monthly emoluments (basic salary + housing allowance + transport allowance). The "
            "employer may contribute more (15%+) as additional benefit. "
            "\n\nRemittance: contributions must be remitted to the employee's chosen Pension Fund "
            "Administrator (PFA) within 7 working days after the salary payment date for the relevant "
            "month. Late remittance attracts a penalty of 2% per month of the unremitted amount. "
            "\n\nEmployee choice: each employee has the right to choose their own PFA from those licensed "
            "by PENCOM. The employer must facilitate transfer of contributions to the chosen PFA. "
            "\n\nRetirement Savings Account (RSA): each enrolled employee has an individual RSA held with "
            "their chosen PFA. Contributions accumulate with investment returns until retirement age (50+). "
            "\n\nDefault: an employer who fails to deduct and remit employee contributions is liable to "
            "make good the contributions plus 2% per month interest and is subject to criminal prosecution "
            "with fines up to ₦250,000 or 3 years imprisonment. "
            "\n\nExemption: federal, state, and local government employees are covered by separate "
            "provisions (Defined Benefit Scheme transitional arrangements); this summary covers private "
            "sector employers only."
        ),
    ),
    # ── Fintech / Financial Regulation ───────────────────────────────────────
    SourceDocument(
        source_key="nigeria-cbn-fintech-licensing",
        title="CBN — Fintech Licensing Framework",
        issuer="Central Bank of Nigeria — Payment System Management Department",
        jurisdiction="Nigeria",
        area="regulatory",
        citation_label="CBN Licensing Framework — Nigerian fintech regulatory tiers",
        production_ready=True,
        body_text=(
            "The Central Bank of Nigeria (CBN) regulates payment services and fintech companies through "
            "the Regulatory Framework for the Licensing and Regulation of Payment Service Banks (PSB) "
            "and the Guidelines on Operations of Electronic Payment Channels in Nigeria. "
            "\n\nKey licensing categories: "
            "\n• Payment Service Bank (PSB): can accept deposits, issue debit cards, provide payment "
            "services — but CANNOT give loans. Minimum capital: ₦5 billion. "
            "\n• Mobile Money Operator (MMO): e-wallets, mobile payments. Operates via agent banking. "
            "Minimum capital: ₦2 billion. "
            "\n• Payment Solution Service Provider (PSSP): payment gateway, POS/card processing. "
            "Minimum capital: ₦100 million. "
            "\n• Switching and Processing: interbank transaction routing. Minimum capital: ₦2 billion. "
            "\n• Payment Terminal Service Provider (PTSP): POS terminal deployment and management. "
            "Minimum capital: ₦100 million. "
            "\n\nAML/CFT requirements: all CBN-licensed entities must: "
            "• Register with the Special Control Unit Against Money Laundering (SCUML). "
            "• Appoint a Money Laundering Reporting Officer (MLRO). "
            "• Implement a KYC programme (3-tier KYC: basic wallet, mid-tier, full-tier). "
            "• File Suspicious Transaction Reports (STRs) with the NFIU. "
            "\n\nFor pre-licensing startups: a fintech company does not need a CBN licence to build its "
            "product in stealth mode, but must obtain the relevant licence BEFORE going live with "
            "customer funds or live payment processing. Founders should engage CBN-experienced fintech "
            "counsel early, as licensing can take 6–18 months. "
            "\n\nSEC overlap: platforms offering investment products, tokenised assets, or securities-like "
            "instruments may also require Securities and Exchange Commission (SEC) registration under "
            "the Investments and Securities Act 2007 (under review as of 2024)."
        ),
    ),
    # ── Commercial Contracts ──────────────────────────────────────────────────
    SourceDocument(
        source_key="nigeria-contract-law-essentials",
        title="Nigerian Contract Law — Essentials and Risk Clauses",
        issuer="Counsel-curated summary based on Nigerian common law",
        jurisdiction="Nigeria",
        area="commercial agreements",
        citation_label="Counsel summary: Nigerian contract law essentials",
        production_ready=True,
        body_text=(
            "Nigerian contract law is based on English common law as received at independence, developed "
            "through Nigerian case law and statute. A valid contract requires: offer, acceptance, "
            "consideration, intention to create legal relations, and capacity of both parties. "
            "\n\nWriting requirement: most commercial contracts are enforceable whether oral or written, "
            "but certain contracts MUST be in writing: (i) contracts for the sale or disposition of land "
            "or any interest in land (Statute of Frauds; Land Use Act); (ii) contracts of guarantee; "
            "(iii) hire-purchase agreements. All business-critical contracts should be in writing for "
            "evidence purposes regardless of legal requirement. "
            "\n\nKey risk clauses to review in any Nigerian commercial agreement: "
            "\n1. Governing law: should be Nigerian law for enforcement in Nigeria. Non-Nigerian governing "
            "law creates enforcement risk for assets or parties based in Nigeria. "
            "\n2. Dispute resolution: arbitration is preferred for commercial disputes — Nigerian courts "
            "are slow (3–7 years for complex matters). The Arbitration and Conciliation Act (Cap A18 LFN "
            "2004) governs domestic arbitration; the Lagos Court of Arbitration (LCA) and Lagos "
            "Multi-Door Courthouse (LMDC) are reliable institutions. "
            "\n3. Liability cap: always cap aggregate liability at the value of fees paid or a multiple "
            "thereof. Uncapped liability creates existential risk for small companies. "
            "\n4. IP ownership: ensure the contract is explicit about who owns deliverables and what "
            "happens to pre-existing IP ('background IP'). Work-for-hire doctrine is not as robust as "
            "in US law; explicit assignment clauses are safer. "
            "\n5. Force majeure: include a clause covering events outside a party's control (strikes, "
            "natural disasters, government action). COVID-19 litigation highlighted gaps in boilerplate "
            "force majeure clauses. "
            "\n6. Data protection: for contracts involving personal data, include a Data Processing "
            "Agreement (DPA) clause referencing NDPA 2023 obligations. "
            "\n7. Payment terms: specify currency (NGN or USD), invoicing cadence, and late payment "
            "interest. Contracts that do not specify currency may be affected by CBN forex regulations. "
            "\n8. Termination for convenience: be clear which party (or both) can terminate without "
            "cause, and the notice required. One-sided termination rights should be flagged."
        ),
    ),
    SourceDocument(
        source_key="nigeria-vendor-agreement-issue-spotting",
        title="Vendor Agreement — Issue-Spotting Guide",
        issuer="Commercial contracts operations summary",
        jurisdiction="Nigeria",
        area="commercial agreements",
        citation_label="Counsel summary: Vendor agreement issue spotting",
        production_ready=True,
        body_text=(
            "Before finalising any vendor or service agreement in Nigeria, the legal ops workflow should "
            "confirm the following: parties (full registered names and RC numbers for companies, not trade "
            "names); scope of work (specific deliverables, timelines, acceptance criteria); fee structure "
            "(fixed vs. variable, milestone-linked vs. monthly); VAT and WHT treatment (who accounts for "
            "VAT and provides WHT credit notes); IP ownership (work product, pre-existing tools, licences "
            "to third-party software); confidentiality (mutual NDA or one-way, duration post-contract); "
            "limitation of liability (cap at contract value; exclude consequential losses); "
            "termination (for cause, for convenience, exit rights); and dispute resolution mechanism. "
            "\n\nCommon issues in Nigerian vendor agreements: "
            "\n• Parties: contracts signed in a trading name not the legal entity name are difficult to "
            "enforce — always use the RC number and full registered name. "
            "\n• WHT: the party receiving payment is often unaware the payer will deduct 5% WHT on "
            "consultancy fees; this must be built into pricing. If the vendor is VAT-registered, they "
            "should issue a VAT invoice and the WHT credit note. "
            "\n• Payment in USD: where parties want USD pricing, the CBN's forex restrictions mean the "
            "agreement should specify whether payment is at official NAFEM/I&E rate or domiciliary "
            "account. Ambiguity here leads to disputes when rates shift. "
            "\n• IP for SaaS/tech vendors: check whether the vendor retains ownership of code and only "
            "licences it to the client. If the client needs ownership (e.g., for fundraising), the "
            "agreement must include an assignment clause, not just a licence. "
            "\n• Governing law mismatch: international vendor templates often specify English or "
            "Delaware law. A Nigerian SME should negotiate for Nigerian governing law or at minimum "
            "mutual recognition of Nigerian court judgments in the dispute resolution clause."
        ),
    ),
    # ── Trademarks ────────────────────────────────────────────────────────────
    SourceDocument(
        source_key="nigeria-trademarks-registration",
        title="Trademarks Act — Brand Registration in Nigeria",
        issuer="Trademarks Act Cap T13 LFN 2004; Trademarks Registry (FIPO)",
        jurisdiction="Nigeria",
        area="intellectual property",
        citation_label="Trademarks Act Cap T13 — Nigerian trademark registration",
        production_ready=True,
        body_text=(
            "Trademark registration in Nigeria is administered by the Federal Institute of Industrial "
            "Property (FIPO), formerly the Trademarks, Patents and Designs Registry (now under FIPO "
            "established by the IP Commission Act 2022). Registration confers the exclusive right to "
            "use the mark in connection with the registered goods/services and provides a basis for "
            "infringement action. "
            "\n\nRegistration process: "
            "\n1. Conduct a trademark search on the FIPO register to identify conflicting marks. "
            "\n2. File an application with: the mark (logo/wordmark), applicant details, class of "
            "goods/services (Nice Classification), and a power of attorney if filed through an agent. "
            "\n3. FIPO examination (formality + substantive): 6–12 months. "
            "\n4. Publication in the Trade Marks Journal for opposition (3 months opposition period). "
            "\n5. If no opposition (or opposition resolved), registration certificate issued. "
            "Total timeline: 18–36 months. "
            "\n\nClasses: Trademarks are registered per class. A brand operating in multiple product/service "
            "categories must file in each relevant class separately. Key classes for Nigerian SMEs: "
            "Class 35 (business services, advertising), Class 36 (financial services), Class 38 "
            "(telecoms), Class 41 (education), Class 42 (technology/SaaS), Class 45 (legal services). "
            "\n\nRenewal: trademark registrations last 7 years from filing date, then renewable for "
            "14-year periods indefinitely. "
            "\n\nCommon law rights: unregistered marks may be protected through a 'passing off' action, "
            "but this requires proof of reputation and goodwill — harder to establish than registration. "
            "\n\nStrategic advice: file early (first-to-file country), before product launch if possible. "
            "File in the name of the company, not the individual founder. Consider international filing "
            "via the Madrid Protocol through WIPO if the brand will operate in multiple African countries."
        ),
    ),
    # ── Employment — Extended ─────────────────────────────────────────────────
    SourceDocument(
        source_key="nigeria-employment-onboarding",
        title="Employment Onboarding — Nigerian SME Checklist",
        issuer="Labour counsel operations summary",
        jurisdiction="Nigeria",
        area="employment",
        citation_label="Counsel summary: Employment onboarding for Nigerian SMEs",
        production_ready=True,
        body_text=(
            "Hiring a first employee in Nigeria triggers a series of statutory obligations that must be "
            "completed before or shortly after the hire. The following checklist is a guide: "
            "\n\nBefore the first hire: "
            "\n• PAYE registration: register with the relevant State Internal Revenue Service (SIRS) "
            "where your office is located. Obtain an employer PAYE reference number. "
            "\n• NSITF registration: register with the Nigeria Social Insurance Trust Fund (NSITF) and "
            "obtain a Group Life Insurance policy as required by the Workmen's Compensation Act / "
            "Employee Compensation Act 2010. Contribution: 1% of annual employee compensation. "
            "\n• PENCOM: register with PENCOM and open a group pension scheme account. Each employee "
            "then chooses their own PFA. "
            "\n• Group life assurance: minimum 3× annual total compensation for employees (required for "
            "companies with 5+ employees under the Pension Reform Act). "
            "\n\nAt the time of hire: "
            "\n• Issue a written employment contract or offer letter within 3 months. "
            "\n• Obtain the employee's NIN, bank account details, and PFA details. "
            "\n• Register the employee with NSITF and PENCOM within 30 days of hire. "
            "\n\nMonthly obligations: "
            "\n• Deduct PAYE from salary and remit to SIRS by the 10th of the following month. "
            "\n• Deduct employee pension contribution (8%) and add employer contribution (10%), "
            "remit to the employee's PFA within 7 working days of salary payment. "
            "\n• Deduct NSITF contribution (1% of payroll) and remit. "
            "\n• Deduct NHF contribution (2.5% of basic salary) for applicable employees and remit "
            "to the Federal Mortgage Bank of Nigeria (FMBN). "
            "\n\nAnnual obligations: "
            "\n• File employer PAYE declaration (Form H1) with SIRS by January 31. "
            "\n• Issue individual employee annual tax statements (Form A) by February 28. "
            "\n• PENCOM annual employer compliance report. "
            "\n\nLeaving employees: pay all outstanding salary, leave pay, and any contractual payments "
            "within 30 days of the last working day. Issue a Form A (tax receipt). Ensure PENCOM and "
            "NSITF are notified of the employee's departure."
        ),
    ),
    # ── Tax — General ─────────────────────────────────────────────────────────
    SourceDocument(
        source_key="nigeria-tax-onboarding-summary",
        title="Nigerian SME Tax Onboarding — Full Checklist",
        issuer="Tax counsel operations summary",
        jurisdiction="Nigeria",
        area="tax",
        citation_label="Counsel summary: Nigeria SME tax onboarding",
        production_ready=True,
        body_text=(
            "A newly incorporated Nigerian company should complete the following tax registrations and "
            "set up compliance workflows before commencement of revenue-generating activities: "
            "\n\n1. TIN Registration: Apply for a corporate TIN from FIRS within 6 months of "
            "incorporation. Required for: bank account opening, government contracts, VAT, WHT, CIT "
            "filings. Apply on firs.gov.ng or through any FIRS integrated service centre. "
            "\n\n2. CIT (Company Income Tax): All Nigerian companies are subject to CIT. Small companies "
            "(turnover ≤ ₦25m) pay 0%. Register for CIT on TaxPro-Max and file annual returns by June "
            "30. Even loss-making companies must file. "
            "\n\n3. VAT Registration: Required once annual turnover reaches ₦25m. Register on TaxPro-Max. "
            "File monthly VAT returns by 21st of the following month. Charge 7.5% VAT on taxable supplies. "
            "\n\n4. PAYE: Register with the State IRS (LIRS for Lagos; FCT IRS for Abuja) before the "
            "first employee is hired. Remit PAYE by 10th of each month. "
            "\n\n5. WHT: Withholding tax must be deducted on certain payments (dividends, rent, "
            "consultancy fees, interest) and remitted to FIRS by 21st of the following month. "
            "\n\n6. Tertiary Education Tax (EDT): 2.5% of assessable profits, filed alongside CIT. "
            "\n\n7. State levies: most states have local business permit fees and development levies "
            "payable annually. Lagos has the Business Premises Permit. Confirm applicable state levies "
            "with a local accountant. "
            "\n\nCompliance calendar trigger points: "
            "• Month 1: obtain TIN, register for CIT "
            "• Month 2–3: register for VAT (or set a trigger when turnover approaches ₦25m) "
            "• Before first hire: PAYE registration "
            "• June 30: CIT and EDT annual return "
            "• 21st each month: VAT and WHT returns "
            "• 10th each month: PAYE remittance "
            "\n\nA licensed tax consultant or accountant should review the company's specific situation — "
            "sector exemptions, fiscal year selection, and group tax considerations all affect the "
            "appropriate compliance workstream."
        ),
    ),
]
