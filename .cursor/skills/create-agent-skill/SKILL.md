---
name: create-agent-skill
description: Create, evaluate, and improve Cursor agent skills using an adapter-backed harness for authoring, evaluation, and iteration.
license: See LICENSE.txt
---

# create-agent-skill

A skill for creating new skills and iteratively improving them using an **adapter-backed agent harness**. The active adapter (how runs are invoked, how transcripts are parsed) is selected from **`config/active_agent`**. Agent-specific CLI and environment details live in **`adapters/<active_agent>/recipes.md`**.

At a high level, the process of creating a skill goes like this:

- Decide what you want the skill to do and roughly how it should do it
- Write a draft of the skill
- Author test prompts and run dual evaluations (candidate skill vs baseline) through the harness
- Help the user evaluate the results both qualitatively and quantitatively
  - While runs execute in the background, draft or refine relevant quantitative assertions. Explain them to the user (or explain existing ones)
  - Use **`eval-harness/viewer/generate_review.py`** so the user can review outputs and metrics
- Rewrite the skill based on feedback from the user’s review and from benchmarks
- Repeat until you are satisfied
- Expand the test set and try again at larger scale when appropriate

Your job when using this skill is to figure out where the user is in this process and help them move forward and progress through these stages. For instance, if they say “I want to make a skill for X,” you can help narrow down the intent, write a draft, write test cases, figure out how they want to evaluate, run the harness, the prompts and repeat. 

On the other hand, if they already have a draft, go straight to the eval and iteration loop.

Stay flexible: if the user does not want heavy evaluation, collaborate in a lighter-weight way.

Then, after the skill is in good shape (order is flexible), you can run **description optimization** so the frontmatter description triggers reliably.

---

## Communicating with the user

This skill may be used by people with different levels of familiarity with technical jargon. Pay attention to context cues to understand how to phrase your communication! In the default case, just to give you some idea:

- “Evaluation” and “benchmark” are usually fine without definition
- For “JSON” and “assertion,” prefer short explanations unless the user clearly knows these terms

It is OK to define terms briefly when in doubt, and feel free to clarify terms with a short definition if you're unsure if the user will get it.

---

## Creating a skill

### Capture intent

Start by understanding the user’s intent. The current conversation may already describe a workflow to capture (for example, they say “turn this into a skill”). If so, extract answers from the conversation history first — the tools used, the sequence of steps, corrections the user made, input/output formats observed. The user may need to fill gaps and should confirm before you proceed to the next step.

1. What should this skill enable the **agent** to do?
2. When should this skill trigger? (what user phrases and contexts)
3. What is the expected output format?
4. Should you set up test cases? Skills with objectively checkable outputs (file transforms, data extraction, code generation, fixed workflows) usually benefit from test cases. Skills with subjective outputs (writing style, art) often do not need them. Suggest a sensible default based on the skill type, but let the user decide.

### Interview and research

Proactively ask about edge cases, input/output formats, example files, success criteria, and dependencies. Wait to finalize test prompts until this is solid and you are confident enough to proceed further.

Check available MCPs - if useful for research (searching docs, finding similar skills, looking up best practices), research in parallel via subagents if available, otherwise inline. Come prepared with context to reduce burden on the user.

### Write the `SKILL.md`

From the interview, fill in:

- **name**: Skill identifier
- **description**: When to trigger and what it does. This is the primary triggering signal: include both what the skill does **AND** specific contexts for when to use it. Put “when to use” information here, not only in the body. Models often **under-trigger** skills — they don't use them when they'd be useful. To combat this, please make the skill descriptions a little bit "pushy". So for instance, instead of "How to build a simple fast dashboard to display internal company finance data.", you might write "How to build a simple fast dashboard to display internal financial data. Make sure to use this skill whenever the user mentions dashboards, data visualization, internal metrics, or wants to display any kind of company data, even if they don't explicitly ask for a 'dashboard.'"
- **compatibility**: Required tools or dependencies (optional, rarely needed)
- **Body**: The rest of the instructions

### Skill writing guide

#### Anatomy of a skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled resources (optional)
    ├── scripts/    - Executable code for deterministic or repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

#### Progressive disclosure

Skills use a three-level loading system:

1. **Metadata** (name + description) — always available in the context (~100 words)
2. **`SKILL.md` body** — In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** — As needed (unlimited, scripts can execute without loading)

These word counts are approximate and you can feel free to go longer if needed.

**Patterns:**

