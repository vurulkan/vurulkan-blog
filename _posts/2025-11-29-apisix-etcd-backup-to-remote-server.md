---
title: "Kubernetes CronJob for APISIX ETCD Backup"
date: 2025-11-29 21:00:00 +0300
last_modified_at: 2026-11-09 00:38:58 +0300
description: "Schedule APISIX ETCD snapshots with a Kubernetes CronJob, transfer backups over SFTP and verify job execution before testing disaster recovery."
categories: [DevOps, Kubernetes, Automation]
tags: [k8s, ansible, kubernetes, apisix, api gateway, bash]
toc: true
published: true
robots: index, follow
---

This guide explains how to configure a **Kubernetes CronJob** to back up APISIX's **ETCD data** and transfer it to a remote server via SSH.
[Show project on GitHub](https://github.com/vurulkan/kubernetes/tree/main/apisix-etcd-backup-to-remote-server){:target="_blank"}

## Configuration

Modify the relevant sections in the `etcd-backup-cronjob.yaml` file:

```bash
LOCAL_SERVER="10.42.0.200"
LOCAL_USER="etcdbackup"
LOCAL_PATH="/home/etcdbackup/apisix-etcd-backup"
```
and apisix etcd pod names;
```bash
apisix-main-etcd-0 apisix-main-etcd-1 apisix-main-etcd-2
```
## Generating an SSH Key Pair

```bash
ssh-keygen
```

## Adding the Private Key to Kubernetes

```bash
kubectl create secret generic sftp-secret --from-file=id_rsa=./path/to/privatekey -n yournamespace
```

## Configuring SSH Access on the Remote Server
```bash
cat path/to/publickey >> /home/$USER/.ssh/authorized_keys
```

| Example Public Key  | Example Private Key |
| ------------- | ------------- |
| ssh-ed25519 AAAAC... mustafav@vurulkan.local  | -----BEGIN OPENSSH PRIVATE KEY----- b3BlbnNzaC1... -----END OPENSSH PRIVATE KEY-----  |


## Deploying Kubernetes Resources
### Apply the Service Account

```bash
kubectl apply -f kubernetes-service-account.yaml -n yournamespace
```

### Deploy the CronJob
```bash
kubectl apply -f etcd-backup-cronjob.yaml -n yournamespace
```

## Verify the CronJob Execution

Manually trigger the CronJob and check the logs:
```bash
JOB="etcd-backup-manual-$(date +%s)"
kubectl create job "$JOB" --from=cronjob/etcd-backup-cronjob -n yournamespace
kubectl logs -f "job/$JOB" -n yournamespace
```

## Backup validation and deployment notes

Use the same namespace consistently in the CronJob, ServiceAccount, Secret and the script's internal `kubectl` commands; the repository example uses `ingress` internally. The manual command above creates a uniquely named Job, and its logs must be read from that Job rather than from the CronJob name. A successful run should save the snapshot and complete its SFTP transfer. Confirm the remote file exists and has the expected size.

The example transfer script disables SSH host-key checking. Before production, mount a verified `known_hosts` file and enable strict host-key checking for the destination. Give the backup ServiceAccount and remote user only the access needed for this workflow.

Test recovery with the ETCD version and TLS settings used by your APISIX deployment. Inspect the saved snapshot and rehearse restoration in an isolated environment; a successful upload alone does not demonstrate recovery. See the [ETCD disaster recovery guide](https://etcd.io/docs/v3.6/op-guide/recovery/) for snapshot inspection and restore behavior.

## Related notes

- [Kubernetes OpenConsole](/posts/kubernetes-openconsole-dashboard-ui/) for workload visibility and CronJob/Job logs.
- [Kubernetes HA on Ubuntu](/posts/ansible-k8s-ha-cluster-ubuntu/) for the surrounding cluster deployment.
