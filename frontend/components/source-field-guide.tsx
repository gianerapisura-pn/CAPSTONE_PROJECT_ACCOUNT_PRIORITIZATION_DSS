const fields = [
  ["ACCOUNT NAMES", "The recorded customer or account name.", "Text, e.g. Sample Trading Company.", "Required for non-cancelled records. Whitespace is cleaned; names are not automatically merged or used to infer B2B eligibility."],
  ["SI NO.", "The Sales Invoice identifier.", "Text, e.g. 000123.", "Required for non-cancelled records. Keep as text to preserve leading zeros; repeated collection rows may refer to the same invoice."],
  ["SI DATE", "The date of the Sales Invoice.", "Date; use YYYY-MM-DD, e.g. 2025-04-15, to avoid ambiguity.", "A parseable date is required for non-cancelled records. Publication also requires an appropriate verified analysis reference."],
  ["SI AMOUNT", "The recorded invoice amount.", "A positive monetary amount, e.g. 12500.00.", "Required and greater than zero for non-cancelled records. Distinct collection rows do not multiply the invoice amount."],
  ["CR NO.", "The Collection Receipt identifier.", "Text, e.g. 000456.", "May be blank; missing collection evidence can prevent settlement calculation. Keep identifiers as text."],
  ["CR DATE", "The date of the Collection Receipt.", "Date; use YYYY-MM-DD, e.g. 2025-04-20.", "May be blank. An invalid date or one before the invoice produces a warning. Only eligible, cutoff-known evidence supports settlement."],
  ["CR AMOUNT", "The recorded amount collected.", "A monetary amount, e.g. 12250.00.", "May be blank. Invalid nonblank amounts produce warnings; settlement needs independently reconciled collection evidence."],
  ["EWT", "The recorded Expanded Withholding Tax amount.", "A monetary amount, e.g. 250.00; use 0 only when zero is actually recorded.", "May be blank, but blank is not zero. A receipt with missing EWT produces a warning; settlement requires independent full reconciliation."],
  ["PAYMENT MODE", "The recorded method of payment.", "Text, e.g. Bank transfer.", "May be blank; the current validator does not impose a fixed payment-method list. Record the source value without guessing."],
  ["PAYMENT STATUS", "The source record's payment status.", "Fully Paid or Cancelled. Paid/full payment and canceled/void/voided are recognized equivalents.", "Blank, partial or unsupported statuses require review before publication. Cancelled records are identified first, kept for audit and excluded from analytics."],
];

export function SourceFieldGuide() {
  return <section className="data-section source-field-guide" aria-labelledby="source-fields-title">
    <div className="section-heading"><h2 id="source-fields-title">Required Source File Columns</h2></div>
    <p>Source files must contain these 10 required fields before they can be validated for import.</p>
    <p className="fine-print">All column headers are required. Whether an individual value may be empty depends on the field and record status. Examples below are illustrative.</p>
    <div className="source-field-grid">{fields.map(([name, meaning, format, rule]) => <details key={name}>
      <summary>{name}</summary><p>{meaning}</p><p><strong>Format:</strong> {format}</p><p><strong>Validation:</strong> {rule}</p>
    </details>)}</div>
  </section>;
}
