Extract structured information from the KEP README body.

Identify grounded, high-value information units and classify each span by its semantic role.

Follow the output structure shown in the examples exactly.
Do not add any explanation, commentary, or extra text.

Core rules:
1. Extract only information explicitly supported by the input text.
2. Use exact source text for each extraction. Do not paraphrase, summarize, rewrite, translate, or merge distant spans.
3. Each extraction must represent one atomic information unit.
4. A chunk may produce zero, one, or many extractions.
5. Output extractions in the order they appear in the text.
6. Do not infer cross-section or cross-document relations.
7. Prefer the smallest complete span that fully expresses the information unit.
8. If a bullet item is itself a complete information unit, extract that bullet item as one extraction.
9. Do not output duplicate extractions for the same source span.
10. Ignore table of contents, markdown formatting, checklist boxes, and section headers by themselves.

Classification rule:
Section headings are only weak cues. Classify by the semantic role of the span itself, not by the title of the section it appears in.
If heading context is provided, use it only as weak disambiguating context for nearby spans.
Do not extract a span only because the heading suggests a class.
Do not let the heading override the literal meaning of the span.
When the span text and the heading context disagree, trust the span text.
If the heading is broad but the span is specific, classify the span by its own specific semantic role.
A Summary section may contain summary, goal, or design_decision spans.
A Post-GA or Optional Future Extensions section may contain future_work rather than non_goal.

Extraction classes:

1. summary
Use for spans that directly summarize what the KEP is proposing.
Use this for concise “what this KEP is about” content, not for goals, not for implementation details.

2. motivation
Use for spans that explain why the KEP is needed, what problem exists, or why the current situation is insufficient.
Use this for “why”, not “what outcome” and not “how it works”.

3. goal
Use for explicit intended outcomes or target results of the KEP.
Use this for statements of what the KEP wants to achieve.

4. non_goal
Use for spans that explicitly state what is out of scope for the current KEP.
Use this when the text clearly excludes something from the proposal scope.

5. design_decision
Use for concrete solution content: proposal definition, mechanism, workflow, API behavior, component behavior, compatibility behavior, rollout behavior, upgrade behavior, version skew behavior, dependency handling, monitoring design, scalability design, troubleshooting design, or other implementation details.

For design_decision, set attributes.category to one of the following:

- proposal_definition
  Use when the span defines the proposal at a high level: what the proposed mechanism or object is, what concept is being introduced, or what the proposal standardizes or establishes.

- workflow
  Use when the span describes a sequence of steps, control flow, interaction flow, lifecycle flow, or how components/processes work together over time.

- api_change
  Use when the span describes an API-level change: new fields, renamed fields, new resources, versioned API behavior, schema restrictions, request/response behavior, or endpoint/interface changes.

- component_change
  Use when the span describes behavior or implementation changes in a specific Kubernetes component, controller, scheduler, kubelet, apiserver, webhook, or other concrete system component.

- compatibility
  Use when the span explains compatibility expectations or behavior across existing systems, clients, resources, formats, or prior behavior, but is not specifically about upgrade flow or version skew policy.

- rollout
  Use when the span describes staged enablement, feature-gated rollout, alpha/beta/GA rollout mechanics, progressive adoption, or how the feature will be introduced operationally.

- upgrade_strategy
  Use when the span explains how upgrades, downgrades, rollback, re-enable behavior, or migration between old and new behavior should work.

- version_skew_strategy
  Use when the span explains how different versions of components, clients, servers, resources, or APIs are expected to interoperate across version skew.

- dependency
  Use when the span describes required external systems, required services, prerequisite components, or explicit dependencies between parts of the system.

- monitoring
  Use when the span describes metrics, observability signals, SLI/SLO-related signals, health indicators, or how operators can detect whether the feature is working.

- scalability
  Use when the span describes scale limits, size/count thresholds, latency targets, storage bounds, resource consumption limits, throughput expectations, or scale behavior.

- troubleshooting
  Use when the span describes failure diagnosis, playbook-like guidance, failure reaction, debugging guidance, or what to do when something goes wrong.

- implementation_detail
  Use when the span contains concrete implementation-specific design detail that does not fit the categories above, such as internal handling logic, algorithm choice, or code-path behavior.

- other
  Use only if the span is clearly a design_decision but does not fit any category above.

6. user_story
Use for a user- or actor-centered scenario that describes who needs something, in what situation, and why.
Typical pattern: “As a ..., I want ..., so that ...”

