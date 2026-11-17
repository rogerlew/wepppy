# CILogon account correctness review gate

- **Reviewer**: independent `account_contract_correctness`, 2026-11-17.
- **Candidate**: task branch after accepted checkpoint `874de621c`.
- **User outcome**: CILogon accounts remain separate; verified Google/GitHub emails select shared accounts; new passwords require mailbox setup; existing local access remains; account pages work at mobile widths.
- **Local verdict**: source findings dispositioned; see [independent implementation review](20261117_correctness_implementation_review.md).
- **Release verdict**: HOLD for [validation gates](validation.md), without production deployment.

The original unassessed template is replaced by the actual review. The independent artifact covers absent/malformed/legacy/new account states, failed mail, wrong/expired/replayed tokens, unavailable provider email, shared and separate projects, recovery, nullable-email consumers, and review findings. Generated signed-token/mail-sink/ORM/browser evidence is retained; real provider/SMTP/PostgreSQL and deployed browser workflows remain separately unproven. No model-result artifact claim is made.
