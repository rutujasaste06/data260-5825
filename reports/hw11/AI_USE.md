# AI USE

## 1. What I used an AI assistant for, and what I did myself
I used AI to help me understand the assignment, the fictional fixtures. I tried to write the policy and the labels and set the SEC user_agent to my own email. 

## 2. An AI output that was wrong or unsuitable
when I asked Muse to send the ORVN alert again, it re-posted the alert text from its memory instead of calling the decide step of watch.py.

## 3. How I detected the problem
I looked at the trace for the ORVN effect and the Muse activity list. The trace showed one SendToUser effect and no decide step for the resend, so the repeat came from the chat and not from the script.

## 4. What changed and why it works now
I did not change the script. I wrote the finding into the report (Part 4.4 and Part 7): the script ledger stops a second effect, but the chat can still repeat an alert, so a rule that a resend request is not a new alert, and a check of effects instead of chat text, are needed before an unattended release.
