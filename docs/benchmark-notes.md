# LAA Benchmark Notes

These notes explain how to read the small benchmark used in the repository.

## What the benchmark measures

The current benchmark compares a naive baseline against the agent routing layer on a compact set of hand-labeled examples.

It focuses on:

- noise and filler rejection
- duplicate suppression
- subtitle routing
- avatar routing
- summary routing
- expectation matching for the selected cases

## What it does not measure

The benchmark is not a full product evaluation.

It does not directly measure:

- end-to-end ASR quality in real classrooms
- latency under sustained live traffic
- multilingual accuracy across full lectures
- avatar comprehensibility for every segment type
- user outcomes from accessibility testing

## How to use the results

Treat the benchmark as a regression check for routing logic, not as a final accessibility claim.

A good use case is:

1. change agent rules
2. rerun the benchmark
3. compare routing behavior before and after
4. inspect recent decisions and reasons when a case changes

## Recommended next steps

- add longer multilingual lecture samples
- add failure cases from real microphone sessions
- track latency and refresh timing alongside routing accuracy
