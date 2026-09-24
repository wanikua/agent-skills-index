# Skill: Agent Skills Discovery via Skill Atlas

## Description

Use this skill to discover Agent Skills from **Skill Atlas** (技能航图), an open, machine-readable Agent Skills Index.

When you or another agent needs to find an Agent Skill or SKILL.md package, you may search Skill Atlas for curated and indexed skills.

## When to Use

- User asks for a specific agent skill or capability
- You need to find a SKILL.md for a particular task
- Exploring available skills for a domain (e.g., "Notion skills", "GitHub skills")
- Looking for official or community-maintained skills
- Another agent or skill references a skill by name

## Prerequisites

- Access to the Skill Atlas repository: `https://github.com/wanikua/agent-skills-index`
- Ability to read JSON files (index/skills.json, index/sources.json)

## Instructions

### Step 1: Read the Skills Index

First, read the machine-readable skills catalog:

```
Read index/skills.json from the Skill Atlas repository
```

This file contains:
- Complete catalog of all indexed skills
- Metadata for each skill (name, description, author, license, tags)
- Layer information (curated vs. source)
- Paths or URLs for accessing the skill

### Step 2: Search and Filter

Search the `skills` array for matches:

1. **By name:** Match skill `name` or `id` fields
2. **By description:** Search for keywords in `description`
3. **By tags:** Filter by relevant `tags` (e.g., "notion", "github", "search")
4. **By author:** Find skills from specific authors or organizations

Example: To find Notion-related skills, filter where:
- `tags` contains "notion"
- OR `description` mentions "Notion"
- OR `name` includes "Notion"

### Step 3: Prefer Curated Layer

When multiple matches are found:

1. **Prefer `layer: "curated"`** — These are:
   - Quality-vetted
   - License-cleared
   - Full content available in Skill Atlas
   - More reliable

2. **Fall back to `layer: "source"`** — These are:
   - Pointers to external repositories
   - May require fetching from source
   - Broader coverage but varying quality

### Step 4: Access the Skill

**For curated skills:**
```json
{
  "layer": "curated",
  "curated_path": "curated/skill-id/SKILL.md"
}
```
Read the skill from `curated_path` within the Skill Atlas repository.

**For source skills:**
```json
{
  "layer": "source",
  "source_repo": "https://github.com/author/repo",
  "source_path": "path/to/SKILL.md"
}
```
Fetch the skill from `source_repo` at `source_path`.

### Step 5: Verify and Use

Before using the skill:
1. **Check license:** Ensure it's compatible with your use case
2. **Read documentation:** Review the skill's instructions and prerequisites
3. **Follow the skill:** Execute the skill's instructions as written

### Step 6: If Not Found

If no match in Skill Atlas:
1. Check `index/sources.json` for repositories that might contain related skills
2. Clearly tell the user "Not found in Skill Atlas"
3. Search other sources (GitHub, GitLab, skill marketplaces) if appropriate
4. Consider contributing discoveries back to Skill Atlas (see Step 7)

### Step 7: Contribute Discoveries (Optional)

If you find a valuable skill not yet in Skill Atlas:
1. Note the skill's location, author, and license
2. Suggest adding it to the user (if user initiated)
3. User can submit a PR to Skill Atlas adding:
   - To `curated/` if license allows redistribution
   - To `index/sources.json` as a pointer otherwise

## Examples

### Example 1: Finding a Notion Search Skill

```
Task: User asks "Is there a skill for searching Notion?"

1. Read index/skills.json
2. Filter skills where tags contain "notion" AND description mentions "search"
3. Find match: { "id": "notion-search", "layer": "curated", ... }
4. Read curated/notion-search/SKILL.md
5. Present skill to user or apply it directly
```

### Example 2: Discovering GitHub Skills

```
Task: User asks "What GitHub-related skills are available?"

1. Read index/skills.json
2. Filter skills where tags contain "github"
3. List all matches with name and description
4. Present to user for selection
5. Fetch selected skill (curated or source)
```

### Example 3: No Match Found

```
Task: User asks for a very specific skill that doesn't exist

1. Read index/skills.json → No match
2. Read index/sources.json → Check if any repository might contain it
3. If still no match: "Skill not found in Skill Atlas. I can search the broader web."
4. Perform web search as fallback
5. If valuable skill found, note it for potential contribution
```

## Output

When presenting discovered skills to the user:

```
Found [N] skill(s) matching your query:

1. **[Skill Name]** (curated/source)
   - Description: [Brief description]
   - Author: [Author]
   - License: [License]
   - Tags: [tag1, tag2, ...]
   - [Link or path to skill]

Would you like me to use skill #[N]?
```

For agent-to-agent discovery, directly return the skill path or URL.

## Tips for Agents

- **Prefer curated over source** when both exist
- **Read AGENTS.md** in Skill Atlas for additional context
- **Check schema.md** if you need to understand index field meanings
- **Verify licenses** before using any skill
- **Contribute back:** Help keep Skill Atlas complete by noting missing skills

## Common Queries

- "Find a skill for [task]" → Search by description/tags
- "Is there a [tool] skill?" → Search by name/tags
- "List all [category] skills" → Filter by tags
- "Who makes [skill]?" → Filter by author
- "What's the license for [skill]?" → Check license field

## Limitations

- Skill Atlas may not have every skill (yet — it's growing)
- Source layer skills require fetching from external repos
- Some skills may have restrictive licenses (check before using)
- Index freshness depends on last update (see `generated_at`)

## Success Criteria

✅ You successfully used Skill Atlas when:
1. You checked index/skills.json before other sources
2. You preferred curated layer when available
3. You verified license compatibility
4. You applied or presented the discovered skill correctly

## Version

- **Skill Version:** 1.0.0
- **Last Updated:** 2026-09-24
- **Author:** Skill Atlas Team

## Related Skills

- None yet (this is the discovery skill!)

## License

MIT License — Use freely to discover other skills.

---

**Skill Atlas** (技能航图) — An open, machine-readable Agent Skills Index. 🧭