- Keep `SKILL.md` under 500 lines; if you're approaching this limit, add an additional layer of hierarchy along with clear pointers about where the model using the skill should go next to follow up.
- Reference files clearly with guidance on when to read them
- For large references (> 300 lines), add a table of contents

**Domain organization** When a skill supports multiple domains/frameworks, organize by variant:

```
cloud-deploy/
├── SKILL.md (workflow + selection)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

The agent reads only the relevant reference file.

#### Principle of lack of surprise

This goes without saying, but SKILLS MUST NOT contain malware, exploit code, or any content that could compromise system security. A skill's contents should not surprise the user in their intent if described. Don't go along with requests to create misleading skills or skills designed to facilitate unauthorized access, data exfiltration, or other malicious activities. Things like a "roleplay as an XYZ" are OK though.

#### Writing patterns

Prefer direct, imperative instructions.

**Output formats** — define templates when helpful:

```markdown
## Report structure
ALWAYS use this exact template:
# [Title]
## Executive summary
## Key findings
## Recommendations
```

**Examples pattern** - It's useful to include examples. You can format them like this (but if "Input" and "Output" are in the examples you might want to deviate a little):

```markdown
## Commit message format
**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

#### Writing style

Explain *why* something matters instead of stacking rigid “MUST” rules. Use theory of mind and try to make the skill general and not super-narrow to specific examples. Start by writing a draft and then look at it with fresh eyes and improve it.


### Test cases

