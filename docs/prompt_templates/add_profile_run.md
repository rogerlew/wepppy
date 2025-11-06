# Add Profile Run

Use this template to add a new nightly profile test workflow and update the readme.

## Prompt

```
Add a new profile run workflow with the following details:

- **Title**: Profile Run - WEPP Reveg
- **Profile name**: daymet-reveg
- **Description**: "Small US WEPP Reveg Run with DAYMET climate"
- **Run time**: next available 10-minute slot before existing workflows

Tasks:
1. Create `.github/workflows/profile-run-[slug].yml` based on existing profile workflow patterns and the title (not the profile name)
2. Update `readme.md` Dev Server Nightly Profile Tests table with new entry (maintain chronological order by run time)
3. Set cron schedule to match the specified Pacific time (convert to UTC, accounting for daylight saving offset)
4. Use existing workflow structure (health check, wctl run-test-profile, artifact upload, redis cleanup)
```

## Notes

- Workflows run sequentially to avoid resource contention on self-hosted runners
- Current profile workflows occupy 04:30, 04:45, 04:55, 05:05, 05:15 AM PT
- Use specified intervals between runs or 15 minutes
- UTC cron times assume Pacific daylight saving (PT = UTC-7); adjust comment if standard time changes
- Workflow filename should match pattern: `profile-run-[descriptive-slug].yml`
- Badge URL in readme should match workflow filename exactly
