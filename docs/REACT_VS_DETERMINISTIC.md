# ReAct vs Deterministic Patterns in LangGraph

**Version**: 1.0  
**Last Updated**: 2025-11-10  
**Status**: Architecture Guide

---

## Table of Contents

1. [Overview](#overview)
2. [Pattern Comparison](#pattern-comparison)
3. [When to Use Each Pattern](#when-to-use-each-pattern)
4. [Decision Matrix](#decision-matrix)
5. [Integration Scenarios](#integration-scenarios)
6. [Intelligent Router Architecture](#intelligent-router-architecture)
7. [Routing Scenarios](#routing-scenarios)
8. [Implementation Details](#implementation-details)
9. [Best Practices](#best-practices)

---

## Overview

This document provides comprehensive guidance on choosing between ReAct (Reasoning and Acting) patterns and deterministic workflows in LangGraph applications, specifically for PAN-OS firewall automation.

### What is ReAct?

**ReAct** is an agentic pattern where the LLM:

- **Reasons** about the current state and goal
- **Acts** by calling tools to gather information or make changes
- **Observes** results and decides next actions
- **Loops** until the task is complete

```text
User Input → Agent Reasoning → Tool Selection → Tool Execution →
Result Observation → Agent Reasoning → ... → Final Response
```

### What are Deterministic Workflows?

**Deterministic workflows** are predefined sequences of steps that execute in order:

- Steps are defined upfront in code
- Execution follows a fixed path
- LLM may evaluate results but doesn't choose tools
- Similar to Ansible playbooks or CI/CD pipelines

```text
User Input → Workflow Lookup → Step 1 → Step 2 → Step 3 → ... → Summary
```

---

## Pattern Comparison

### Overview Table

| Aspect | Autonomous (ReAct) | Deterministic (Workflow) |
|--------|-------------------|-------------------------|
| **Control Flow** | LLM decides next action | Predefined step sequence |
| **Flexibility** | High - can adapt to any scenario | Medium - follows workflow definition |
| **Predictability** | Variable - depends on LLM reasoning | High - same steps every time |
| **Auditability** | Moderate - log of tool calls | Excellent - known workflow execution |
| **Error Recovery** | LLM can retry/adapt | Stops or continues based on config |
| **Human Approval** | Optional via tools | Built-in approval gates |
| **Tool Access** | All tools available | Only tools in workflow steps |
| **Token Usage** | High - full reasoning each turn | Lower - evaluation only |
| **Latency** | Variable - depends on decisions | Predictable - fixed steps |
| **Cost** | Higher - more LLM calls | Lower - fewer LLM calls |
| **Best For** | Exploration, debugging, ad-hoc | Production, compliance, repeatability |

### Execution Flow Comparison

#### ReAct Pattern Flow

```text
┌─────────────────────────────────────────────────┐
│           Autonomous Graph (ReAct)              │
│  ┌─────────────────────────────────────────┐   │
│  │  1. User Input (Natural Language)       │   │
│  └─────────────────┬───────────────────────┘   │
│                    │                            │
│                    ▼                            │
│  ┌─────────────────────────────────────────┐   │
│  │  2. Agent Node (LLM with tools)         │   │
│  │     - Receives: messages history        │   │
│  │     - Claude Sonnet 4.5 reasoning       │   │
│  │     - Tool binding (all 34 tools)       │   │
│  │     - Returns: Response + tool calls    │   │
│  └─────────────────┬───────────────────────┘   │
│                    │                            │
│                    ▼                            │
│            ┌───────────────┐                    │
│            │  Tool calls?  │                    │
│            └───────┬───────┘                    │
│                    │                            │
│          ┌─────────┴──────────┐                 │
│          │ Yes                │ No              │
│          ▼                    ▼                 │
│  ┌────────────────┐    ┌──────────────┐        │
│  │  3. Tools Node │    │  5. END      │        │
│  │  Execute tools │    │  (Response)  │        │
│  │  in parallel   │    └──────────────┘        │
│  └────────┬───────┘                            │
│           │                                     │
│           │ 4. Tool results                     │
│           │    added to messages                │
│           └──────────┐                          │
│                      │                          │
│                      ▼                          │
│           ┌────────────────────┐                │
│           │  Loop back to      │                │
│           │  Agent Node (2)    │                │
│           └────────────────────┘                │
└─────────────────────────────────────────────────┘
```

**Example:**

```text
User: "Create address objects for web servers 10.1.1.1 through 10.1.1.5"

Turn 1:
  Agent → Analyzes: "Need to create 5 address objects"
  Agent → Calls: address_create() for first server
  Tools → Returns: "✅ Created address: web-server-1"

Turn 2:
  Agent → Calls: address_create() for remaining 4 servers
  Tools → Returns: "✅ Created" for each

Turn 3:
  Agent → Calls: address_list() to verify
  Tools → Returns: List including new addresses

Turn 4:
  Agent → Confirms all created successfully
  Agent → Returns: "Created 5 address objects for web servers"
  END
```

#### Deterministic Workflow Flow

```text
┌──────────────────────────────────────────────────────┐
│        Deterministic Graph (Workflow Executor)       │
│  ┌──────────────────────────────────────────────┐   │
│  │  1. User Input: "workflow: <name>"           │   │
│  └────────────────┬─────────────────────────────┘   │
│                   │                                  │
│                   ▼                                  │
│  ┌──────────────────────────────────────────────┐   │
│  │  2. Load Workflow Definition                 │   │
│  │     - Lookup in WORKFLOWS dict               │   │
│  │     - Extract steps list                     │   │
│  │     - Initialize state                       │   │
│  └────────────────┬─────────────────────────────┘   │
│                   │                                  │
│                   ▼                                  │
│  ┌──────────────────────────────────────────────┐   │
│  │  3. Execute Each Step Sequentially           │   │
│  │     - Step 1: tool_call                      │   │
│  │     - Step 2: tool_call                      │   │
│  │     - Step 3: approval (HITL)                │   │
│  │     - Step 4: tool_call                      │   │
│  │     - LLM evaluates each result              │   │
│  └────────────────┬─────────────────────────────┘   │
│                   │                                  │
│                   ▼                                  │
│  ┌──────────────────────────────────────────────┐   │
│  │  4. Format Summary                           │   │
│  │     - Steps executed: 4/4                    │   │
│  │     - Success/failure counts                 │   │
│  │     - Detailed results                       │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

**Example:**

```text
User: "workflow: web_server_setup"

Step 1/4: Create web server address
  Tool: address_create(name="web-server-1", value="10.10.1.100")
  Result: ✅ Created address object
  LLM: {"decision": "continue", "success": true}

Step 2/4: Create HTTP service
  Tool: service_create(name="custom-http", port="8080")
  Result: ✅ Created service object
  LLM: {"decision": "continue", "success": true}

Step 3/4: Approval gate
  Type: approval
  PAUSED - Waiting for approval...
  [User approves]

Step 4/4: Create service group
  Tool: service_group_create(name="web-services", members=[...])
  Result: ✅ Created service group
  LLM: {"decision": "continue", "success": true}

Summary:
  ✅ Workflow complete: 4/4 steps successful
```

---

## When to Use Each Pattern

### Use ReAct (Autonomous) When

#### 1. Exploration & Discovery

- Unknown problem space requiring investigation
- User needs help figuring out *what* to do
- Multiple valid solution paths exist

**Examples:**

- "Show me all address objects and groups"
- "Find unused security policies"
- "Investigate why traffic is being blocked"

#### 2. Ad-hoc Operations

- One-off tasks that don't follow a pattern
- Quick fixes or temporary changes
- Tasks that vary significantly each time

**Examples:**

- "Create a new address for server X"
- "Quickly add this IP to the DMZ group"
- "Delete all objects with tag 'temporary'"

#### 3. Complex Problem-Solving

- Tasks requiring strategic thinking
- Situations where next steps depend on current state
- Need to adapt based on findings

**Examples:**

- "Set up microsegmentation for database tier"
- "Optimize our security policy rulebase"
- "Troubleshoot connectivity issue between zones"

#### 4. Learning/Training

- Users exploring the firewall
- Understanding configuration
- "What if" scenarios

**Examples:**

- "What objects reference this address group?"
- "How would I create a security policy for...?"
- "Explain the current NAT configuration"

#### 5. Adaptive Requirements

- Requirements not fully known upfront
- Need LLM to make contextual decisions
- Want agent to explore and recommend

**Examples:**

- "Improve security posture for DMZ"
- "What's the best way to allow this traffic?"
- "Help me design a policy for this use case"

### Use Deterministic (Workflows) When

#### 1. Production Operations

- Repeatable processes executed regularly
- Standard operating procedures
- Known sequence of steps

**Examples:**

- Server onboarding
- Network segment provisioning
- Scheduled policy updates
- Application decommissioning

#### 2. Compliance & Audit

- Need exact record of steps executed
- Regulatory requirements for change tracking
- Must follow specific procedures
- Require approval gates

**Examples:**

- PCI-DSS compliant changes
- SOX-regulated environments
- Change management workflows
- Audit trail requirements

#### 3. Repeatable Operations

- Same task performed multiple times
- Batch processing with known structure
- Multiple environments (dev/staging/prod)

**Examples:**

- Onboard 50 new servers
- Create security policies for each app
- Set up identical configs per environment

#### 4. Critical Operations

- Changes requiring human approval
- Multi-step processes with dependencies
- Operations with rollback requirements
- High-risk changes

**Examples:**

- Production firewall changes
- Policy modifications affecting critical apps
- NAT configuration changes
- Commit operations

#### 5. Team Collaboration

- Codifying tribal knowledge
- Ensuring consistency across operators
- Onboarding new team members
- Sharing best practices

**Examples:**

- Standard web server setup
- Database tier provisioning
- VPN user onboarding
- Decommissioning checklist

---

## Decision Matrix

Use this matrix to quickly determine which pattern to use:

| Question | ReAct | Deterministic |
|----------|-------|---------------|
| Do I know all steps upfront? | ❌ No → ReAct | ✅ Yes → Workflow |
| Will steps vary based on context? | ✅ Yes → ReAct | ❌ No → Workflow |
| Need human approval gates? | ⚠️ Via tool | ✅ Built-in → Workflow |
| Cost sensitive? | ❌ Higher cost | ✅ Lower cost → Workflow |
| Need detailed audit trail? | ⚠️ Moderate | ✅ Excellent → Workflow |
| Users are non-technical? | ✅ NL interface → ReAct | ⚠️ Need workflow names |
| Time-critical execution? | ❌ Variable latency | ✅ Predictable → Workflow |
| Requires adaptability? | ✅ High → ReAct | ❌ Low → Workflow |
| Error recovery needs creativity? | ✅ Yes → ReAct | ❌ No → Workflow |
| Same task run repeatedly? | ❌ No → ReAct | ✅ Yes → Workflow |

**Legend:**

- ✅ Strong indicator for this pattern
- ❌ Strong indicator against this pattern
- ⚠️ Possible but not optimal

---

## Integration Scenarios

Rather than choosing exclusively between patterns, the most powerful approach is to **integrate** them. Here are proven integration patterns:

### Pattern 1: ReAct Calls Workflows

The autonomous agent discovers it needs to run a standard workflow and delegates to deterministic execution.

```text
User: "Set up new web server in DMZ"
  ↓
ReAct Agent analyzes request
  ↓
Agent: "This matches our standard DMZ setup workflow"
  ↓
Agent calls workflow_execute("dmz_web_server_setup", params={...})
  ↓
Deterministic workflow executes with approval gates
  ↓
Result returned to user
```

**Benefits:**

- LLM decides *which* workflow to use
- Workflow ensures correct execution
- Combines flexibility with predictability
- Best of both worlds

**Implementation:**

- Add `workflow_execute` tool to autonomous agent
- Tool invokes deterministic graph
- Results flow back to ReAct conversation

### Pattern 2: Workflow Contains ReAct Steps

A deterministic workflow includes steps that require LLM reasoning.

```python
workflow = {
    "steps": [
        {"type": "tool_call", "tool": "address_create", ...},  # Deterministic
        {"type": "agent_task", "prompt": "Analyze security posture and recommend policy"},  # ReAct
        {"type": "approval", "message": "Review recommendations"},  # Gate
        {"type": "tool_call", "tool": "security_policy_create", ...}  # Deterministic
    ]
}
```

**Benefits:**

- Structured workflow with flexible decision points
- LLM handles complex analysis within workflow
- Maintain audit trail while allowing intelligence
- Controlled flexibility

**Use Cases:**

- Workflows needing security analysis
- Tasks requiring optimization decisions
- Complex validation logic

### Pattern 3: Hybrid "Smart Workflow"

Workflows with fixed structure but dynamic parameters determined by LLM.

```python
workflow = {
    "name": "smart_server_onboarding",
    "steps": [
        {
            "type": "tool_call",
            "tool": "address_create",
            "params": "{{agent_determines}}"  # LLM fills in based on context
        },
        {
            "type": "tool_call",
            "tool": "security_policy_create",
            "params": {
                "name": "{{agent_determines}}",
                "source": "{{extracted_from_context}}",
                "action": "allow"  # Fixed
            }
        }
    ]
}
```

**Benefits:**

- Workflow structure is auditable
- Parameters adapt to context
- Balance between flexibility and control

**Implementation:**

- Template parameters in workflow definition
- LLM extracts/generates values before execution
- Validation before workflow starts

### Pattern 4: ReAct for Planning, Deterministic for Execution

Agent analyzes and plans, then generates and executes a workflow.

```text
Phase 1 (ReAct - Planning):
  User: "Migrate 50 servers from old firewall"
    ↓
  Agent analyzes current state
    ↓
  Agent identifies objects to migrate
    ↓
  Agent creates workflow definition dynamically
    ↓
  Agent presents plan to user for approval

Phase 2 (Deterministic - Execution):
  User approves plan
    ↓
  Agent executes generated workflow
    ↓
  Each step predictable and logged
    ↓
  Human approvals at key points
    ↓
  Summary of all changes
```

**Benefits:**

- Intelligence in planning phase
- Reliability in execution phase
- Complete audit trail
- User controls before execution

**Use Cases:**

- Complex migrations
- Large-scale changes
- Multi-phase projects

---

## Intelligent Router Architecture

The **intelligent router** sits between the user and the execution patterns, automatically determining which pattern to use based on the request.

### Architecture Overview

```text
┌─────────────────────────────────────────────────────────┐
│                    Router Graph                         │
│                                                          │
│  User Input                                              │
│      ↓                                                   │
│  Initialize Device Context                               │
│      ↓                                                   │
│  ┌──────────────────────────────────────────┐           │
│  │         Router Subgraph                  │           │
│  │  1. Parse user request                   │           │
│  │  2. Classify intent with LLM             │           │
│  │  3. Match against workflows              │           │
│  │  4. Extract parameters                   │           │
│  │  5. Calculate confidence score           │           │
│  │  6. Make routing decision                │           │
│  └──────────────────┬───────────────────────┘           │
│                     │                                    │
│                     ▼                                    │
│            ┌────────────────┐                            │
│            │ Route Decision │                            │
│            └────────┬───────┘                            │
│                     │                                    │
│         ┌───────────┴────────────┐                       │
│         │                        │                       │
│         ▼                        ▼                       │
│  ┌─────────────┐        ┌──────────────┐                │
│  │ Confidence  │        │  Confidence  │                │
│  │  >= 0.8 &   │        │   < 0.8 OR   │                │
│  │  Workflow   │        │  No Workflow │                │
│  │  Matched    │        │    Match     │                │
│  └──────┬──────┘        └──────┬───────┘                │
│         │                      │                         │
│         ▼                      ▼                         │
│  ┌──────────────────┐  ┌─────────────────┐              │
│  │  Deterministic   │  │   Autonomous    │              │
│  │     Graph        │  │   ReAct Graph   │              │
│  │  (with params)   │  │ (flexible exec) │              │
│  └────────┬─────────┘  └────────┬────────┘              │
│           │                     │                        │
│           └──────────┬──────────┘                        │
│                      │                                   │
│                      ▼                                   │
│              Format Response                             │
│                      │                                   │
│                      ▼                                   │
│                    END                                   │
└─────────────────────────────────────────────────────────┘
```

### Router Components

#### 1. Intent Classifier

Uses LLM to understand user intent:

- Primary action (create, modify, delete, query, setup)
- Target objects (address, service, policy)
- Entities mentioned (IPs, names, ports)
- Workflow indicators (multi-step phrases)

#### 2. Workflow Matcher

Compares intent against available workflows:

- Semantic similarity between request and workflow descriptions
- Keyword matching against workflow metadata
- Intent pattern matching
- Returns best match with confidence score

#### 3. Parameter Extractor

Extracts parameters from natural language:

- Identifies values for workflow parameters
- Maps user phrases to parameter names
- Handles partial information gracefully
- Validates extracted values

#### 4. Confidence Scorer

Calculates routing confidence:

- Intent clarity (0-1)
- Workflow match quality (0-1)
- Parameter completeness (0-1)
- Combined score determines routing

#### 5. Routing Decision Engine

Makes final routing choice:

- Confidence >= 0.8 + workflow match → Deterministic
- Confidence < 0.8 OR no match → Autonomous
- Multiple high matches → Ask clarification
- Special keywords ("ad-hoc", "explore") → Force autonomous

---

## Routing Scenarios

### Scenario 1: Exact Workflow Match

**User Input:** "Set up web server"

**Router Processing:**

```text
Intent Classification:
  - Primary intent: setup/provision
  - Target: web server
  - Entities: none specific
  - Multi-step: yes

Workflow Matching:
  - Best match: "web_server_setup"
  - Confidence: 0.95
  - Reasoning: Exact phrase match

Parameter Extraction:
  - No parameters needed (workflow has defaults)
  - Completeness: 1.0

Routing Decision:
  - Confidence: 0.95 ✅
  - Route to: Deterministic
  - Workflow: web_server_setup
  - Params: {} (use defaults)
```

**Result:** Executes `web_server_setup` workflow with predefined steps

### Scenario 2: Semantic Match

**User Input:** "Create database infrastructure"

**Router Processing:**

```text
Intent Classification:
  - Primary intent: create/setup
  - Target: database infrastructure
  - Entities: none
  - Multi-step: yes

Workflow Matching:
  - Best match: "network_segmentation"
  - Confidence: 0.82
  - Reasoning: Database infrastructure typically includes network segmentation
  - Alternative: "multi_address_creation" (0.65)

Parameter Extraction:
  - tag: "Database" (inferred from context)
  - Completeness: 0.8

Routing Decision:
  - Confidence: 0.81 ✅
  - Route to: Deterministic
  - Workflow: network_segmentation
  - Params: {tag: "Database"}
```

**Result:** Executes network segmentation workflow with database tag

### Scenario 3: Parameter Extraction

**User Input:** "Create address for 10.1.1.50 named db-server"

**Router Processing:**

```text
Intent Classification:
  - Primary intent: create
  - Target: address object
  - Entities: IP=10.1.1.50, name=db-server
  - Multi-step: no (single operation)

Workflow Matching:
  - Best match: "simple_address"
  - Confidence: 0.88
  - Reasoning: Single address creation workflow

Parameter Extraction:
  - name: "db-server" ✅
  - value: "10.1.1.50" ✅
  - description: "db-server" (derived from name)
  - Completeness: 1.0

Routing Decision:
  - Confidence: 0.88 ✅
  - Route to: Deterministic
  - Workflow: simple_address
  - Params: {name: "db-server", value: "10.1.1.50", description: "db-server"}
```

**Result:** Executes simple address creation workflow with extracted parameters

### Scenario 4: Ambiguous Request

**User Input:** "Set up security"

**Router Processing:**

```text
Intent Classification:
  - Primary intent: setup
  - Target: security (ambiguous)
  - Entities: none
  - Multi-step: probably

Workflow Matching:
  - Match 1: "security_rule_complete" (0.75)
  - Match 2: "complete_security_workflow" (0.73)
  - Match 3: "network_segmentation" (0.68)
  - No clear winner

Routing Decision:
  - Confidence: 0.75 (below threshold) ❌
  - Multiple high matches
  - Route to: Autonomous (with clarification)
```

**Result:** ReAct agent asks for clarification:

```text
"I found several workflows related to security setup:
1. Complete security rule setup (address + policy)
2. Complete security workflow with commit
3. Network segmentation

Which would you like to use, or would you prefer I handle this flexibly?"
```

### Scenario 5: No Workflow Match

**User Input:** "Show me all unused address objects created before 2023"

**Router Processing:**

```text
Intent Classification:
  - Primary intent: query/analyze
  - Target: address objects
  - Entities: date filter, unused filter
  - Multi-step: yes (complex query)

Workflow Matching:
  - No good match
  - Best match: "address_list" (0.45 - too low)
  - Reasoning: Complex filtering not supported by workflows

Routing Decision:
  - Confidence: 0.45 ❌
  - No workflow match
  - Route to: Autonomous
```

**Result:** ReAct agent handles with multiple tool calls:

1. Calls `address_list()` to get all addresses
2. Filters by creation date (from metadata)
3. Checks usage (references in policies/groups)
4. Returns filtered results

### Scenario 6: Confidence Threshold Edge Case

**User Input:** "Create some addresses for servers"

**Router Processing:**

```text
Intent Classification:
  - Primary intent: create
  - Target: addresses (plural)
  - Entities: "servers" (vague)
  - Multi-step: maybe

Workflow Matching:
  - Best match: "multi_address_creation" (0.78)
  - Reasoning: Plural addresses mentioned

Parameter Extraction:
  - count: unknown ("some")
  - names: not provided
  - values: not provided
  - Completeness: 0.1

Routing Decision:
  - Match confidence: 0.78
  - Parameter completeness: 0.1
  - Combined: 0.44 ❌
  - Route to: Autonomous
```

**Result:** ReAct agent asks clarifying questions:

```text
"I can help create multiple address objects. Could you provide:
1. How many addresses?
2. The IP addresses or subnets?
3. Naming convention?"
```

### Scenario 7: Forced Routing with Keywords

**User Input:** "Explore what security policies we have"

**Router Processing:**

```text
Intent Classification:
  - Primary intent: query
  - Target: security policies
  - Special keyword: "explore" (indicates exploration)

Routing Decision:
  - Keyword "explore" detected
  - Force route to: Autonomous
  - Reason: Exploratory task best suited for flexible agent
```

**Result:** ReAct agent handles exploration with adaptive tool calls

**Keywords that force autonomous:**

- "explore", "investigate", "analyze", "troubleshoot", "debug", "find", "show me"

**Keywords that prefer deterministic:**

- "workflow", "standard", "procedure", "checklist", "run", "execute"

### Scenario 8: Multi-Workflow Request

**User Input:** "Set up web server and create security policy for it"

**Router Processing:**

```text
Intent Classification:
  - Primary intent: setup (multi-stage)
  - Target: web server + security policy
  - Multi-step: yes (multiple workflows)

Workflow Matching:
  - Match 1: "web_server_setup" (0.82)
  - Match 2: "complete_security_workflow" (0.85)
  - Multiple workflows needed

Routing Decision:
  - Multiple workflows detected
  - Route to: Autonomous (for orchestration)
  - Agent will: Execute workflows in sequence
```

**Result:** ReAct agent orchestrates:

1. Calls `workflow_execute("web_server_setup")`
2. Extracts created objects
3. Calls `workflow_execute("security_rule_complete")` with objects
4. Returns comprehensive summary

---

## Implementation Details

### Workflow Metadata Structure

Each workflow should include metadata for intelligent routing:

```python
"workflow_name": {
    "name": "Display Name",
    "description": "What this workflow does",
    
    # Routing metadata
    "keywords": ["key", "terms", "for", "matching"],
    "intent_patterns": [
        "example user phrase 1",
        "example user phrase 2"
    ],
    "required_params": ["param1", "param2"],
    "optional_params": ["param3", "param4"],
    "parameter_descriptions": {
        "param1": "Description of param1 for extraction",
        "param2": "Description of param2 for extraction"
    },
    
    # Execution definition
    "steps": [...]
}
```

### Confidence Scoring Formula

```python
confidence_score = (
    intent_clarity * 0.3 +
    workflow_match_quality * 0.4 +
    parameter_completeness * 0.2 +
    contextual_factors * 0.1
)
```

**Components:**

- **Intent clarity** (0-1): How well we understand user's goal
- **Workflow match** (0-1): Semantic similarity to workflow
- **Parameter completeness** (0-1): What % of params we extracted
- **Contextual factors** (0-1): Device context, user history, keywords

### Routing Thresholds

```python
ROUTING_THRESHOLDS = {
    "deterministic_min": 0.80,  # Minimum confidence for workflow routing
    "clarification_min": 0.60,  # Below this, don't ask, just use autonomous
    "multi_match_diff": 0.10,   # Max difference between top matches to clarify
}
```

---

## Best Practices

### 1. Start with Workflows for Common Tasks

Identify your most common operations and create workflows:

- Server onboarding
- Policy creation
- Network provisioning
- User access setup

Let ReAct handle everything else.

### 2. Use Rich Workflow Metadata

Invest in good metadata:

- Descriptive names and descriptions
- Comprehensive intent patterns
- Clear parameter specifications
- Example user phrases

Better metadata = better routing accuracy.

### 3. Monitor Routing Decisions

Track and analyze:

- How often each route is chosen
- User satisfaction with routing
- False positive workflows (wrong route)
- False negative workflows (missed route)

Use data to refine thresholds and metadata.

### 4. Provide Escape Hatches

Always allow users to override:

- "Actually, just let me do this manually"
- "Use autonomous mode for this"
- "Run workflow X instead"

### 5. Optimize for User Experience

**Good routing UX:**

```text
✅ "I found a workflow for web server setup. Executing..."
✅ "This looks like database provisioning. Should I use the standard workflow?"
✅ "No workflow found for this. I'll handle it flexibly."
```

**Bad routing UX:**

```text
❌ "Routing to deterministic graph with confidence 0.82"
❌ "Intent classification: {intent: create, target: address}"
❌ Silent routing with no explanation
```

### 6. Balance Automation and Control

**More automation** (higher threshold = 0.85):

- Production environments
- Experienced users
- Well-established workflows
- Cost-sensitive scenarios

**More control** (lower threshold = 0.75):

- Development environments
- New users
- Experimental workflows
- Learning scenarios

### 7. Leverage Both Patterns

Don't force everything into one pattern:

- Use ReAct for exploration and discovery
- Use workflows for production operations
- Use router for seamless user experience
- Use hybrid approaches for complex scenarios

### 8. Document Workflows Well

Each workflow should have:

- Clear name indicating purpose
- Detailed description
- Example usage scenarios
- Parameter requirements
- Expected outcomes
- Approval points explained

### 9. Test Routing Extensively

Create test datasets:

- Known workflow matches
- Known autonomous cases
- Edge cases
- Ambiguous requests
- Multi-intent requests

Aim for >85% routing accuracy.

### 10. Iterate Based on Usage

- Review misrouted requests weekly
- Update workflow metadata based on user phrases
- Adjust confidence thresholds based on outcomes
- Add new workflows for common patterns
- Retire unused workflows

---

## Summary

### Key Takeaways

1. **ReAct is for flexibility**, deterministic is for predictability
2. **Both patterns are valuable** in different scenarios
3. **Integration is powerful** - don't choose exclusively
4. **Intelligent routing** provides best user experience
5. **Confidence-based decisions** balance automation and control
6. **Continuous improvement** through monitoring and iteration

### Decision Flow

```text
User Request
    ↓
Can this be handled by a workflow?
    ├─ Yes, high confidence (>=0.8) → Use Deterministic
    ├─ Maybe, medium confidence (0.6-0.8) → Ask user or use Autonomous
    └─ No, low confidence (<0.6) → Use Autonomous

If using Deterministic:
    ↓
Can we extract all parameters?
    ├─ Yes → Execute workflow
    └─ No → Ask for missing params or use Autonomous

If using Autonomous:
    ↓
Does agent discover a workflow?
    ├─ Yes → Suggest workflow to user
    └─ No → Handle with tools
```

### The Future: Hybrid AI Agents

The most sophisticated agents combine:

- **Intelligence** (ReAct reasoning)
- **Reliability** (deterministic workflows)
- **Adaptability** (smart routing)
- **Safety** (approval gates)
- **Auditability** (comprehensive logging)

Your PAN-OS agent architecture demonstrates this hybrid approach, providing both patterns with intelligent routing between them.

---

**Version Notes:**

- v1.0 (2025-11-10): Initial comprehensive guide with routing architecture
