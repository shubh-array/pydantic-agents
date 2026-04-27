import { useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import { defaultAnalyticsJsonl } from "./defaultData";
import "./App.css";

type AnalyticsRecord = Record<string, unknown>;

type ParsedLine = {
  line: number;
  raw: string;
  record?: AnalyticsRecord;
  error?: string;
};

type FieldProfile = {
  name: string;
  present: number;
  nullish: number;
  types: Record<string, number>;
  examples: string[];
};

const FILTER_ALL = "__all__";

function parseJsonl(input: string): ParsedLine[] {
  return input
    .split(/\r?\n/)
    .map((raw, index) => ({ raw: raw.trim(), line: index + 1 }))
    .filter((line) => line.raw.length > 0)
    .map((line) => {
      try {
        const parsed = JSON.parse(line.raw);
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
          return { ...line, error: "Line is not a JSON object" };
        }
        return { ...line, record: parsed as AnalyticsRecord };
      } catch (error) {
        return {
          ...line,
          error: error instanceof Error ? error.message : "Invalid JSON",
        };
      }
    });
}

function valueType(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value;
}

function asString(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not set";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function asNumber(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function asDate(value: unknown): Date | undefined {
  if (typeof value !== "string") return undefined;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

function fmtInt(value: number): string {
  return new Intl.NumberFormat().format(Math.round(value));
}

function fmtMs(value: number): string {
  if (value < 1000) return `${fmtInt(value)} ms`;
  if (value < 60000) return `${(value / 1000).toFixed(1)} s`;
  return `${(value / 60000).toFixed(1)} min`;
}

function countBy(records: AnalyticsRecord[], field: string): [string, number][] {
  const counts = new Map<string, number>();
  records.forEach((record) => {
    const key = asString(record[field]);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  });
  return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}

function sum(records: AnalyticsRecord[], field: string): number {
  return records.reduce((total, record) => total + (asNumber(record[field]) ?? 0), 0);
}

function profileFields(records: AnalyticsRecord[]): FieldProfile[] {
  const profiles = new Map<string, FieldProfile>();
  records.forEach((record) => {
    Object.entries(record).forEach(([name, value]) => {
      const profile =
        profiles.get(name) ??
        { name, present: 0, nullish: 0, types: {}, examples: [] };
      profile.present += 1;
      if (value === null || value === undefined) profile.nullish += 1;
      const type = valueType(value);
      profile.types[type] = (profile.types[type] ?? 0) + 1;
      const example = asString(value);
      if (example !== "Not set" && profile.examples.length < 3 && !profile.examples.includes(example)) {
        profile.examples.push(example.length > 80 ? `${example.slice(0, 80)}...` : example);
      }
      profiles.set(name, profile);
    });
  });
  return [...profiles.values()].sort((a, b) => a.name.localeCompare(b.name));
}

function bucketTimeline(records: AnalyticsRecord[]): { label: string; count: number }[] {
  const dated = records
    .map((record) => asDate(record.ts))
    .filter((date): date is Date => Boolean(date))
    .sort((a, b) => a.getTime() - b.getTime());
  if (!dated.length) return [];

  const start = dated[0].getTime();
  const end = dated[dated.length - 1].getTime();
  const span = Math.max(end - start, 1);
  const bucketCount = Math.min(36, Math.max(8, Math.ceil(Math.sqrt(dated.length))));
  const bucketMs = Math.max(Math.ceil(span / bucketCount), 1000);
  const buckets = new Map<number, number>();

  dated.forEach((date) => {
    const bucket = start + Math.floor((date.getTime() - start) / bucketMs) * bucketMs;
    buckets.set(bucket, (buckets.get(bucket) ?? 0) + 1);
  });

  return [...buckets.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([bucket, count]) => ({
      label: new Date(bucket).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      count,
    }));
}

function downloadText(filename: string, text: string) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function StatCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-detail">{detail}</div>
    </div>
  );
}