7. definition
Use for explicit definitions of terms, concepts, roles, or artifacts.

For definition, you may set attributes.definition_type to one of:

- term
  Use for a glossary-like term, abbreviation, or named concept being defined.

- role
  Use for a defined actor, responsibility, or organizational role.

- artifact
  Use for a defined object, file, resource, API object, document type, or system artifact.

- other
  Use only if the span is clearly definitional but does not fit the above.

8. future_work
Use for explicitly deferred future extensions, post-GA tasks, backlog items, or later work that is not part of the current KEP scope.

For future_work, you may set attributes.horizon to one of:

- post_ga
  Use when the text explicitly says the work belongs after GA or after the current graduation.

- future_extension
  Use when the text describes a possible future capability, optional future extension, or later enhancement.

- backlog
  Use when the text refers to queued follow-up work, task lists, or deferred items without a strong post-GA framing.

- other
  Use only if the span is clearly future_work but none of the above fits.

9. risk
Use for explicit risks, caveats, limitations, failure modes, negative consequences, or safety concerns.

10. mitigation
Use for an explicit safeguard, fallback, control, or risk-reduction measure.

11. test_case
Use for explicit tests, validation items, or verification requirements.

For test_case, set attributes.test_type to one of:

- prerequisite_update
  Use for prerequisite or preparatory testing changes that must happen before broader testing is valid.

- unit_test
  Use for unit-level validation of isolated logic or a specific package/component.

- integration_test
  Use for integration-level testing across components, APIs, storage, conversions, or end-to-end behavior within the system under controlled integration conditions.

- e2e_test
  Use for full end-to-end tests that exercise the feature in a realistic cluster workflow.

- conformance_test
  Use for tests intended to be promoted to, or described as part of, Kubernetes conformance coverage.

- manual_validation
  Use for explicitly manual checks, manual rollout checks, or human-run validation procedures.

- benchmark_or_scale
  Use for scale tests, load tests, latency checks, or performance/scalability validation.

- other
  Use only if the span is clearly a test_case but none of the above fits.

12. graduation_criterion
Use for explicit conditions that must be satisfied for promotion to a maturity stage.

For graduation_criterion, set attributes.stage to one of:

- alpha
  Use when the condition is explicitly tied to alpha readiness or alpha behavior.

- beta
  Use when the condition is explicitly tied to beta readiness or beta promotion.

- ga
  Use when the condition is explicitly tied to GA readiness, GA promotion, or general availability.

- stable
  Use when the text explicitly uses “stable” rather than “GA”, or when stable is the stated maturity target.

- other
  Use only if the span is clearly a graduation criterion but the stage is not one of the above.

13. drawback
Use for explicit disadvantages, tradeoffs, burdens, or downsides of the proposal itself.
Do not use drawback for operational risk or failure mode; use risk for those.

14. alternative
Use for an alternative approach, rejected option, competing design, or another path considered instead of the proposed one.

15. implementation_history
Use for implementation timeline or history items such as dated events, release milestones, or stage transitions.

For implementation_history, you may set:

- attributes.marker
  Use this for the explicit date, release, or stage label if one is clearly present in the text.

- attributes.marker_type
  Use one of:
  - release
    Use when the marker is a Kubernetes release or version-like milestone such as 1.32, v1.34, Release 1.20.
  - date
    Use when the marker is an explicit calendar date.
  - stage
    Use when the marker is a named lifecycle stage such as alpha, beta, or stable.
  - other
    Use only if a marker is present but none of the above fits.

Boundary guidance:
- summary = what the KEP is
- motivation = why it is needed
- goal = what outcome it wants to achieve
- non_goal = what it explicitly does not aim to do
- design_decision = how it works
- user_story = who needs what in which scenario
- definition = what a term or concept means
- future_work = later work, not part of the current committed scope
- risk = what could go wrong or what limitation exists
- mitigation = how a risk is reduced
- test_case = how the proposal is validated
- graduation_criterion = what must be true for promotion
- drawback = downside of the proposal itself
- alternative = another approach considered
- implementation_history = historical or milestone event

If a span could fit multiple classes, choose the most specific semantic role.

Attribute rules:
- Include an attributes object for every extraction.
- Use only the attribute names and values defined above.
- Do not invent attribute values.
- If no attribute applies, use an empty attributes object.
- Keep attribute values concise.
- For optional attributes, only set them when the text provides enough evidence.
