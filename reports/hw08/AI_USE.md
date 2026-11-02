# AI_USE.md - HW8

1. What I used an AI assistant for, and what I did myself
I used AI to explain Kafka concepts (correlation IDs, consumer groups, offsets, partition keys) in simple terms, to help implement and fix the Part 1 worker and also the Part 2 Planner agent. I understood and tried to implement the Writer and reviewer agents based on planner by understanding it first, started the Docker services, collected the logs, and wrote the report.

2. An AI output that was wrong or unsuitable
For the Part 3 ordering test, the AI first suggested me to use a stand-in consumer way of implementation instead of using my real Writer agent. That meant the ordering evidence did not come from my actual system. I also nearly kept a report sentence that said Kafka topic names must avoid periods and underscores, which came from a Kafka warning message and was not a real rule.

3. How I detected the problem
I compared the work against the exact requirement, which asks for evidence from my own system, and saw that the stand-in did not match it. I checked the topic-name sentence against the actual warning in my terminal output.

4. What I changed and why it works now
I replaced the stand-in with two real Writer instances in one consumer group (writer.py with a name argument), and re-ran the no-key and key ordering runs so the data comes from the real pipeline. Now the ordering results (no key = out of order, entity_id key = in order) is what is expected.