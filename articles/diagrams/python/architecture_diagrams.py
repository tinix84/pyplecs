"""
System Architecture Diagrams for PyPLECS Article Series
Uses diagrams library (pip install diagrams)
Generates architecture diagrams for Articles 5, 7
"""

try:
    from diagrams import Diagram, Cluster, Edge
    from diagrams.programming.language import Python
    from diagrams.onprem.client import Client
    from diagrams.onprem.compute import Server
    from diagrams.onprem.queue import Celery
    from diagrams.generic.storage import Storage
    from diagrams.generic.database import SQL
    from diagrams.generic.blank import Blank
    from diagrams.custom import Custom
    import os

    DIAGRAMS_AVAILABLE = True
except ImportError:
    print("⚠️  diagrams library not installed. Skipping architecture diagrams.")
    print("   Install with: pip install diagrams")
    DIAGRAMS_AVAILABLE = False

OUTPUT_DIR = "../output"


def create_api_architecture():
    """Article 5: REST API Architecture"""
    if not DIAGRAMS_AVAILABLE:
        return

    graph_attr = {
        "fontsize": "14",
        "bgcolor": "white",
        "pad": "0.5"
    }

    with Diagram("PyPLECS REST API Architecture",
                 filename=f"{OUTPUT_DIR}/article-05-api-architecture",
                 show=False,
                 direction="TB",
                 graph_attr=graph_attr):

        with Cluster("Client Applications"):
            clients = [
                Client("Python"),
                Client("MATLAB"),
                Client("JavaScript"),
                Client("curl/CLI")
            ]

        with Cluster("PyPLECS API Server (FastAPI)"):
            api = Server("REST API\n(Port 8000)")

            with Cluster("Endpoints"):
                sim_endpoint = Python("POST /simulations")
                status_endpoint = Python("GET /simulations/{id}")
                results_endpoint = Python("GET /results")
                cache_endpoint = Python("POST /cache/clear")

        with Cluster("Orchestration Layer"):
            orchestrator = Celery("SimulationOrchestrator")
            priority_queue = Storage("Priority Queue")
            task_manager = Python("Task Manager")

        with Cluster("Cache Layer"):
            cache = SQL("SimulationCache")
            cache_store = Storage("Parquet Files")

        with Cluster("Execution Layer"):
            plecs_server = Server("PLECS Server\n(XML-RPC)")
            plecs_batch = Python("Batch Parallel API")

        # Connections
        for client in clients:
            client >> Edge(label="HTTP") >> api

        api >> sim_endpoint >> orchestrator
        api >> status_endpoint >> task_manager
        api >> results_endpoint >> cache

        orchestrator >> priority_queue
        priority_queue >> task_manager

        task_manager >> Edge(label="Check") >> cache
        cache >> cache_store

        task_manager >> Edge(label="Execute") >> plecs_server
        plecs_server >> plecs_batch

        plecs_batch >> Edge(label="Results") >> cache

    print("✓ Saved: article-05-api-architecture.png")


