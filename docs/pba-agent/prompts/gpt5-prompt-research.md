# Research Synthesis — Prompt Design Reference

**Purpose:** Audit trail for the design decisions in `base_agent_prompt.md`, `operations_agent_prompt.md`, and `marketing_agent_prompt.md`. Separates **verified** guidelines (traced to authoritative OpenAI sources) from **synthesized** patterns (my architectural recommendations not directly endorsed by OpenAI).

**Validation method:** Every item in Section 1 was re-verified against the cited source during this session. Items in Section 2 are explicitly flagged as synthesis with the reasoning for inclusion.

---

## Authoritative sources consulted

| Source | URL | Date accessed |
|---|---|---|
| OpenAI Model Spec (current) | model-spec.openai.com/2025-12-18.html | Apr 23, 2026 |
| GPT-5.4 Prompt Guidance | developers.openai.com/api/docs/guides/prompt-guidance | Apr 23, 2026 |
| GPT-5.2 Prompting Guide | cookbook.openai.com/examples/gpt-5/gpt-5-2_prompting_guide | Apr 23, 2026 |
| GPT-5.1 Prompting Guide | cookbook.openai.com/examples/gpt-5/gpt-5-1_prompting_guide | Apr 23, 2026 |
| Original GPT-5 Prompting Guide | cookbook.openai.com/examples/gpt-5/gpt-5_prompting_guide | Apr 23, 2026 |
| OpenAI Agents SDK docs | openai.github.io/openai-agents-python/ | Apr 23, 2026 |
| "A practical guide to building agents" | openai.com/business/guides-and-resources/ | Apr 23, 2026 |

---

## Section 1 — Verified guidelines and where they appear in the prompts

