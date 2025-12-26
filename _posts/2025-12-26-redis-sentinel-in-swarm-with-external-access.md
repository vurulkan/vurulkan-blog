---
title: "Setting Up a Redis Sentinel Cluster on Docker Swarm with External Access"
date: 2025-12-26 02:00:00 +0300
categories: [DevOps, Docker]
tags: [redis, docker, swarm, docker swarm]
toc: true
---

# Setting Up a Redis Sentinel Cluster on Docker Swarm with External Access

Redis Sentinel works well for high availability, but running it on Docker Swarm introduces a common issue: Sentinel may announce an internal IP that external clients cannot reach. This becomes a problem when applications outside the Swarm try to connect to Sentinel and discover the current Redis master.

This guide shows how to deploy Redis + Sentinel on a 3-node Docker Swarm cluster and ensure that external applications can reliably access the correct Redis instance during failover.

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
mkdir -p /docker-deployments/redis-cluster/
```

### sentinel1.conf

```ini
port 26380
sentinel monitor mymaster 172.16.207.198 6380 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 10000
sentinel parallel-syncs mymaster 1
sentinel announce-ip 172.16.207.198
sentinel announce-port 26380
sentinel known-sentinel mymaster 172.16.207.199 26381
sentinel known-sentinel mymaster 172.16.207.200 26382
```

### sentinel2.conf

```ini
port 26381
sentinel monitor mymaster 172.16.207.198 6380 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 10000
sentinel parallel-syncs mymaster 1
sentinel announce-ip 172.16.207.199
sentinel announce-port 26381
sentinel known-sentinel mymaster 172.16.207.198 26380
sentinel known-sentinel mymaster 172.16.207.200 26382
```

### sentinel3.conf

```ini
port 26382
sentinel monitor mymaster 172.16.207.198 6380 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 10000
sentinel parallel-syncs mymaster 1
sentinel announce-ip 172.16.207.200
sentinel announce-port 26382
sentinel known-sentinel mymaster 172.16.207.198 26380
sentinel known-sentinel mymaster 172.16.207.199 26381
```

### File permissions

```bash
chmod 644 /docker-deployments/redis-cluster/sentinel*.conf
```

---

## docker-compose.yml (Docker Stack)

```yaml
version: '3.8'

services:
  redis1:
    image: redis:7.2-alpine
    command: redis-server --port 6380 --appendonly yes
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
    command: redis-server --port 6381 --appendonly yes
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
    command: redis-server --port 6382 --appendonly yes
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
      - /docker-deployments/redis-cluster/sentinel1.conf:/etc/redis/sentinel.conf

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
      - /docker-deployments/redis-cluster/sentinel2.conf:/etc/redis/sentinel.conf

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
      - /docker-deployments/redis-cluster/sentinel3.conf:/etc/redis/sentinel.conf

volumes:
  redis_data1:
  redis_data2:
  redis_data3:
```

---

## Setting Up Redis Replication

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