# High-Availability Containerized Web Platform

This project implements a highly available containerized web application platform with OS-level clustering concepts, TLS, monitoring, and async processing.

## Architecture

```mermaid
graph TD
    User([User/Client]) -- HTTPS:443 --> VIP[Virtual IP: 172.20.0.100]
    
    subgraph LB_Layer [Load Balancer Layer - High Availability]
        VIP --> Keepalived1[Keepalived Master]
        VIP --> Keepalived2[Keepalived Backup]
        Keepalived1 --- Traefik1[Traefik 1]
        Keepalived2 --- Traefik2[Traefik 2]
    end

    Traefik1 -- HTTP --> App[Flask Application]
    Traefik2 -- HTTP --> App
    
    subgraph App_Layer [Application & Processing]
        App -- SQL --> DB[(PostgreSQL)]
        App -- Publish --> RMQ[RabbitMQ]
        Worker[Background Worker] -- Consume --> RMQ
        Worker -- Update --> DB
    end

    subgraph Monitoring_Layer [Observability]
        Netdata[Netdata] --- Traefik1
        Netdata --- App
        Netdata --- DB
    end

    classDef primary fill:#f9f,stroke:#333,stroke-width:2px;
    classDef secondary fill:#bbf,stroke:#333,stroke-width:1px;
    class VIP,Keepalived1,Keepalived2,Traefik1,Traefik2 primary;
```

### Component Details

#### 1. Load Balancer Layer (Traefik & Keepalived)
- **Traefik (v2.10)**: Acts as the edge router, handling TLS termination and dynamic service discovery via Docker labels. 
    - **Configuration**: Managed via `docker-compose.yml` and `lb/dynamic.yml`.
    - **Features**: Automatic HTTP-to-HTTPS redirection, SSL/TLS management with self-signed certificates.
- **Keepalived**: Manages the Virtual IP (VIP) `172.20.0.100`. 
    - **Mechanism**: Uses VRRP (Virtual Router Redundancy Protocol). The Master node holds the VIP; if it fails, the Backup node takes over.
    - **Health Checks**: Monitors the Traefik process using `killall -0 traefik`.

#### 2. Application Layer (Flask)
- **Framework**: Flask with SQLAlchemy ORM.
- **Server**: Gunicorn (as configured in the Dockerfile).
- **Statelessness**: The app stores no local state, allowing easy scaling. All state is in PostgreSQL or RabbitMQ.
- **Endpoints**:
    - `GET /items`: List all items.
    - `POST /items`: Create a new item.
    - `POST /items/<id>/process`: Enqueue a background job to RabbitMQ.

#### 3. Database Layer (PostgreSQL)
- **Version**: 15 (Alpine based).
- **Persistence**: Data is persisted in a Docker volume `db_data`, ensuring it survives container restarts.
- **Access**: Restricted to the `private` internal network.

#### 4. Async Processing (RabbitMQ & Worker)
- **RabbitMQ**: Message broker for asynchronous tasks.
- **Worker**: A separate Python process that consumes messages from the `task_queue` and performs background operations (e.g., updating database records).

#### 5. Monitoring (Netdata)
- **Capabilities**: Real-time performance monitoring of CPU, RAM, Disk I/O, and Docker container metrics.
- **Dashboard**: Available on port `19999`.

#### 6. OS-Level Clustering (Corosync & Pacemaker)
- **Files**: `lb/Dockerfile.cluster`, `lb/corosync.conf`.
- **Purpose**: Provides a template for production-grade clustering where resources (VIP, Traefik) are managed by Pacemaker instead of just Keepalived. This allows for more complex failover logic and resource grouping.

## Prerequisites

- Docker and Docker Compose
- openssl (for generating certificates)

## Setup and Startup

1. **Generate TLS Certificates**:
   ```bash
   bash scripts/generate_certs.sh
   ```

2. **Configure Environment**:
   The project includes a default `.env` file. You can modify it if needed.

3. **Start the Platform**:
   ```bash
   docker-compose up --build
   ```

## Verification

### Functional
- **HTTPS Access**: Access the application via `https://localhost` (via VIP 172.20.0.100 if configured on host, or directly via Traefik ports).
- **CRUD Operations**: Use `/items` endpoint for POST, GET, PUT, DELETE.
- **Async Processing**: POST to `/items/<id>/process` to trigger a background job.

### Reliability
- **Failover**: Stop `traefik_1` to see Keepalived migrate the VIP to `traefik_2`.
- **Persistence**: Database data is stored in a persistent volume `db_data`.

### Observability
- **Netdata**: Access metrics at `http://localhost:19999`.
- **Traefik Dashboard**: Access at `http://localhost:8080`.

## Phase 3: OS-Level Clustering
The `lb/Dockerfile.cluster` and `lb/corosync.conf` provide the foundation for OS-level clustering. In a production environment, these would be deployed on separate physical or virtual nodes to manage resources like the VIP and Traefik service across the cluster, ensuring that if a node fails, Pacemaker migrates the services to the healthy node.

## Deliverables
- `docker-compose.yml`: Main orchestration file.
- `app/`: Flask application and Worker source code.
- `lb/`: Load balancer and Keepalived/Cluster configurations.
- `scripts/`: TLS generation and utility scripts.
- `.env`: Environment configuration.