After writing the skill draft, come up with 2-3 realistic test prompts — the kind of thing a real user would actually say. Share them with the user: [you don't have to use this exact language] "Here are a few test cases I'd like to try. Do these look right, or do you want to add more?" Then run them.

Save cases under the skill under test as **`evals/evals.json`**. Start with prompts (and optional expectations); you will refine assertions (expectations) in the next step while runs are in flight.

Shape (prompts only at first):

```json
[
  {
    "id": 1,
    "prompt": "User's task prompt",
    "files": []
  }
]
```

After drafting assertions (Step 3), add structured expectations:

```json
[
  {
    "id": 1,
    "prompt": "User's task prompt",
    "expectations": [
      {"assertion_id": "has-output", "text": "Produces the expected file", "critical": true}
    ],
    "files": []
  }
]
```

Full field definitions and validation: **`references/schemas/evals.schema.json`**. Related structures use the other JSON schemas in **`references/schemas/`** (see **Reference files** below).

---

## Running and evaluating test cases

This section is one continuous sequence—do not stop partway through. Use the harness and the phase map in **`references/execution-contract.md`**.

Put results in **`<skill-name>-workspace/`** as a sibling of the skill directory. Within the workspace, organize results by iteration (`iteration-1/`, `iteration-2/`, etc.) and within that, each test case gets a directory (`eval-0/`, `eval-1/`, etc.). Don't create all of this upfront — just create directories as you go.

**Working directory:** Run harness commands with the **create-agent-skill root** (this skill’s directory) as the current working directory so imports resolve.

### Step 1: Preflight and eval JSON

Validate the skill under test:

```bash
python scripts/quick_validate.py <path-to-skill-under-test>
```

Author **`evals/evals.json`** on the skill under test. When present, quick validation checks it against **`references/schemas/evals.schema.json`**.

**Description trigger check (optional):** To measure whether the frontmatter description should fire for a labeled query set (before or alongside full task runs), run:

```bash
python eval-harness/scripts/run_eval.py trigger --eval-set <path-to-json> --skill-path <path-to-skill-under-test>
```

### Step 2: Dual execution (candidate vs baseline)

Launch **with_skill** and baseline runs **in the same batch** when your environment supports parallel work—do not serialize unnecessarily. Dual runs compare the skill-enabled agent against a baseline:

- **New skill:** baseline is **without_skill** (no skill).
- **Improving an existing skill:** baseline can be **old_skill** (prior snapshot). Snapshot the skill before editing if you need a stable baseline.

Write **`iteration-N/iteration.json`** (paths, baseline type, eval references). The manifest is schema-validated against **`references/schemas/iteration.schema.json`** before any runs start — malformed manifests fail fast.

Minimal `iteration.json`:

```json
{
  "skill_path": "/abs/path/to/<skill-name>",
  "evals_path": "/abs/path/to/<skill-name>/evals/evals.json",
  "runs_per_configuration": 1
}
```

When `baseline_type` is `old_skill`, also set `old_skill_path` to the snapshot directory.

Then run:

```bash
python eval-harness/scripts/run_eval.py dual --iteration N --workspace <workspace>
```

**Skill isolation contract.** The default executor template (**`agents/executor.md`**) contains a `{{SKILL_CONTENT}}` placeholder. For `with_skill` runs the harness substitutes the candidate SKILL.md content; for `without_skill` runs it substitutes an empty string; for `old_skill` runs it substitutes the snapshot. This is what makes the comparison meaningful — the baseline genuinely lacks the skill.

Runs are laid out under **`<workspace>/iteration-N/<eval-id>/`** with sides **`with_skill`**, **`without_skill`**, or **`old_skill`** (see **`references/evaluation.md`**). Timing is written to each run’s **`timing.json`** (schema: **`references/schemas/timing.schema.json`**).

**Note:** For each test case, spawn two subagents in the same turn — one with the skill, one without. This is important: don't spawn the with-skill runs first and then come back for baselines later. Launch everything at once so it all finishes around the same time.

Adapter specifics (timeouts, transcripts, parallelism): **`adapters/<active_agent>/recipes.md`**.

### Step 3: While runs are in progress, draft assertions

Use the wait time to draft **quantitative assertions** where they add value. If assertions already exist in **`evals/evals.json`**, review and explain them.

Good assertions are objectively verifiable and have descriptive names — they should read clearly in the benchmark viewer so someone glancing at the results immediately understands what each one checks. Subjective skills (writing style, design quality) are better evaluated qualitatively — don't force assertions onto things that need human judgment.

Update the `eval_metadata.json` files and `evals/evals.json` with the assertions once drafted. Also explain to the user what they'll see in the viewer — both the qualitative outputs and the quantitative benchmark.

Persist expectations so graders can emit **`grading.json`** (see **`references/schemas/grading.schema.json`**). The viewer’s formal grades expect consistent field names—follow **`agents/grader.md`**.

### Step 4: Grade, aggregate, open the viewer

When runs finish:

1. **Grade each run** by spawning a grader subagent (or grade inline) that reads **`agents/grader.md`** and evaluate each assertion against the outputs. Save results to **`grading.json`** per run (in each run directory). Prefer small scripts for repeatable checks. For assertions that can be checked programmatically, write and run a script rather than eyeballing it — scripts are faster, more reliable, and can be reused across iterations.

2. **Aggregate** into **`benchmark.json`** / **`benchmark.md`**:

   ```bash
   python eval-harness/scripts/aggregate_benchmark.py --iteration N --workspace <workspace> --skill-name <name>
   ```

   Schema: **`references/schemas/benchmark.schema.json`**.

3. **Gate the iteration** (project-specific thresholds live only in **`config/thresholds.json`**):

   ```bash
   python scripts/check_iteration.py --iteration N --workspace <workspace>
   ```

4. **Analyst pass** — read **`agents/analyzer.md`** (benchmark analysis) for patterns aggregates hide (non-discriminating checks, flaky evals, time/token tradeoffs).

5. **Launch the viewer** (qualitative + quantitative):

   ```bash
   python eval-harness/viewer/generate_review.py <workspace> --iteration N --skill-name <name> --benchmark <workspace>/iteration-N/benchmark.json > /dev/null 2>&1 & VIEWER_PID=$!
   ```

   For iteration 2+, pass **`--previous-workspace`** to the prior iteration’s workspace when you need diff context.

   **Headless or no browser:** use **`--static <output_path>`** to emit standalone HTML. If feedback is downloaded from the viewer UI, place **`feedback.json`** in the workspace for the next iteration.

6. Tell the user how to use the **Outputs** and **Benchmark** views and that **`feedback.json`** captures submitted notes.

#### What the user sees in the viewer

The "Outputs" tab shows one test case at a time:
- **Prompt**: the task that was given
- **Output**: the files the skill produced, rendered inline where possible
- **Previous Output** (iteration 2+): collapsed section showing last iteration's output
- **Formal Grades** (if grading was run): collapsed section showing assertion pass/fail
- **Feedback**: a textbox that auto-saves as they type
- **Previous Feedback** (iteration 2+): their comments from last time, shown below the textbox

The "Benchmark" tab shows the stats summary: pass rates, timing, and token usage for each configuration, with per-eval breakdowns and analyst observations.

Navigation is via prev/next buttons or arrow keys. When done, they click "Submit All Reviews" which saves all feedback to `feedback.json`.

### Step 5: Read feedback

When the user is done reviewing, read **`feedback.json`** (schema: **`references/schemas/feedback.schema.json`**). Empty feedback usually means no issues—prioritize cases with specific complaints.

Stop the viewer process when finished (if you started a local server).

Kill the viewer server when you're done with it:

```bash
kill $VIEWER_PID 2>/dev/null
```

### Step 6: Promotion gate (phase F)

When **`feedback.json`** exists and **`benchmark.json`** is ready, run the promotion gate (thresholds only in **`config/thresholds.json`**):

```bash
python scripts/check_promotion.py --iteration N --workspace <workspace>
```

---

## Improving the skill

### How to think about improvements

1. **Generalize from the feedback.** The big picture thing that's happening here is that we're trying to create skills that can be used a million times (maybe literally, maybe even more who knows) across many different prompts. Here you and the user are iterating on only a few examples over and over again because it helps move faster. The user knows these examples in and out and it's quick for them to assess new outputs. But if the skill you and the user are codeveloping works only for those examples, it's useless. Rather than put in fiddly overfitty changes, or oppressively constrictive MUSTs, if there's some stubborn issue, you might try branching out and using different metaphors, or recommending different patterns of working. It's relatively cheap to try and maybe you'll land on something great.

2. **Keep the prompt lean.** Remove things that aren't pulling their weight. Make sure to read the transcripts, not just the final outputs — if it looks like the skill is making the model waste a bunch of time doing things that are unproductive, you can try getting rid of the parts of the skill that are making it do that and seeing what happens.

3. **Explain the why.** Try hard to explain the **why** behind everything you're asking the model to do. Today's LLMs are *smart*. They have good theory of mind and when given a good harness can go beyond rote instructions and really make things happen. Even if the feedback from the user is terse or frustrated, try to actually understand the task and why the user is writing what they wrote, and what they actually wrote, and then transmit this understanding into the instructions. If you find yourself writing ALWAYS or NEVER in all caps, or using super rigid structures, that's a yellow flag — if possible, reframe and explain the reasoning so that the model understands why the thing you're asking for is important. That's a more humane, powerful, and effective approach.

4. **Look for repeated work across test cases.** Read the transcripts from the test runs and notice if the subagents all independently wrote similar helper scripts or took the same multi-step approach to something. If all 3 test cases resulted in the subagent writing a `create_docx.py` or a `build_chart.py`, that's a strong signal the skill should bundle that script. Write it once, put it in `scripts/`, and tell the skill to use it. This saves every future invocation from reinventing the wheel.

This task is pretty important (we are trying to create billions a year in economic value here!) and your thinking time is not the blocker; take your time and really mull things over. I'd suggest writing a draft revision and then looking at it anew and making improvements. Really do your best to get into the head of the user and understand what they want and need.

### The iteration loop

After improving the skill:

1. **Before making any edits**, snapshot the current skill directory to **`<workspace>/iteration-N-snapshot/`**. This preserves the exact version that produced the current iteration's results and can serve as an `old_skill` baseline later.
2. Apply updates to the skill under test.
3. Re-run all cases into a **new** **`iteration-(N+1)/`**, including baselines (for a new skill, baseline stays **without_skill**).
4. Open the viewer with **`--previous-workspace`** pointing at the prior iteration when applicable.
5. Wait for user review and new feedback.
6. Repeat until the user is satisfied, feedback is uniformly positive, or progress stalls.

**Default cap: 3 iterations.** By default the harness runs at most **three** iterations for both body and description optimization. Three is usually enough to get past the obvious wins and surface diminishing returns; going further tends to overfit a small eval set. If you need more, bump `--max-iterations` explicitly and justify it with the benchmark trend.

**When the user declines further iterations or the promotion gate passes**, proceed to the "Description optimization" section below. Always offer this step — even when the body is stable, the frontmatter description may under-trigger or over-trigger.

---

## Advanced: Blind comparison

For a stricter comparison of two skill versions, use the blind comparison flow in **`agents/comparator.md`** with analysis guidance in **`agents/analyzer.md`**. Optional and heavier than the default human review loop.

---

## Description optimization

The **`description`** field in frontmatter is the main trigger signal. After the skill works well, offer to optimize it.

### Step 1: Generate trigger eval queries

Create ~20 queries—mix of **should-trigger** and **should-not-trigger**. Save as JSON:

```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "another prompt", "should_trigger": false}
]

```

The queries must be realistic and something a user would actually type. Not abstract requests, but requests that are concrete and specific and have a good amount of detail. For instance, file paths, personal context about the user's job or situation, column names and values, company names, URLs. A little bit of backstory. Some might be in lowercase or contain abbreviations or typos or casual speech. Use a mix of different lengths, and focus on edge cases rather than making them clear-cut (the user will get a chance to sign off on them).

Bad: `"Format this data"`, `"Extract text from PDF"`, `"Create a chart"`

Good: `"ok so my boss just sent me this xlsx file (its in my downloads, called something like 'Q4 sales final FINAL v2.xlsx') and she wants me to add a column that shows the profit margin as a percentage. The revenue is in column C and costs are in column D i think"`

For the **should-trigger** queries (8-10), think about coverage. You want different phrasings of the same intent — some formal, some casual. Include cases where the user doesn't explicitly name the skill or file type but clearly needs it. Throw in some uncommon use cases and cases where this skill competes with another but should win.

For the **should-not-trigger** queries (8-10), the most valuable ones are the near-misses — queries that share keywords or concepts with the skill but actually need something different. Think adjacent domains, ambiguous phrasing where a naive keyword match would trigger but shouldn't, and cases where the query touches on something the skill does but in a context where another tool is more appropriate.

The key thing to avoid: don't make should-not-trigger queries obviously irrelevant. "Write a fibonacci function" as a negative test for a PDF skill is too easy — it doesn't test anything. The negative cases should be genuinely tricky.

### Step 2: Review with the user

Present the eval set to the user for review using the HTML template: **`assets/eval_review.html`**

1. Read the template from `assets/eval_review.html`.
2. Replace **`__EVAL_DATA_PLACEHOLDER__`**, **`__SKILL_NAME_PLACEHOLDER__`**, **`__SKILL_DESCRIPTION_PLACEHOLDER__`** per the file’s instructions.
3. Open the filled HTML for the user to edit and export a finalized eval set.

### Step 3: Run the optimization loop

Warn that the loop may take time. From the create-agent-skill root:

```bash
python eval-harness/scripts/run_loop.py \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <model-id-for-this-session> \
  --max-iterations 3 \
  --verbose
```

The default `--max-iterations` is **3**. Most skills converge (or plateau) within three rounds, and longer loops tend to overfit the training split. Raise it only when you have a large eval set and clear evidence that iteration 3 was still improving.

Use the model id that matches how the user experiences triggering. The loop trains and tests descriptions, iterating with **`eval-harness/scripts/improve_description.py`** under the hood; reports are generated via **`eval-harness/scripts/generate_report.py`**.

### Step 4: Apply the result

Take **`best_description`** from the JSON output, update frontmatter, show before/after, and summarize scores.

---

## Package and present

If your environment exposes a **`present_files`**-style tool, package the skill:

```bash
python scripts/package_skill.py <path/to/skill-folder>
```

Point the user at the resulting **`.skill`** artifact for installation. Packaging only needs Python and a filesystem when run locally.

---

## Agent-specific execution

Behavior that depends on the host product (CLI flags, transcripts, browser vs static viewer, parallelism) is **not** duplicated here. Read **`adapters/<active_agent>/recipes.md`** for the adapter selected in **`config/active_agent`**.

---

## Reference files

**Agents** (specialized instructions—read when needed):

- **`agents/executor.md`** — Default dual-run executor template; supports `{{USER_INPUT}}` and `{{SKILL_CONTENT}}`
- **`agents/grader.md`** — Evaluate assertions against outputs
- **`agents/comparator.md`** — Blind A/B comparison between outputs
- **`agents/analyzer.md`** — Analyze why one version outperformed another

**JSON schemas** (under **`references/schemas/`**):

- **`evals.schema.json`**, **`eval_metadata.schema.json`**, **`grading.schema.json`**, **`benchmark.schema.json`**, **`feedback.schema.json`**, **`timing.schema.json`**, **`iteration.schema.json`**

**Phase map (commands A–F):** **`references/execution-contract.md`**

**Intro setup:** **`references/getting-started.md`**

---

## Core loop (summary)

- Understand what the skill is for
- Draft or edit the skill and **`evals/evals.json`**
- Run dual evaluation through the harness; capture timing and grades
- Aggregate benchmarks, open **`eval-harness/viewer/generate_review.py`**, collect feedback
- Improve and repeat
- Optimize description, then package when appropriate

Good luck.
