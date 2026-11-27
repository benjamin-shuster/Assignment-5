# ADR NNNN: the decision, as a short phrase

Status: Accepted
Date: 2026-11-27

## Context

What problem forces a decision, and what happens if nobody decides.

When at the exact same time, two requests are made to book the same room for overlapping times, the backend must ensure that only one booking is created and the other request is rejected with a `409 overlap` error. If nobody decides how to handle this situation, it could lead to inconsistent data in the database and unexpected behavior in the application.

## Options considered

1. First option: how it works, one advantage, one cost.
The first option is to use a database transaction with a `BEGIN IMMEDIATE` statement to lock the database for writing during the booking process. This ensures that only one request can modify the bookings at a time, preventing overlaps. The advantage of this approach is that it guarantees data consistency and prevents race conditions. The cost is that it may lead to increased wait times for users if multiple requests are made simultaneously, as they will have to wait for the lock to be released.
2. Second option: how it works, one advantage, one cost.
The second option is to implement application-level locking, where the backend checks for existing bookings before creating a new one and uses a mutex or similar mechanism to prevent concurrent modifications. The advantage of this approach is that it can be more flexible and may allow for better performance in some scenarios. The cost is that it requires additional complexity in the application code and may still be vulnerable to race conditions if not implemented correctly.
## Decision

What you chose, and the main reason.

I chose the first option of using a database transaction with a `BEGIN IMMEDIATE` statement to lock the database for writing during the booking process. The main reason for this decision is that it provides a straightforward and reliable way to ensure data consistency and prevent race conditions, which is critical for maintaining the integrity of the booking system.

## Consequences

What becomes easier, what becomes harder, and what someone must watch from now on.

As a result of this decision, it becomes easier to ensure that overlapping bookings are prevented and that the backend behaves predictably under concurrent requests. However, it may become harder to handle high traffic scenarios, as users may experience increased wait times due to the locking mechanism. From now on, it is important to monitor the performance of the booking system and consider implementing additional optimizations or scaling strategies if necessary to handle increased load while maintaining data integrity.
