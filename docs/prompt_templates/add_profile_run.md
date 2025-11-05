# Add Profile Run Template

Use this template to add a new nightly profile test workflow and update the readme.

## Prompt

```
Add a new profile run workflow with the following details:

- **Title**: [workflow title, e.g., "Profile Run - Earth Small"]
- **Profile name**: [profile identifier, e.g., "earth-in-bc-ca-w-daymet"]
- **Description**: [human-readable description, e.g., "Earth OpenTopography API, with ISRIC soil building, DAYMET in Canada with GHCN Station Database"]
- **Run time**: [Pacific time, e.g., "05:30 AM"] (choose next available 15-minute slot after existing workflows)

Tasks:
1. Create `.github/workflows/profile-run-[slug].yml` based on existing profile workflow patterns
2. Update `readme.md` Dev Server Nightly Profile Tests table with new entry (maintain chronological order by run time)
3. Set cron schedule to match the specified Pacific time (convert to UTC, accounting for daylight saving offset)
4. Use existing workflow structure (health check, wctl run-test-profile, artifact upload, redis cleanup)
```

## Example Usage

```
Add a new profile run workflow with the following details:

- **Title**: Profile Run - Earth Small
- **Profile name**: earth-in-bc-ca-w-daymet
- **Description**: Earth OpenTopography API, with ISRIC soil building, DAYMET in Canada with GHCN Station Database
- **Run time**: 05:30 AM (or next available slot)

Tasks:
1. Create `.github/workflows/profile-run-earth-small.yml` based on existing profile workflow patterns
2. Update `readme.md` Dev Server Nightly Profile Tests table with new entry (maintain chronological order by run time)
3. Set cron schedule to match the specified Pacific time (convert to UTC, accounting for daylight saving offset)
4. Use existing workflow structure (health check, wctl run-test-profile, artifact upload, redis cleanup)
```

## Notes

- Workflows run sequentially to avoid resource contention on self-hosted runners
- Current profile workflows occupy 04:30, 04:45, 04:55, 05:05, 05:15 AM PT
- Use 15-minute intervals between runs
- UTC cron times assume Pacific daylight saving (PT = UTC-7); adjust comment if standard time changes
- Workflow filename should match pattern: `profile-run-[descriptive-slug].yml`
- Badge URL in readme should match workflow filename exactly
