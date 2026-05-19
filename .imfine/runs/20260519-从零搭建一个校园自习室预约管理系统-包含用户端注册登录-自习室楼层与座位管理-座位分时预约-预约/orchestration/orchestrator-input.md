# Orchestrator Input

You are the only orchestration decision maker for this run.

You must coordinate independent native subagents from the current provider session.
Do not complete the full workflow by pretending one agent performed all roles.

## Run

- run id: 20260519-从零搭建一个校园自习室预约管理系统-包含用户端注册登录-自习室楼层与座位管理-座位分时预约-预约
- execution mode: true_harness
- project kind: existing_project

## Required Decision Output

Write `orchestration/orchestrator-session.json` as the single source of orchestration truth.

The file must:

- declare `decision_source=orchestrator_agent`
- declare `execution_mode=true_harness`
- declare `harness_classification=true_harness`
- define every planned `next_action`
- define every `agent_run`
- define explicit dependencies and parallel groups

You must:

- decide which roles to start
- use the current session's native subagent capability to dispatch independent agents
- keep QA, Review, Committer, and Archive as separate roles
- mark the run blocked if the current provider session cannot launch independent subagents

Runtime will only materialize what you write in that file and will only perform deterministic backend actions.
