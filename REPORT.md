# Assignment 5 report

Name: Benjamin Shuster
Agent tool and version Antigravity CLI v1.5.18

Answer each question in two to five sentences, below the question, unless it asks for a
table. Point to commits, files, tests or rule IDs where you can.

## 1. Clarify (Part 3)

How many questions did the agent list? Which one, if guessed wrong, would have changed
the backend's behavior the most, and what did you decide?

The agent listed 10 questions. The question that would have changed the backend's behavior the most if guessed wrong was "What should the backend do when the daily limit is exceeded?" I decided that when the daily limit is exceeded, the backend should return a 422 status code, as this aligns with the existing error handling for invalid requests and maintains consistency in the API's response structure.

## 2. Tests before the lock (Part 4)

Name one weak test you found before the lock and how you fixed it. Did any locked test
turn out to be wrong later? If so, which test, which rule, and why.

While not exactly weak, I noticed the times were being stored as strings like "10:00" and "11:00", which could lead to incorrect comparisons between timezones.
I decided not to change the tests to use datetime objects, as the spec does not require timezone handling - so that would have been a change outside the spec.

## 3. The plan (Part 5)

What did you reject from the plan, or add to "Not in this change", and why?

Mainly out of scope things like auth and adding external dependencies.
These were also not in the spec, and would have been unnecessary for the assignment / out of scope.

## 4. Review findings (Part 7)

One row for every finding in `evidence/review.md` and `evidence/contract-check.md`.

| #   | Agent | Finding, in a few words | Fixed (commit SHA) or rejected (reason) |
| --- | ----- | ----------------------- | --------------------------------------- |
| 1   |   Review    |         R7: Concurrent requests can create overlapping bookings due to non-atomic transactions.                |    451bfd83c7c7bfb3bd51d9fbb6895a3589cf6c2b                                     |
| 2   |  Review     |          R2, R6, R8, R9: Oversized integer inputs cause unhandled exceptions and HTTP 500 errors.               |             451bfd83c7c7bfb3bd51d9fbb6895a3589cf6c2b                            |
| 3   |   Contract Check    |           daily_limit error code exists in the frontend and 7 D1 but not in the backend or spec.              |                  Rejection - enforcing a daily limit would contradict 4–6 by rejecting otherwise valid requests.                       |

## 5. The spec change (Part 8)

Did the contract checker, or any earlier step, notice that the page already handles an
error code the spec did not define? Why does a change go spec, then test, then code, in
three commits?

## 6. Where the lock stops (Part 4)

Name one way an agent could still change a locked test despite your deny rule, and what
in this assignment would catch it.

## 7. Legacy parser (Part 10)

Which odd behaviors did you pin? Did the agent's first refactor change any behavior, and
how did you find out? Before fixing one of these bugs for real, what would you check?

## 8. The agent team

What did giving each agent one job and its own tools buy you? Name one thing that went
wrong with an agent and how you caught it.

## Screenshot

`evidence/page.png` shows the page with at least one booking made through your backend.
