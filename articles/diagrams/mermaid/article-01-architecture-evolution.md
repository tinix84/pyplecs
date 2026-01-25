# Article 1: Architecture Evolution Diagram

## Before Refactoring (v0.x) - Complex Architecture

```mermaid
graph TD
    A[User Request] --> B[GenericConverterPlecsMdl]
    B --> C{Parse XML Model}
    C --> D[Extract Metadata]
    D --> E[generate_variant_plecs_mdl]
    E --> F{Create Physical File}
    F --> G[Write to data/01/]
    G --> H[Create New Model Object]
    H --> I[PlecsServer Init]
    I --> J[Custom Thread Pool]
    J --> K[Worker Thread 1]
    J --> L[Worker Thread 2]
    J --> M[Worker Thread 3]
    J --> N[Worker Thread 4]
    K --> O[PLECS XML-RPC]
    L --> O
    M --> O
    N --> O
    O --> P[Sequential Simulations]
    P --> Q[Result Aggregation]
    Q --> R[Cleanup Variant Files]

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style R fill:#f96,stroke:#333,stroke-width:2px
    style F fill:#ff6,stroke:#333,stroke-width:2px
    style J fill:#ff6,stroke:#333,stroke-width:2px
```

**Complexity**: HIGH
**LOC**: 4,081
**Performance**: 2× baseline (custom threading)

## After Refactoring (v1.0.0) - Simplified Architecture

```mermaid
graph TD
    A[User Request] --> B[PlecsServer]
    B --> C{Cache Check}
    C -->|Cache Hit| D[Return Cached Result]
    C -->|Cache Miss| E[simulate_batch]
    E --> F[PLECS Native Batch API]
    F --> G[PLECS Internal Parallelization]
    G --> H[Process 1: Core 0]
    G --> I[Process 2: Core 1]
    G --> J[Process 3: Core 2]
    G --> K[Process 4: Core 3]
    H --> L[Results]
    I --> L
    J --> L
    K --> L
    L --> M[Store in Cache]
    M --> D

    style A fill:#9f9,stroke:#333,stroke-width:2px
    style D fill:#9f9,stroke:#333,stroke-width:2px
    style C fill:#9ff,stroke:#333,stroke-width:2px
    style F fill:#9ff,stroke:#333,stroke-width:2px
```

**Complexity**: LOW
**LOC**: 2,500 (39% reduction)
**Performance**: 4-5× baseline (native parallelization)

## Comparison Summary

```mermaid
graph LR
    subgraph "v0.x Issues"
        A1[File I/O Overhead]
        A2[Python GIL Contention]
        A3[Custom Threading Complexity]
        A4[Manual Cleanup Required]
    end

    subgraph "v1.0.0 Improvements"
        B1[In-Memory Parameters]
        B2[Process-Level Parallelism]
        B3[PLECS Native Batch]
        B4[Automatic Caching]
    end

    A1 -.->|Removed| B1
    A2 -.->|Solved| B2
    A3 -.->|Simplified| B3
    A4 -.->|Automated| B4

    style A1 fill:#faa,stroke:#333
    style A2 fill:#faa,stroke:#333
    style A3 fill:#faa,stroke:#333
    style A4 fill:#faa,stroke:#333
    style B1 fill:#afa,stroke:#333
    style B2 fill:#afa,stroke:#333
    style B3 fill:#afa,stroke:#333
    style B4 fill:#afa,stroke:#333
```
