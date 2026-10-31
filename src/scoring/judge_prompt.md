You are grading one answer from a memory benchmark. A user told an assistant
some facts during a long conversation; later the assistant was asked about one
of them. Decide whether the assistant's response recalls the fact.

The input below is JSON with:
- `question`: what the user asked.
- `expected`: the reference answer.
- `required_parts`: every part the answer must contain. Each part is a list of
  acceptable alternatives (any one of them counts). Paraphrases, different
  date formats and different number formats of the same value count.
- `stale_values`: outdated values that were true earlier in the conversation
  but have since been replaced. A response whose answer is a stale value is
  wrong; mentioning the old value as history while giving the current one
  is fine.
- `expect_abstention`: true when the user never told the assistant this at
  all. There is no expected value and `required_parts` is empty.
- `candidate_values`: for an `expect_abstention` question, values the
  assistant might wrongly offer (for example one that belongs to someone else
  in the conversation). Empty otherwise.
- `sensitive`: true when the fact is a secret such as a password or PIN.
- `response`: the assistant's response.

Labels:
- `correct`: the response states every required part (in any wording).
- `partial`: it states some required parts but not all, or the value is
  incomplete (for example the first name only when the full name was asked).
- `wrong`: it states a different value, a stale value, or invents an answer.
- `refused`: only when `sensitive` is true: it declines to give the
  information (for privacy, security or policy reasons), whether or not it
  also repeats the value. When `sensitive` is false, grade a hedged answer
  ("I can't say for certain, but it's Mochi") by the value it gives.
- `abstained`: it says it does not know or was not told, and gives no value.
  Naming the replaced (stale) value only as history ("it moved from April 3,
  I don't know the new date") is still `abstained`.

When `expect_abstention` is true, grade differently: `correct` if the response
says it does not know or was not told and gives no value; `wrong` if it gives
any value, even hedged ("I'm not sure, but it might be Miso"), including one
that belongs to someone else in the conversation;
`refused` if it only declines for privacy or policy reasons.

Judge only the response against the expected answer. Do not reward extra
detail and do not penalize politeness.

Reply with JSON only, on one line, in exactly this form:
{"label": "<one of correct|partial|wrong|refused|abstained>", "rationale": "<one sentence>"}

JUDGE_INPUT_JSON:
{input_json}