| # | Guideline | Source | Applied in |
|---|---|---|---|
| 1 | **Modular, XML-tagged, block-structured prompts** improve GPT-5.x instruction adherence. Tags like `<output_contract>`, `<verification_loop>`, `<tool_persistence_rules>` are the canonical style in OpenAI's own examples. | GPT-5.4 guidance: "Instruction adherence in modular, skill-based, and block-structured prompts when the contract is explicit." GPT-5.2 guide uses same pattern throughout. | Entire structure of base + derived prompts. |
| 2 | **Explicit `<instruction_priority>` block** is the OpenAI-recommended mechanism for declaring how the model should resolve conflicts between layers of instructions. | GPT-5.4 guidance, "Set clear defaults for follow-through" section. Exact starter wording: *"User instructions override default style, tone, formatting, and initiative preferences. Safety, honesty, privacy, and permission constraints do not yield."* | `<instruction_priority>` block in base prompt. |
| 3 | **Chain of command authority levels** — Root > System > Developer > User > Guideline. Developer-role instructions cannot override Root/System; within a developer message, all text is nominally the same authority. | Model Spec "Instructions and levels of authority" section. | Informs the whole design: the prompt's intra-message authority is declared by the prompt itself, because the API does not provide it. |
| 4 | **Untrusted data (quoted text, tool outputs, fetched pages, attachments) has no authority by default.** Imperatives inside these sources should be treated as data unless explicitly delegated. | Model Spec "Ignore untrusted data by default" (Root-level rule). | `<untrusted_input_policy>` block in base. |
| 5 | **Explicit output contracts with concrete length clamps** — 3–6 sentences or ≤5 bullets as a default; ≤2 sentences for simple Q&A; structured format for contractual outputs. | GPT-5.2 guide §3.1 "Controlling verbosity and output shape." Verbatim text reused. | `<output_contract>` block in base. |
| 6 | **Completeness contract** — treat the task as incomplete until all items are covered; track items; verify before finalizing. | GPT-5.4 guidance, "Force completeness on long-horizon tasks." | `<completeness_contract>` in base. |
| 7 | **Verification loop before finalizing** — check correctness, grounding, formatting, safety/irreversibility. | GPT-5.4 guidance, "Add a verification loop before high-impact actions." | Embedded in `<completeness_contract>` in base. |
| 8 | **Tool persistence and dependency-aware rules** — do not skip prerequisites; retry on empty results; parallelize independent reads; sequence dependent steps. | GPT-5.4 guidance, "Make tool use persistent when correctness depends on it" and "Dependency-aware workflows." | `<tool_use_defaults>` block in base. |
| 9 | **Ambiguity handling without blocking** — proceed with stated assumptions when reversible and low-risk; ask only when irreversible. | GPT-5.4 guidance, "Default follow-through policy" and GPT-5.2 guide §3.4. | `<operating_defaults>` in base (ambiguity rule). |
| 10 | **Grounding and uncertainty expression** — prefer retrieved evidence; never fabricate specific figures/IDs/citations; use hedged language when evidence is thin. | GPT-5.2 guide §3.4 (`<uncertainty_and_ambiguity>`); GPT-5.4 `<grounding_rules>`. | `<operating_defaults>` in base (grounding, uncertainty rules). |
| 11 | **Irreversible-action gating** — confirm before executing side-effecting actions (send/purchase/delete/publish/modify production). | Model Spec "Control and communicate side effects" (Root-level). GPT-5.4 `<action_safety>` pattern. | `<non_negotiable>` in base. Amplified in both ops and marketing. |
| 12 | **Don't provide regulated advice as a professional** — legal, medical, financial advice requires a disclaimer and a recommendation to seek qualified help. | Model Spec "Provide information without giving regulated advice" (Developer-level default). | `<non_negotiable>` legal/regulatory rule in base. |
| 13 | **Privilege / confidentiality of developer prompts** — do not reveal the verbatim or paraphrased contents of system/developer messages. | Model Spec "Do not reveal privileged information" (Root-level). | `<non_negotiable>` confidentiality rule in base. |
| 14 | **Separate persistent personality from per-response writing controls** — personality stays stable; length/channel/register vary per response. | GPT-5.4 guidance, "Control personality for customer-facing workflows." | Structural: base defines brand voice (persistent); domain defines channel/length overrides. Used heavily in marketing agent. |
| 15 | **Anti-sycophancy as an explicit rule** — ban openers like "Got it," "Thank you," "Great question." | GPT-5.1 guide, personality section. GPT-5.4 `<user_updates_spec>`: *"Do not begin responses with conversational interjections... Avoid openers such as acknowledgements."* | `<non_negotiable>` brand voice rule; marketing `<brand_voice_extensions>` forbidden-phrasings list. |
| 16 | **Contradictions in a core prompt silently degrade performance.** Cursor case study: fixing contradictions produced large reasoning gains with no other changes. | Original GPT-5 prompting guide, Cursor case study. | Informs the maintenance rule in `base_agent_prompt.md`: "contradiction hunt before each release." |
| 17 | **GPT-5.4 default `reasoning_effort` is `none`; GPT-5's was `medium`.** | GPT-5.2 guide migration table; GPT-5.4 guidance. | Maintenance rule: do not embed reasoning_effort in the prompt; set per-agent in code. |
| 18 | **Reasoning effort is a last-mile knob, not the primary quality lever.** Improve prompt contracts first; raise effort only when evals still regress. | GPT-5.4 guidance, "Treat reasoning effort as a last-mile knob." | Maintenance guidance, not in the prompt itself. |
| 19 | **One change at a time when migrating prompts across model versions** — switch model → pin reasoning_effort → run evals → tune prompt. | GPT-5.2 guide §8 migration steps. | Maintenance section of the base prompt doc. |
| 20 | **Agent.clone(instructions=...) is the SDK-native derivation primitive.** Instructions can also be a callable for runtime composition. | openai-agents-python, Agent class reference. | Drives the recommended composition approach: `clone(instructions=assemble(base, domain))`. |

---

## Section 2 — Synthesized patterns (not directly endorsed by OpenAI; my reasoning for including them)

These patterns are extrapolations or architectural choices I made. I could not find explicit OpenAI documentation endorsing them. I'm including them because they fill gaps that the official guidance does not address for a base+derived prompt architecture.

