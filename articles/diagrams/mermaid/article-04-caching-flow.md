# Article 4: Caching System Flow Diagram

## Cache Decision Flow

```mermaid
flowchart TD
    A[Simulation Request] --> B{Generate Cache Key}
    B --> C[SHA256 Hash]
    C --> D{Include Model Content?}
    D -->|Yes| E[Read Model File]
    D -->|No| F[Use File Path Only]
    E --> G[Hash: Model + Parameters + Version]
    F --> G
    G --> H{Cache Exists?}
    H -->|Yes - Cache Hit| I[Load from Parquet]
    I --> J[Return Result]
    H -->|No - Cache Miss| K[Run PLECS Simulation]
    K --> L[Store Result]
    L --> M{Storage Format}
    M -->|Parquet| N[Save with Snappy Compression]
    M -->|HDF5| O[Save with GZIP]
    M -->|CSV| P[Save as Text]
    N --> J
    O --> J
    P --> J

    style A fill:#9f9,stroke:#333,stroke-width:2px
    style I fill:#9ff,stroke:#333,stroke-width:3px
    style K fill:#ff9,stroke:#333,stroke-width:2px
    style J fill:#9f9,stroke:#333,stroke-width:2px
```

## Cache Key Generation

```mermaid
sequenceDiagram
    participant User
    participant Cache
    participant Hasher
    participant FileSystem
    participant PLECS

    User->>Cache: simulate(model, params)
    Cache->>Hasher: create_cache_key()

    alt Include Model Content
        Hasher->>FileSystem: read model.plecs
        FileSystem-->>Hasher: file content
    end

    Hasher->>Hasher: normalize_parameters()
    Hasher->>Hasher: SHA256(model + params + version)
    Hasher-->>Cache: cache_key (64 chars)

    Cache->>Cache: check if exists

    alt Cache Hit
        Cache->>FileSystem: load cache_key.parquet
        FileSystem-->>Cache: simulation results
        Cache-->>User: results (50ms)
    else Cache Miss
        Cache->>PLECS: run simulation
        PLECS-->>Cache: results (10000ms)
        Cache->>FileSystem: store cache_key.parquet
        Cache-->>User: results
    end
```

## Cache Storage Comparison

```mermaid
graph TD
    subgraph "Storage Formats"
        A[Simulation Result<br/>10k points, 8 channels]

        A --> B[CSV Format]
        A --> C[HDF5 Format]
        A --> D[Parquet Format]

        B --> B1[Write: 450ms<br/>Read: 380ms<br/>Size: 2.41 MB]
        C --> C1[Write: 180ms<br/>Read: 120ms<br/>Size: 0.78 MB]
        D --> D1[Write: 95ms<br/>Read: 55ms ⭐<br/>Size: 0.61 MB ⭐]
    end

    style D fill:#afa,stroke:#333,stroke-width:3px
    style D1 fill:#afa,stroke:#333,stroke-width:2px
    style B1 fill:#faa,stroke:#333
    style C1 fill:#ff9,stroke:#333
```

## Cache Hit Rate Over Time

```mermaid
gantt
    title Cache Performance (1 Month Production)
    dateFormat YYYY-MM-DD
    section Week 1
    Cache Hits (55%)    :2025-01-01, 7d
    section Week 2
    Cache Hits (62%)    :2025-01-08, 7d
    section Week 3
    Cache Hits (67%)    :2025-01-15, 7d
    section Week 4
    Cache Hits (63%)    :2025-01-22, 7d
```

## Cache Invalidation Triggers

```mermaid
graph LR
    A[Simulation Request] --> B{Check Validity}

    B --> C{Model Changed?}
    C -->|Yes| D[Cache Miss]
    C -->|No| E{PLECS Version Changed?}

    E -->|Yes| D
    E -->|No| F{Parameters Different?}

    F -->|Yes| D
    F -->|No| G{Cache Expired TTL?}

    G -->|Yes| D
    G -->|No| H[Cache Hit ✓]

    style H fill:#afa,stroke:#333,stroke-width:3px
    style D fill:#faa,stroke:#333,stroke-width:2px
```

## Time Savings Visualization

```mermaid
pie title "Time Distribution (63% Hit Rate)"
    "Cache Hits (instant)" : 63
    "New Simulations" : 37
```

**Impact**:
- **Without Cache**: 100 simulations × 10s = 1000s (16.7 min)
- **With Cache** (63% hit rate):
  - 63 hits × 0.05s = 3.15s
  - 37 misses × 10s = 370s
  - **Total**: 373s (6.2 min) → **2.7× speedup**
