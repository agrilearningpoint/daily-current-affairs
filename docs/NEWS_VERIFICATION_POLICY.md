# Zero-Error News Research & Verification Policy

1. **Primary Source Priority**: Official releases from PIB, Ministry of Agriculture & Farmers Welfare (`agriwelfare.gov.in`), ICAR, DAHD, NABARD, RBI, SEBI, ISRO, DRDO, NITI Aayog, MoEFCC, FAO, World Bank, and IMF take precedence over secondary editorial summaries.
2. **Strict Numerical Grounding**: Every monetary figure (`₹`, `crore`, `lakh`), percentage (`%`), production volume (`LMT`, `MT`), and rank in an edited summary or bullet is cross-checked by `verify_claim_against_source()` against the raw source evidence. Any item containing an ungrounded number is quarantined.
3. **Contradiction Quarantine**: When two sources covering the same event report conflicting numerical figures, `detect_source_contradictions()` flags and quarantines the disputed fact rather than guessing one number.
4. **Provisional vs. Final Labeling**: Figures marked as `provisional`, `advance estimate`, or `revised` retain their exact status qualifier in `state/fact_ledger.json`.
5. **Strict 24-Hour IST Window**: Only news published within the configured 24-hour `Asia/Kolkata` window is eligible; missing timestamps are quarantined.
