import { PageHeader } from "@/components/page-state"; import { ImportPanel } from "@/components/import-panel";
export default function ImportPage(){return <div className="page-stack"><PageHeader eyebrow="Administrator workflow" title="Import source data" description="Validate, preview, confirm, transform, and publish controlled historical sales and collection records."/><ImportPanel/></div>}