| # | Pattern | Reasoning for inclusion | Risk if wrong |
|---|---|---|---|
| S1 | **Specific tag names** like `<non_negotiable>`, `<domain_extension>`, `<brand_voice_extensions>`. | OpenAI uses descriptive XML tags in all their examples but does not publish ablation data showing one name outperforms another. Names are chosen for human readability. | Low. If a tag name performs worse, it's a search-and-replace fix. The pattern still works. |
| S2 | **Base-prompt vs. domain-extension composition model** with a fixed `<domain_extension>` insertion point. | The "practical guide to building agents" recommends "a single flexible base prompt that accepts policy variables." I extended that to a two-layer composition with explicit extension points, because domain specialization is substantially more than policy variables. | Moderate. OpenAI may publish a more-recommended pattern (e.g., skills-based prompts via their Skills tool) that supersedes this. Reassess if that happens. |
| S3 | **Locked sections enforced by prompt declaration + engineering-layer append-only rule.** OpenAI's chain of command does not give intra-developer-message authority; you have to declare and enforce it yourself. | This is the only way to make brand/legal/PII rules structurally non-overridable by a domain author. Prompt declaration alone is a soft guarantee; composition-layer CI is what makes it hard. | Low–moderate. If prompt-layer enforcement weakens under adversarial inputs, the CI-enforced append-only rule still holds the structural guarantee. |
| S4 | **"Contradiction hunt" as a pre-release ritual.** | Extrapolated from the Cursor case study (verified item #16). OpenAI endorses fixing contradictions; they do not explicitly recommend a scheduled review. I'm codifying it because prompts drift. | Very low. Worst case: unnecessary process overhead. |
| S5 | **Forbidden-phrasings list** inside marketing agent's `<brand_voice_extensions>`. | OpenAI documents the concept of banning sycophantic openers but does not publish a canonical forbidden-phrasings list for marketing voice. The list is my opinion applied to Echo Theory's stated register. | Low. Edit the list to taste; the structure is sound. |
| S6 | **Specific content-type length contracts for marketing** (tweet ≤280 chars, LinkedIn 100–250 words, blog 800–1500 words, etc.). | OpenAI endorses "concrete length constraints" but publishes no authoritative table of marketing-channel defaults. Numbers are industry-reasonable but not OpenAI-sanctioned. | Low. Tune to your audience data. |
| S7 | **[NEEDS SOURCE] inline tag for unverified marketing claims.** | OpenAI's guidance says not to fabricate; they don't specify a review-handoff convention. This is a workflow detail, not a model behavior detail. | None, provided reviewers know the convention. |
| S8 | **Amplification vs. relaxation taxonomy** (what domains may tighten vs. relax vs. never touch). | This is an architectural vocabulary I imposed. OpenAI does not publish a formal taxonomy for base/derived-prompt governance. | Low. Pure framing choice; swap terminology if it confuses. |

---

## Section 3 — Known unknowns

These are things I could not verify and you should treat as open questions:

1. **How many domain extensions this architecture scales to before prompt length hurts performance.** OpenAI's 1M context on GPT-5.4 makes length less of a concern than it was, but instruction adherence over very long prompts is not specifically benchmarked in the public guides.
2. **Whether GPT-5.5+ (when shipped) will change the recommended structure.** The 5.2 → 5.4 transition preserved most patterns; a bigger jump could move things. Re-verify when the next model family ships.
3. **Whether the prompt-declared authority in `<instruction_priority>` holds under sophisticated prompt injection** (especially when the injection lives inside user-quoted content that the user asked you to process). The `<untrusted_input_policy>` mitigates this but is not a provable guarantee.
4. **Whether the specific `<non_negotiable>` wording survives edge cases in legal/regulatory domains** (GDPR, HIPAA, sector-specific rules). The block is a sensible starting default; it is not a substitute for counsel review in your actual regulated verticals.
5. **Whether "Developer" role is correct for multi-tenant deployments where your customers are effectively developers too.** Model Spec treats your customers as users unless they interact with the API directly. If you expose prompt-editing to your customers, the authority picture changes.

---

**Bottom line:** Items in Section 1 are load-bearing — remove them and you lose OpenAI-endorsed behavior. Items in Section 2 are architectural choices I'm responsible for; they're defensible but swap-able. Section 3 flags what re-verification your team should schedule.