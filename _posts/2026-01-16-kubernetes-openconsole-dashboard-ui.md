---
title: "Kubernetes OpenConsole: Multi-Cluster Visibility and Controlled Operations"
date: 2026-01-16 19:20:00 +0300
last_modified_at: 2026-11-08 23:30:00 +0300
description: "Deploy Kubernetes OpenConsole for multi-cluster visibility, namespace-scoped permissions, live logs, audited operations and recorded pod shells."
categories: [DevOps, Kubernetes]
tags: [devops, kubernetes, ui, dashboard, observability, rbac]
toc: true
published: true
robots: index, follow
---

Kubernetes OpenConsole has grown from a visibility dashboard into a console for both observing clusters and performing controlled operations. It brings live workload data, troubleshooting tools and application-level permissions into a Go backend and a React interface.

The distinction matters: **the current console is not read-only by default at the Kubernetes identity level**. Restart, scale, YAML editing, pod shells and Secret access depend on application grants, feature flags and the permissions of the identity used to connect each cluster. A separate read-only Kubernetes RBAC manifest is available when the console should only observe.

[View Kubernetes OpenConsole on GitHub](https://github.com/vurulkan/kubernetes-openconsole).

## What the current console includes

### Cluster and workload visibility

- A multi-cluster selector remembered separately for each user, with an administrator-defined default.
- An administrator Overview for pod health, workload restarts, cluster usage, warning events and nodes.
- An administrator-only, read-only Nodes screen with capacity, allocatable resources, conditions, taints, events and the pods running on each node.
- Pods, Deployments, StatefulSets, DaemonSets, HPAs, Services, ConfigMaps, Secrets, Ingresses, CronJobs and Jobs in the Dashboard.
- Detail drawers for workloads and pods, including container state, requests and limits, rollout conditions, related events and restart explanations.
- Configurable list columns, search across displayed fields and label filters. Pod rows can show per-container state and the direct controller in the Containers and Controlled By columns.

List endpoints use a `client-go` informer cache. Live Events stream changes over WebSocket rather than relying on repeated full-page refreshes.

### Troubleshooting and observability

Pod, Deployment and Job logs support container selection, the previous container instance, live follow, search, pause, wrapping, copy and download. Streams reconnect and follow restarting containers.

CPU and memory usage come from metrics-server. Short-term usage history is kept in memory; a configured Prometheus source provides longer history, up to seven days. Container exit history is retained separately, including exits for pods that no longer exist.

The console also exposes Prometheus metrics, structured JSON logging and optional OpenTelemetry tracing. `/livez` checks the process and `/readyz` checks the database; one unavailable cluster does not make the console itself unready.

### Controlled operations

| Capability | Application permission |
|---|---|
| Restart a Deployment | `deployments:restart` |
| Scale a Deployment or StatefulSet | `deployments:scale`, `statefulsets:scale` |
| Edit workload YAML with diff, server dry-run and apply | `{resource}:edit` |
| Open a pod shell | `pods:exec` |
| Read Secret metadata or reveal a value | `secrets:list`, `secrets:get`, `secrets:reveal` |
| Edit a Secret | `secrets:edit` |

Write operations are opt-in for regular users through role permissions, scoped by namespace and cluster. Administrators implicitly have application permissions, but Kubernetes RBAC and operator feature flags still limit what can run.

Pod shell sessions are recorded as asciicast files by default and can be replayed by administrators. Recording settings include retention, size limits, total quota and disk-pressure policy. A recording can contain credentials printed in the terminal, so recordings need the same care as the audit database.

## Architecture and permission boundaries

- **Backend:** Go, `client-go`, chi, structured logging and SQLite.
- **Frontend:** React, TypeScript and Vite, with a YAML editor, WebSocket terminal and recording player.
- **Deployment:** one container, with persistent data under `/data`.

The application uses one configured identity per cluster. End users do not receive individual Kubernetes identities: OpenConsole evaluates their groups, roles and namespace/cluster grants in the application layer. The API server independently limits the shared identity through Kubernetes RBAC.

The pod does **not** automatically adopt its mounted ServiceAccount or discover a cluster from an environment variable. Connections are added in **Admin → Clusters**, using a ServiceAccount token or a supported kubeconfig. Avoid personal administrator kubeconfigs; exec-plugin authentication is not supported by the container.

## Choose an image

The current README uses release `2.21.0`:

```yaml
image: ghcr.io/vurulkan/kubernetes-openconsole:2.21.0
```

Release images support `linux/amd64` and `linux/arm64`. Pin a release for a reproducible installation. `latest` follows published releases; development images use separate `dev-*` tags. Release images include GitHub build-provenance and SBOM attestations; verification commands are in the repository README.

To build your own image from a checked-out repository:

```bash
docker build -t kubernetes-openconsole:local .
```

## Try it locally

```bash
docker run --rm -p 127.0.0.1:8080:8080 \
  -e TIMEZONE=Europe/Istanbul \
  -v kubernetes-openconsole-data:/data \
  ghcr.io/vurulkan/kubernetes-openconsole:2.21.0
```

Open `http://localhost:8080`. The named volume preserves the SQLite database and recordings. This starts the console; cluster access is configured through the UI afterwards.

## Deploy to Kubernetes

From the repository checkout:

```bash
kubectl apply -k deploy/
```

Before applying, review the manifests for your environment:

- `deployment.yaml` defaults to `latest`; pin the chosen release there or with the Kustomize `images` override.
- The deployment has **one replica**. SQLite on a ReadWriteOnce volume is not a horizontal scale-out configuration.
- The default PVC is 5 Gi and stores both the database and recordings. Plan capacity and backups accordingly.
- The Service exposes port 80 to container port 8080. Put your own Ingress or Gateway in front of it.
- The deployment runs without an automatically mounted ServiceAccount token. Cluster credentials are supplied through the UI.
- The default `rbac.yaml` includes permissions for supported operations. For an observation-only installation, replace its entry in `deploy/kustomization.yaml` with `rbac-readonly.yaml` **before** applying the directory.

The read-only manifest removes write operations and excludes Secrets. Logs remain available. Do not grant write or exec actions in application roles when the underlying Kubernetes identity cannot perform them.

## First login and cluster connection

On first startup, log in with `admin` / `admin` and complete the required password change. Administrator pages remain locked until the password is changed.

Then:

1. Open **Admin → Clusters → Add Cluster**.
2. Choose **ServiceAccount Token** or **Kubeconfig**.
3. Supply an API endpoint reachable from the OpenConsole backend and the matching CA certificate and credentials.
4. Save the cluster to validate the connection, then set a default if appropriate.
5. Configure users, groups, roles and namespace/cluster permissions.

For the cluster hosting OpenConsole, the API endpoint can be `https://kubernetes.default.svc`. Remote clusters need their own reachable endpoint and identity. The README includes token/CA extraction and kubeconfig examples; generated credentials should never be committed to Git.

## Users, identity and audit

Local users, LDAP/Active Directory and single-tenant Azure AD / Entra ID login are configured in the UI. LDAP supports search, import and first-login provisioning according to its configured rules.

Roles can use Viewer, Developer, SRE and Admin permission templates, or individual grants. Users without the required group and role assignments do not gain access merely by signing in. Each user switches only their own active cluster.

Audit records include the actor, action, target cluster, namespace/resource, outcome and operation details. Failed and denied actions are recorded as well. Audit filters and CSV export support access reviews. Administrators can list and revoke sessions and review shell recordings.

## Operator controls

| Setting | Purpose |
|---|---|
| `DATA_PATH` | SQLite location; image default `/data/app.db` |
| `STATIC_DIR` | Frontend assets; image default `/app/public` |
| `TIMEZONE` | Audit timestamp timezone; default UTC |
| `LOG_RETENTION_DAYS` | Audit retention; default 30 days |
| `RESTART_HISTORY_RETENTION_DAYS` | Container exit history; default 30 days |
| `MAX_REPLICAS` | Scale endpoint ceiling; default 100 |
| `EXEC_IDLE_TIMEOUT` | Idle pod-shell timeout; default `5m` |
| `MAX_EXEC_SESSIONS_PER_USER` | Concurrent shell limit; default 3 |

Feature flags let operators disable capabilities for everyone, including administrators:

```yaml
- name: FEATURE_POD_EXEC
  value: "false"
- name: FEATURE_YAML_EDIT
  value: "false"
- name: FEATURE_WORKLOAD_ACTIONS
  value: "false"
- name: FEATURE_SECRETS
  value: "false"
```

These flags complement Kubernetes RBAC and application grants. They do not replace either. Recording environment variables normally seed settings only on the first startup; later changes belong in **Admin → Recordings → Recording settings**. `SESSION_RECORDING_DIR` is read on each startup.

## Everyday use and troubleshooting

The UI supports English and Turkish, light/dark/system themes, saved views, a command palette and keyboard navigation. Shared views carry filters and context, but never grant access to the underlying namespace.

If the console appears empty, check the selected cluster and application permissions first. If a Kubernetes action returns 403, compare both the application grant and the connected identity's ClusterRole. Missing CPU/memory data usually requires checking metrics-server and the relevant metrics API permissions. A connection failure on Save should be investigated from the backend pod's network path and CA configuration.

Keep ServiceAccount permissions limited to the capabilities you actually expose, rotate credentials, and back up the persistent database and recordings. The console is an internal operations tool; its shared cluster identity makes careful permission design essential.

## Related cluster deployment guides

- [Kubernetes HA on Ubuntu](/posts/ansible-k8s-ha-cluster-ubuntu/)
- [Kubernetes HA on RHEL](/posts/ansible-k8s-ha-cluster-rhel/)
- [Kubernetes HA on Debian](/posts/ansible-k8s-ha-cluster-debian/)

Updated against the [repository README at `a63ae9a`](https://github.com/vurulkan/kubernetes-openconsole/blob/a63ae9a7b957b151b780b1ac16d3887c328c5688/README.md) on November 8, 2026. This article documents the repository's current deployment and usage model; consult the README for subsequent changes and the full configuration reference.
