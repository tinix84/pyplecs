# Article 7: Orchestration System Diagrams

## Priority Queue Processing

```mermaid
flowchart TD
    A[Incoming Simulation Requests] --> B{Assign Priority}

    B -->|User Specified| C[CRITICAL - 0]
    B -->|User Specified| D[HIGH - 1]
    B -->|Default| E[NORMAL - 2]
    B -->|User Specified| F[LOW - 3]

    C --> G[Priority Queue<br/>Min-Heap]
    D --> G
    E --> G
    F --> G

    G --> H{Scheduler}
    H --> I[Pop Highest Priority]

    I --> J{Same Model<br/>& Similar Priority?}

    J -->|Yes| K[Group into Batch]
    J -->|No| L[Execute Single]

    K --> M[Execute Batch<br/>PLECS Parallel API]
    L --> M

    M --> N{Success?}

    N -->|Yes| O[Store Result]
    N -->|No| P{Retry Count < 3?}

    P -->|Yes| Q[Wait + Exponential Backoff]
    Q --> M
    P -->|No| R[Mark as FAILED]

    O --> S[Notify User]
    R --> T[Error Notification]

    style C fill:#e74c3c,stroke:#333,stroke-width:3px
    style D fill:#f39c12,stroke:#333,stroke-width:2px
    style E fill:#3498db,stroke:#333,stroke-width:1px
    style F fill:#95a5a6,stroke:#333,stroke-width:1px
    style O fill:#2ecc71,stroke:#333,stroke-width:2px
    style R fill:#e74c3c,stroke:#333,stroke-width:2px
```

## Task Lifecycle States

```mermaid
stateDiagram-v2
    [*] --> QUEUED: submit_simulation()

    QUEUED --> RUNNING: Scheduler picks task
    QUEUED --> CANCELLED: User cancels

    RUNNING --> COMPLETED: Simulation succeeds
    RUNNING --> FAILED: Max retries exceeded
    RUNNING --> RUNNING: Transient error<br/>(auto-retry)

    COMPLETED --> [*]: Results delivered
    FAILED --> [*]: Error logged
    CANCELLED --> [*]: Task removed

    note right of QUEUED
        Waiting in priority queue
        Position based on priority
    end note

    note right of RUNNING
        Executing on PLECS
        Progress: 0-100%
        Retries: 0-3 attempts
    end note

    note right of COMPLETED
        Results cached
        Task archived
    end note
```

## Retry Logic with Exponential Backoff

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant E as Executor
    participant P as PLECS Server
    participant L as Logger

    Note over O,L: Attempt 1

    O->>E: execute_task(task)
    E->>P: simulate(params)
    P--xE: ConnectionError

    E->>E: Check retry count (0 < 3)
    E->>L: Log: Attempt 1 failed, retrying...
    E->>E: sleep(5 seconds)

    Note over O,L: Attempt 2 (5s delay)

    E->>P: simulate(params)
    P--xE: TimeoutError

    E->>E: Check retry count (1 < 3)
    E->>L: Log: Attempt 2 failed, retrying...
    E->>E: sleep(10 seconds)

    Note over O,L: Attempt 3 (10s delay)

    E->>P: simulate(params)
    P-->>E: Success! Results

    E->>L: Log: Success on attempt 3
    E-->>O: Task COMPLETED

    Note over O,L: Total time: ~25s (5s + 10s + actual sim time)
```

## Batch Optimization Strategy

```mermaid
flowchart LR
    A[Priority Queue] --> B{Batch Optimizer}

    B --> C{Check Next Tasks}

    C --> D{Same Model File?}

    D -->|Yes| E{Priority Difference ≤ 1?}
    D -->|No| F[Execute Current Batch]

    E -->|Yes| G{Batch Size < Max?}
    E -->|No| F

    G -->|Yes| H[Add to Batch]
    G -->|No| F

    H --> C

    F --> I[Execute Batch via<br/>PLECS Native API]

    I --> J{Results}
    J --> K[Store All Results]
    K --> L[Process Next Batch]
    L --> B

    style B fill:#f39c12,stroke:#333,stroke-width:3px
    style I fill:#2ecc71,stroke:#333,stroke-width:3px
    style K fill:#3498db,stroke:#333,stroke-width:2px
```

## Real-World Scenario: 3 AM Production

```mermaid
gantt
    title Production Scenario: Automatic Retry Saves the Day
    dateFormat HH:mm
    axisFormat %H:%M

    section Background Jobs
    Long Parameter Sweep (LOW) :active, bg1, 02:00, 2h

    section Critical Task
    Production Design Verification (CRITICAL) :crit, task1, 03:00, 10m

    section Failure & Recovery
    First Attempt (Connection Error) :crit, fail1, 03:00, 5s
    Retry Delay :03:00, 5s
    Second Attempt (Success!) :done, success, 03:00, 10m

    section User Experience
    User Sleeps :03:00, 3h
    User Wakes Up :milestone, 06:00, 0m
    Sees Completed Results :done, 06:00, 5m
```

## Event Callbacks & Monitoring

```mermaid
flowchart TD
    A[Orchestrator Events] --> B{Event Type}

    B -->|on_submit| C[Event: Submitted]
    B -->|on_start| D[Event: Started]
    B -->|on_progress| E[Event: Progress Update]
    B -->|on_complete| F[Event: Completed]
    B -->|on_error| G[Event: Error]

    C --> H[Registered Callbacks]
    D --> H
    E --> H
    F --> H
    G --> H

    H --> I[Logger]
    H --> J[WebSocket Broadcast]
    H --> K[Slack Notification]
    H --> L[Metrics Collector]
    H --> M[Custom User Callback]

    I --> N[File: simulation.log]
    J --> O[Web Dashboard Update]
    K --> P[Team Alert]
    L --> Q[Prometheus/Grafana]
    M --> R[User-Defined Action]

    style H fill:#f39c12,stroke:#333,stroke-width:3px
    style O fill:#3498db,stroke:#333,stroke-width:2px
    style P fill:#e74c3c,stroke:#333,stroke-width:2px
```

## Statistics Tracking

```mermaid
pie title "Production Simulation Results (3 Months)"
    "Completed on First Attempt" : 8547
    "Completed After Retry" : 453
    "Failed (All Retries Exhausted)" : 50
```

**Key Metrics**:
- **Total Simulations**: 9,050
- **Success Rate**: 99.4% (with retries)
- **Retry Effectiveness**: 90% of failures recovered
- **Average Retries per Failed Task**: 1.7
