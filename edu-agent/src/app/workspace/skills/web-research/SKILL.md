---
name: web-research
description: >
  Searches multiple web sources, synthesizes findings, and produces cited research reports.
  Use when the user asks to research a topic online, search the web, look something up,
  find current information, compare options, or produce a research report.
---

# Web Research Skill

## Available Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `tavily_search` | Search the web for current information on any topic. | Quick fact-checking, news, data, or initial discovery. |
| `tavily_research` | Perform comprehensive research on a given topic or question. | **Preferred** for most research tasks—gathers information from multiple sources and returns a detailed, synthesized response. Rate limit: 20 requests/min. |
| `tavily_extract` | Extract content from specific URLs. | When you need the raw page content (markdown/text) of one or more known URLs. |
| `tavily_crawl` | Crawl a website starting from a URL. | When you need to explore a site deeply with configurable depth/breadth. |
| `tavily_map` | Map a website's structure. | When you need a list of URLs under a base domain (e.g., documentation sections). |
| `tavily_skill` | Search documentation for any library, API, or tool. | When researching a specific library, API, or tool. Always pass the library name for best results. |

Please strictly follow the process below to conduct the research.

## Research Process

### Step 1: Analyze the Request and Choose a Strategy

- **Simple fact-finding or quick lookup** → Use `tavily_search` directly (1–2 queries).
- **Comprehensive research report** → Use `tavily_research` directly. It is optimized to gather and synthesize multi-source information into a detailed response.
- **Exploratory / multi-faceted investigation** → Create a research plan and delegate subtopics to parallel `Agent` subagents (see below).

### Step 2: Create and Save a Research Plan (for complex topics)

Before delegating to subagents:

1. **Create a research folder** to keep files organized:
   ```
   research_<topic_name>
   ```
2. **Break the question into 2–5 distinct, non-overlapping subtopics.**
3. **Write `research_<topic_name>/research_plan.md`** using `WriteFile`. Include:
   - Main research question
   - Subtopics (2–5)
   - Expected information per subtopic
   - Synthesis strategy

**Planning Guidelines:**
- Simple fact-finding: 1–2 subtopics
- Comparative analysis: 1 subtopic per comparison element (max 3)
- Complex investigations: 3–5 subtopics

### Step 3: Delegate to Research Subagents (optional, for complex topics)

For each subtopic in your plan:

1. **Use `Agent`** to spawn a research subagent with:
   - A clear, specific research question (no acronyms without explanation)
   - Instructions to save findings with `WriteFile` to `research_<topic_name>/findings_<subtopic>.md`
   - Budget: 3–5 web searches maximum per subagent

2. **Run up to 3 subagents in parallel** for efficiency.

**Subagent Prompt Template:**
```
Research: [SPECIFIC SUBTOPIC].
Use tavily_search and/or tavily_research to gather information.
After completing your research, use WriteFile to save findings to research_<topic_name>/findings_<subtopic>.md.
Include key facts, relevant quotes, and source URLs.
Use 3–5 searches maximum.
```

### Step 4: Synthesize Findings

After all subagents complete (or after `tavily_research` returns):

1. **Review findings**:
   - If subagents were used, list the research directory with `Shell` (`ls research_<topic_name>` or `dir research_<topic_name>`), then read each file with `ReadFile`.
2. **Synthesize** into a comprehensive response that:
   - Directly answers the original question
   - Integrates insights from all subtopics
   - Cites specific sources with URLs
   - Notes any gaps or limitations
3. **Write final report** (if requested) with `WriteFile` to `research_<topic_name>/research_report.md`.

## Best Practices

- **Prefer `tavily_research`** for most report-style requests—it handles multi-source synthesis automatically.
- **Use `tavily_search`** for quick, targeted lookups or when you need to verify a single fact.
- **Use `tavily_extract`** when you already have specific URLs and need the full page content.
- **Use `tavily_skill`** whenever the research involves a library, API, or tool; always include the library/tool name in the query.
- **Plan before delegating** — write `research_plan.md` first for complex topics.
- **Clear subtopics** — ensure each subagent has a distinct, non-overlapping scope.
- **File-based communication** — have subagents save findings to files, not return them inline.
- **Stop appropriately** — don't over-research; 3–5 searches per subtopic is usually sufficient.