def create_orchestration_flow():
    """Article 7: Orchestration System Flow"""
    if not DIAGRAMS_AVAILABLE:
        return

    graph_attr = {
        "fontsize": "14",
        "bgcolor": "white",
        "pad": "0.5"
    }

    with Diagram("Simulation Orchestration Flow",
                 filename=f"{OUTPUT_DIR}/article-07-orchestration-flow",
                 show=False,
                 direction="LR",
                 graph_attr=graph_attr):

        user = Client("User Request")

        with Cluster("Orchestrator"):
            submit = Python("submit_simulation()")

            with Cluster("Priority Queue"):
                critical = Storage("CRITICAL (0)")
                high = Storage("HIGH (1)")
                normal = Storage("NORMAL (2)")
                low = Storage("LOW (3)")

            scheduler = Python("Scheduler")

            with Cluster("Batch Grouping"):
                batch_optimizer = Python("Batch Optimizer")
                group_by_model = Python("Group by Model")

            with Cluster("Retry Logic"):
                executor = Python("Executor")
                retry = Python("Retry Handler\n(max 3 attempts)")

        with Cluster("PLECS Execution"):
            plecs = Server("PLECS Batch API")
            workers = [
                Python("Worker 1"),
                Python("Worker 2"),
                Python("Worker 3"),
                Python("Worker 4")
            ]

        cache = SQL("Result Cache")

        # Flow
        user >> submit
        submit >> Edge(label="Enqueue") >> critical
        submit >> high
        submit >> normal
        submit >> low

        critical >> scheduler
        high >> scheduler
        normal >> scheduler
        low >> scheduler

        scheduler >> batch_optimizer
        batch_optimizer >> group_by_model
        group_by_model >> executor

        executor >> Edge(label="Try") >> plecs
        executor >> Edge(label="On Failure", style="dashed", color="red") >> retry
        retry >> Edge(label="Retry", style="dashed") >> executor

        plecs >> workers[0]
        plecs >> workers[1]
        plecs >> workers[2]
        plecs >> workers[3]

        for worker in workers:
            worker >> Edge(label="Store") >> cache

    print("✓ Saved: article-07-orchestration-flow.png")


def create_caching_architecture():
    """Article 4: Caching System Architecture"""
    if not DIAGRAMS_AVAILABLE:
        return

    graph_attr = {
        "fontsize": "14",
        "bgcolor": "white",
        "pad": "0.5"
    }

    with Diagram("Hash-Based Caching Architecture",
                 filename=f"{OUTPUT_DIR}/article-04-cache-architecture",
                 show=False,
                 direction="TB",
                 graph_attr=graph_attr):

        user = Client("Simulation Request")

        with Cluster("Cache Key Generation"):
            hasher = Python("SHA256 Hasher")
            model_reader = Storage("Read model.plecs")
            param_normalizer = Python("Normalize Params")
            version_checker = Python("Get PLECS Version")

        with Cluster("Cache Storage"):
            cache_manager = SQL("Cache Manager")

            with Cluster("Storage Backends"):
                parquet = Storage("Parquet\n(Primary)")
                hdf5 = Storage("HDF5\n(Large Data)")
                csv = Storage("CSV\n(Fallback)")

        with Cluster("Cache Validation"):
            ttl_checker = Python("TTL Checker\n(30 days)")
            size_limiter = Python("Size Limiter\n(10 GB max)")

        plecs = Server("PLECS Simulation\n(on cache miss)")

        # Flow
        user >> hasher
        hasher >> model_reader
        hasher >> param_normalizer
        hasher >> version_checker

        model_reader >> Edge(label="Cache Key\n(64 char hash)") >> cache_manager
        param_normalizer >> cache_manager
        version_checker >> cache_manager

        cache_manager >> Edge(label="Store") >> parquet
        cache_manager >> hdf5
        cache_manager >> csv

        cache_manager >> Edge(label="Validate") >> ttl_checker
        ttl_checker >> size_limiter

        cache_manager >> Edge(label="Miss", color="red") >> plecs
        plecs >> Edge(label="New Result") >> cache_manager

    print("✓ Saved: article-04-cache-architecture.png")


if __name__ == '__main__':
    if not DIAGRAMS_AVAILABLE:
        print("\n❌ diagrams library not available")
        print("   Install with: pip install diagrams")
        print("   Then run this script again.")
        exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\n🏗️  Generating architecture diagrams...")
    print("=" * 60)

    create_api_architecture()
    create_orchestration_flow()
    create_caching_architecture()

    print("=" * 60)
    print("✅ All architecture diagrams generated successfully!")
    print(f"📁 Output directory: {OUTPUT_DIR}/")
    print("\nGenerated files:")
    print("  • article-05-api-architecture.png")
    print("  • article-07-orchestration-flow.png")
    print("  • article-04-cache-architecture.png")
    print("\nNote: Diagrams library generates high-quality PNG images")
    print("      suitable for publication in articles.")
