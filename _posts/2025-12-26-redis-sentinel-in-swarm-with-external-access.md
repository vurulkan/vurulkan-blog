---
title: "Setting Up a Redis Sentinel Cluster on Docker Swarm with External Access"
date: 2025-12-26 02:00:00 +0300
last_modified_at: 2026-11-09 17:30:00 +0300
description: "Configure Redis Sentinel on Docker Swarm with host-published ports, reachable replica addresses and master discovery for clients outside the Swarm."
categories: [DevOps, Docker]
tags: [redis, docker, swarm, docker swarm]
toc: true
published: true
robots: index, follow
---

Redis Sentinel works well for high availability, but running it on Docker Swarm introduces a common issue: Sentinel may announce an internal IP that external clients cannot reach. This becomes a problem when applications outside the Swarm try to connect to Sentinel and discover the current Redis master.

This guide shows how to deploy Redis + Sentinel on a 3-node Docker Swarm cluster and ensure that external applications can reliably access the correct Redis instance during failover.

The example uses **host-mode port publishing**, which bypasses Swarm's routing mesh for those ports. It does not put the containers in the host network namespace. Both Sentinel peers and Redis replicas must advertise addresses reachable from the other nodes and from your clients. Replace the example private IPs with addresses on your trusted network.

This revision was checked against the [Redis Sentinel documentation](https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/) and [Docker Swarm networking documentation](https://docs.docker.com/engine/swarm/networking/). The revised configuration has not been exercised on a live three-node cluster as part of this article update; use the checks below before relying on failover.

---

## Architecture Overview

We use a 3-node Docker Swarm cluster:

- redis-1 → 172.16.207.198
- redis-2 → 172.16.207.199
- redis-3 → 172.16.207.200

Each node runs:

- one Redis container
- one Sentinel container

---

## Adding Node Labels

```bash
docker node update --label-add redis_node=redis-1 <NODE_ID_198>
docker node update --label-add redis_node=redis-2 <NODE_ID_199>
docker node update --label-add redis_node=redis-3 <NODE_ID_200>
```

List nodes:

```bash
docker node ls
```

---

## Creating Sentinel Config Files

```bash
mkdir -p /docker-deployments/redis-cluster/sentinel{1,2,3}
```

### sentinel1/sentinel.conf

```ini
port 26380
sentinel monitor mymaster 172.16.207.198 6380 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 10000
sentinel parallel-syncs mymaster 1
sentinel announce-ip 172.16.207.198
sentinel announce-port 26380
```

### sentinel2/sentinel.conf

```ini
port 26381
sentinel monitor mymaster 172.16.207.198 6380 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 10000
sentinel parallel-syncs mymaster 1
sentinel announce-ip 172.16.207.199
sentinel announce-port 26381
```

### sentinel3/sentinel.conf

```ini
port 26382
sentinel monitor mymaster 172.16.207.198 6380 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 10000
sentinel parallel-syncs mymaster 1
sentinel announce-ip 172.16.207.200
sentinel announce-port 26382
```

### File permissions

Create each `sentinel.conf` inside the corresponding directory, on the node where that Sentinel will run. Sentinel discovers peers through the monitored master; do not add incomplete `known-sentinel` lines by hand.

Sentinel rewrites its configuration as topology changes. Mount the **directory**, rather than a single file, and make both the directory and file writable by the Redis user in the selected image. Run this on each node after creating its configuration:

```bash
REDIS_UID="$(docker run --rm --entrypoint id redis:7.2-alpine -u redis)"
REDIS_GID="$(docker run --rm --entrypoint id redis:7.2-alpine -g redis)"
sudo chown -R "$REDIS_UID:$REDIS_GID" /docker-deployments/redis-cluster/sentinel{1,2,3}
chmod 750 /docker-deployments/redis-cluster/sentinel{1,2,3}
sudo find /docker-deployments/redis-cluster/sentinel{1,2,3} -maxdepth 1 -type f -name sentinel.conf -exec chmod 640 {} +
```

Apply the file mode only to configuration files present on that node. Keep the directories persistent across service restarts. The example retains the original Redis 7.2 image family; review its supported patch level before deployment.

---

## docker-compose.yml (Docker Stack)

```yaml
version: '3.8'

services:
  redis1:
    image: redis:7.2-alpine
    command: redis-server --port 6380 --appendonly yes --replica-announce-ip 172.16.207.198 --replica-announce-port 6380
    deploy:
      placement:
        constraints:
          - node.labels.redis_node == redis-1
    ports:
      - target: 6380
        published: 6380
        protocol: tcp
        mode: host
    volumes:
      - redis_data1:/data

  redis2:
    image: redis:7.2-alpine
    command: redis-server --port 6381 --appendonly yes --replica-announce-ip 172.16.207.199 --replica-announce-port 6381
    deploy:
      placement:
        constraints:
          - node.labels.redis_node == redis-2
    ports:
      - target: 6381
        published: 6381
        protocol: tcp
        mode: host
    volumes:
      - redis_data2:/data

  redis3:
    image: redis:7.2-alpine
    command: redis-server --port 6382 --appendonly yes --replica-announce-ip 172.16.207.200 --replica-announce-port 6382
    deploy:
      placement:
        constraints:
          - node.labels.redis_node == redis-3
    ports:
      - target: 6382
        published: 6382
        protocol: tcp
        mode: host
    volumes:
      - redis_data3:/data

  sentinel1:
    image: redis:7.2-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
    deploy:
      placement:
        constraints:
          - node.labels.redis_node == redis-1
    ports:
      - target: 26380
        published: 26380
        protocol: tcp
        mode: host
    volumes:
      - /docker-deployments/redis-cluster/sentinel1:/etc/redis

  sentinel2:
    image: redis:7.2-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
    deploy:
      placement:
        constraints:
          - node.labels.redis_node == redis-2
    ports:
      - target: 26381
        published: 26381
        protocol: tcp
        mode: host
    volumes:
      - /docker-deployments/redis-cluster/sentinel2:/etc/redis

  sentinel3:
    image: redis:7.2-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
    deploy:
      placement:
        constraints:
          - node.labels.redis_node == redis-3
    ports:
      - target: 26382
        published: 26382
        protocol: tcp
        mode: host
    volumes:
      - /docker-deployments/redis-cluster/sentinel3:/etc/redis

volumes:
  redis_data1:
  redis_data2:
  redis_data3:
```

---

## Setting Up Redis Replication

Deploy the stack from a manager after labeling the nodes and preparing the files:

```bash
docker stack deploy -c docker-compose.yml redis-ha
docker stack services redis-ha
```

The published ports are reachable on the node running each service. The replica announce settings are needed in addition to Sentinel's own announce settings; publishing a port does not rewrite the addresses Redis reports.

```bash
redis-cli -h 172.16.207.199 -p 6381 REPLICAOF 172.16.207.198 6380
redis-cli -h 172.16.207.200 -p 6382 REPLICAOF 172.16.207.198 6380
```

---

## Verification

### Master status

```bash
redis-cli -h 172.16.207.198 -p 6380 info replication
```

Expected:

```
role:master
connected_slaves:2
slave0:ip=172.16.207.199,port=6381,state=online
slave1:ip=172.16.207.200,port=6382,state=online
```

### Sentinel status

```bash
redis-cli -h 172.16.207.198 -p 26380 info sentinel
```

Expected:

```
sentinel_masters:1
master0:name=mymaster,status=ok,address=172.16.207.198:6380,slaves=2,sentinels=3
```

---

## Key Takeaways

1. `announce-ip` and `announce-port` must reflect the host's real reachable IP.
2. Ports must be published using host mode.
3. Services must be pinned with node labels.
4. Sentinel config files must be mounted with correct permissions.
## Operational checks

Confirm that clients outside the Swarm can reach every announced Redis and Sentinel address, then test a controlled master failover. Sentinel discovery must return an address reachable by those clients. Keep Redis and Sentinel ports on trusted network paths, and use the authentication and transport settings appropriate to the deployment.

From the same network as the application, query the master address and replica inventory:

```bash
redis-cli -h 172.16.207.198 -p 26380 SENTINEL get-master-addr-by-name mymaster
redis-cli -h 172.16.207.198 -p 26380 SENTINEL replicas mymaster
redis-cli -h 172.16.207.198 -p 26380 SENTINEL ckquorum mymaster
```

Initially, discovery should return `172.16.207.198` and `6380`. The replica inventory should advertise the other two host IP/port pairs, not container-only addresses. Repeat master discovery against the other two Sentinel endpoints. In an isolated failover rehearsal, confirm that discovery changes to the promoted replica and that a Sentinel-aware client reconnects. A quorum check alone does not prove application failover. Recheck the writable Sentinel files and replication roles after a restart; the manual `REPLICAOF` setup above is a bootstrap step, not a complete lifecycle controller.

For another data-protection workflow, see [scheduled APISIX ETCD backups](/posts/apisix-etcd-backup-to-remote-server/). HA and backup recovery address different failure cases; verify both for the service you operate.
