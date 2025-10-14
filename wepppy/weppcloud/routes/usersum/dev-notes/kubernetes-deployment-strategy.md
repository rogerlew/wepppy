### **1\. Development Environment: Docker Compose (The Local Stack) 🐳**

This layer is for developers. It prioritizes speed, simplicity, and a fast iteration loop.

* **Rationale**: The existing Docker Compose file is well-suited for a consistent, isolated local development environment. It avoids the complexity of a local Kubernetes cluster and allows for real-time code changes via host-mounted volumes.  
* **Key Components**:  
  * **Docker Compose File**: The current docker-compose.yml serves as the single source of truth for the development stack.  
  * **Volumes**: The host mounts (../:/workdir/wepppy, etc.) are critical here. They enable hot-reloading and allow developers to use their local IDEs.  
  * **Tooling**: Use docker compose for all local environment management.

---

### **2\. Repository & Data Management 🧹**

This is a one-time project to optimize the underlying codebase and data storage. It's a critical first step before a scalable Kubernetes deployment.

* **Problem**: A 3.3GB .git history and large data files (e.g., climates, soils) make the repository bloated and inefficient for container image builds.  
* **Solution**:  
  1. **Git History Cleanup**: Use **git-filter-repo** to permanently remove large files from the repository history. This will dramatically shrink the .git directory size.  
  2. **Separate Data from Code**: Move the large climates and soils data directories out of the main repository.  
  3. **Data Storage**: Store this data on the existing **/geodata NFS** share. This is a perfect use case for a shared, read-heavy volume that can be accessed by multiple pods.  
  4. **Container Build Process**: The final Docker images for production will **not** include these large files. The running containers will access them from the mounted /geodata volume.

---

### **3\. Production Architecture: Kubernetes (The On-Prem Stack) 🚀**

This is the core of the deployment strategy. It translates the Docker Compose services into a resilient, scalable, and manageable on-premise Kubernetes cluster.

#### **Core Services**

Each service will have its own **Deployment** and **Service** objects.

* **weppcloud**: A **Deployment** with multiple replicas for horizontal scaling.  
* **rq-worker**: A **Deployment** with a configurable number of replicas. It will be the workhorse for processing jobs.  
* **PostgreSQL**: A **StatefulSet** with a single replica to ensure a stable identity and persistent storage for the database.  
* **Redis**: A **StatefulSet** or **Deployment** with a PVC for persistence and a ClusterIP Service for internal access.

#### **Storage**

On-premise storage is a key consideration.

* **Shared Data (NFS)**: The **wc1 and geodata NFS** shares will be exposed to Kubernetes as **Persistent Volumes (PVs)**. These PVs will be backed by the existing NFS server. **Persistent Volume Claims (PVCs)** will then be used by weppcloud, weppcloudr, and other services to mount these volumes.  
* **Database (Block Storage)**: For PostgreSQL, a **distributed block storage** solution like **Rook/Ceph** or **Longhorn** is recommended. This provides better performance and fault tolerance for the database's write-heavy workload than NFS.

#### **Networking and Traffic Routing**

* **Ingress Controller**: An open-source Ingress Controller like **Nginx** or **Traefik** will replace caddy as the reverse proxy. It will be deployed using a NodePort service and a tool like **MetalLB** to expose it externally.  
* **Session Affinity**: The runid affinity requirement will be handled at the Ingress controller level using **cookie-based session affinity**. This ensures that requests for a specific runid are routed to the same weppcloud pod, preserving the session state.

#### **CI/CD and GitOps**

* **Private Registry**: Deploy a private container registry in the cluster, such as **Harbor**, to store all WEPPcloud images. Your CI pipeline will push images here.  
* **GitOps**: Adopt a **GitOps** workflow using a tool like **Argo CD** or **Flux**. All Kubernetes manifests will be stored in a Git repository. Any changes to the manifests will be automatically applied to the cluster, making the repository the single source of truth.

#### **Monitoring & Management**

* **Logging**: Use a centralized logging solution like the **EFK** (Elasticsearch, Fluentd, Kibana) or **Loki** stack to collect and analyze logs from all services.  
* **Metrics**: Deploy **Prometheus** and **Grafana** to monitor cluster and application performance, providing dashboards for resource utilization and service health.

This strategy combines the best of both worlds: a simple, productive development environment and a robust, scalable, and manageable production deployment tailored to your on-premise infrastructure.