function BarList({ title, data, limit = 8 }: { title: string; data: [string, number][]; limit?: number }) {
  const max = Math.max(...data.map(([, count]) => count), 1);
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>{title}</h2>
        <span>{data.length} groups</span>
      </div>
      <div className="bar-list">
        {data.slice(0, limit).map(([label, count]) => (
          <div className="bar-row" key={label}>
            <div className="bar-meta">
              <span title={label}>{label}</span>
              <strong>{fmtInt(count)}</strong>
            </div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${(count / max) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Timeline({ data }: { data: { label: string; count: number }[] }) {
  const max = Math.max(...data.map((point) => point.count), 1);
  return (
    <section className="panel wide">
      <div className="panel-heading">
        <h2>Event Timeline</h2>
        <span>{data.length} buckets</span>
      </div>
      <div className="timeline">
        {data.map((point, index) => (
          <div className="timeline-bar" key={`${point.label}-${index}`}>
            <div
              className="timeline-fill"
              style={{ height: `${Math.max(8, (point.count / max) * 100)}%` }}
              title={`${point.label}: ${point.count}`}
            />
            <span>{point.label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function App() {
  const [sourceName, setSourceName] = useState("Comprehensive hook simulation analytics.jsonl");
  const [jsonl, setJsonl] = useState(defaultAnalyticsJsonl);
  const [eventFilter, setEventFilter] = useState(FILTER_ALL);
  const [policyFilter, setPolicyFilter] = useState(FILTER_ALL);
  const [query, setQuery] = useState("");
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteValue, setPasteValue] = useState("");

  const parsed = useMemo(() => parseJsonl(jsonl), [jsonl]);
  const records = useMemo(
    () => parsed.flatMap((line) => (line.record ? [line.record] : [])),
    [parsed],
  );
  const errors = parsed.filter((line) => line.error);

  const eventTypes = useMemo(() => countBy(records, "event_type"), [records]);
  const policies = useMemo(() => countBy(records, "policy_outcome"), [records]);

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return records.filter((record) => {
      if (eventFilter !== FILTER_ALL && asString(record.event_type) !== eventFilter) return false;
      if (policyFilter !== FILTER_ALL && asString(record.policy_outcome) !== policyFilter) return false;
      if (!normalizedQuery) return true;
      return JSON.stringify(record).toLowerCase().includes(normalizedQuery);
    });
  }, [records, eventFilter, policyFilter, query]);

  const schema = useMemo(() => profileFields(records), [records]);
  const timeline = useMemo(() => bucketTimeline(filtered), [filtered]);
  const shellRecords = filtered.filter((record) => asString(record.event_type) === "shell_eval");
  const promptRecords = filtered.filter((record) => asString(record.event_type) === "prompt_submit");
  const blockedRecords = filtered.filter(
    (record) =>
      record.policy_outcome === "deny" ||
      Boolean(record.deny_reason) ||
      (Array.isArray(record.policy_violations) && record.policy_violations.length > 0),
  );
  const shadowDenyRecords = filtered.filter((record) => record.any_would_deny === true);
  const skillSignalRecords = filtered.filter((record) => record.skill_signal === true);
  const dated = filtered.flatMap((record) => {
    const date = asDate(record.ts);
    return date ? [date.getTime()] : [];
  });
  const firstDate = dated.length ? new Date(Math.min(...dated)) : undefined;
  const lastDate = dated.length ? new Date(Math.max(...dated)) : undefined;
  const spanMs = firstDate && lastDate ? lastDate.getTime() - firstDate.getTime() : 0;

  const commandRows = shellRecords
    .filter((record) => record.command_sample)
    .slice(-12)
    .reverse();

  const blockedRows = blockedRecords
    .slice()
    .reverse();

  const generationRows = countBy(filtered, "generation_id")
    .filter(([id]) => id !== "Not set")
    .slice(0, 8)
    .map(([id, count]) => ({ id, count }));

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setJsonl(await file.text());
    setSourceName(file.name);
    setEventFilter(FILTER_ALL);
    setPolicyFilter(FILTER_ALL);
    setQuery("");
  }

  function applyPaste() {
    setJsonl(pasteValue);
    setSourceName("Pasted JSONL");
    setPasteOpen(false);
    setEventFilter(FILTER_ALL);
    setPolicyFilter(FILTER_ALL);
    setQuery("");
  }

  return (
    <main className="dashboard">
      <section className="hero-panel">
        <div>
          <div className="eyebrow">Agent session analytics</div>
          <h1>Cursor Agent JSONL Dashboard</h1>
          <p>
            Explore event streams from agentic coding sessions. Load any JSONL file
            with the same event schema to inspect policy outcomes, shell activity,
            prompts, durations, and field coverage.
          </p>
        </div>
        <div className="source-card">
          <span>Current source</span>
          <strong>{sourceName}</strong>
          <div className="source-actions">
            <label className="button">
              Upload JSONL
              <input type="file" accept=".jsonl,.json,.txt" onChange={handleFile} />
            </label>
            <button type="button" onClick={() => setPasteOpen((open) => !open)}>
              Paste
            </button>
            <button type="button" onClick={() => downloadText("filtered-events.jsonl", filtered.map((record) => JSON.stringify(record)).join("\n"))}>
              Export filtered
            </button>
          </div>
        </div>
      </section>

      {pasteOpen && (
        <section className="panel paste-panel">
          <div className="panel-heading">
            <h2>Paste JSONL</h2>
            <span>{pasteValue.length} chars</span>
          </div>
          <textarea
            value={pasteValue}
            onChange={(event) => setPasteValue(event.target.value)}
            placeholder="Paste newline-delimited JSON records here..."
          />
          <button type="button" onClick={applyPaste} disabled={!pasteValue.trim()}>
            Analyze pasted data
          </button>
        </section>
      )}

      <section className="filters">
        <label>
          Event type
          <select value={eventFilter} onChange={(event) => setEventFilter(event.target.value)}>
            <option value={FILTER_ALL}>All events</option>
            {eventTypes.map(([eventType]) => (
              <option value={eventType} key={eventType}>
                {eventType}
              </option>
            ))}
          </select>
        </label>
        <label>
          Policy outcome
          <select value={policyFilter} onChange={(event) => setPolicyFilter(event.target.value)}>
            <option value={FILTER_ALL}>All outcomes</option>
            {policies.map(([policy]) => (
              <option value={policy} key={policy}>
                {policy}
              </option>
            ))}
          </select>
        </label>
        <label className="search">
          Search records
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="command, model, reason, id..." />
        </label>
      </section>

      {errors.length > 0 && (
        <section className="error-panel">
          <strong>{errors.length} parse errors</strong>
          <span>First issue on line {errors[0].line}: {errors[0].error}</span>
        </section>
      )}

      <section className="stats-grid">
        <StatCard label="Records" value={fmtInt(filtered.length)} detail={`${fmtInt(records.length)} total parsed`} />
        <StatCard label="Session span" value={spanMs ? fmtMs(spanMs) : "n/a"} detail={firstDate && lastDate ? `${firstDate.toLocaleString()} to ${lastDate.toLocaleTimeString()}` : "No timestamps"} />
        <StatCard label="Blocked" value={fmtInt(blockedRecords.length)} detail={`${fmtInt(shellRecords.length)} shell checks`} />
        <StatCard label="Shadow denies" value={fmtInt(shadowDenyRecords.length)} detail={`${fmtInt(sum(promptRecords, "shell_fence_count"))} shell fences`} />
        <StatCard label="Skill signals" value={fmtInt(skillSignalRecords.length)} detail="Task/subagent audit hints" />
        <StatCard label="Schema fields" value={fmtInt(schema.length)} detail={`${fmtInt(errors.length)} invalid lines`} />
      </section>

      <section className="panel danger-panel">
        <div className="panel-heading">
          <h2>Blocked & Dangerous Operations</h2>
          <span>{fmtInt(blockedRecords.length)} denied or violation-bearing records</span>
        </div>
        <div className="blocked-list">
          {blockedRows.map((record, index) => (
            <article key={`${record.ts}-${index}`}>
              <div className="blocked-topline">
                <strong>{asString(record.deny_reason || record.policy_reason || record.policy_outcome)}</strong>
                <span>{asString(record.event_type)} / {asString(record.command_class)}</span>
              </div>
              <code>{asString(record.command_sample)}</code>
              <div className="blocked-meta">
                <span>Trace: {Array.isArray(record.policy_trace) ? record.policy_trace.join(" -> ") : "n/a"}</span>
                <span>Violations: {Array.isArray(record.policy_violations) ? record.policy_violations.join(", ") : "n/a"}</span>
              </div>
            </article>
          ))}
          {!blockedRows.length && <p>No denied operations in the current filter.</p>}
        </div>
      </section>

      <section className="chart-grid">
        <Timeline data={timeline} />
        <BarList title="Event Types" data={eventTypes} />
        <BarList title="Policy Outcomes" data={policies} />
        <BarList title="Command Classes" data={countBy(filtered, "command_class")} />
        <BarList title="Models" data={countBy(filtered, "model")} limit={5} />
      </section>

      <section className="panel wide">
        <div className="panel-heading">
          <h2>Recent Shell Commands</h2>
          <span>{fmtInt(shellRecords.length)} shell evaluations</span>
        </div>
        <div className="command-list">
          {commandRows.map((record, index) => (
            <article key={`${record.generation_id}-${index}`}>
              <div>
                <strong>{asString(record.command_class)}</strong>
                <span>{asString(record.policy_outcome)} / {asString(record.policy_reason)}</span>
              </div>
              <code>{asString(record.command_sample)}</code>
            </article>
          ))}
          {!commandRows.length && <p>No shell command samples in the current filter.</p>}
        </div>
      </section>

      <section className="two-column">
        <section className="panel">
          <div className="panel-heading">
            <h2>Top Generations</h2>
            <span>{generationRows.length} shown</span>
          </div>
          <div className="generation-list">
            {generationRows.map((row) => (
              <div key={row.id}>
                <code>{row.id.slice(0, 12)}...</code>
                <strong>{row.count} events</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Policy Signals</h2>
            <span>Current filter</span>
          </div>
          <div className="signal-grid">
            <StatCard label="Would deny" value={fmtInt(filtered.filter((record) => record.any_would_deny === true).length)} detail="prompt-level signal" />
            <StatCard label="Violations" value={fmtInt(filtered.filter((record) => Array.isArray(record.policy_violations) && record.policy_violations.length > 0).length)} detail="records with violations" />
          </div>
        </section>
      </section>

      <section className="panel wide">
        <div className="panel-heading">
          <h2>Schema Profile</h2>
          <span>{schema.length} fields across {fmtInt(records.length)} records</span>
        </div>
        <div className="schema-table">
          <table>
            <thead>
              <tr>
                <th>Field</th>
                <th>Coverage</th>
                <th>Types</th>
                <th>Examples</th>
              </tr>
            </thead>
            <tbody>
              {schema.map((field) => (
                <tr key={field.name}>
                  <td><code>{field.name}</code></td>
                  <td>{Math.round((field.present / Math.max(records.length, 1)) * 100)}% present, {fmtInt(field.nullish)} null</td>
                  <td>{Object.entries(field.types).map(([type, count]) => `${type} (${count})`).join(", ")}</td>
                  <td>{field.examples.join(" | ") || "No non-null examples"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

export default App;
