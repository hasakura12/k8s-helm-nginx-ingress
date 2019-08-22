# Create Helm Chart for the Nginx container

Index
- [Create and Configure Helm Chart](#create)
- [Deploy Helm Chart](#deploy)
- [How to Test](#test)
- [Refs](#refs)

This repo is based on the Nginx docker image created in [/docker](/docker) folder.

What this repo does is to package up the dockerlized Nginx into a Helm Chart so that deploying it onto Kubernetes cluster in the form of K8s deployment and service becomes easier.

## Create and Configure Helm Chart <a name="create"></a>
```
helm create reverse-proxy
```
Four yaml files are configured.
- [deployment.yaml](reverse-proxy/templates/deployment.yaml)
- [service.yaml](reverse-proxy/templates/service.yaml)
- [horizontal-pod-autoscaler.yaml](reverse-proxy/templates/horizontal-pod-autoscaler.yaml)
- [values.yaml](reverse-proxy/values.yaml)

For detailed explanations and walkthrough of K8s template configurations, refer to [update/rolling update and autoscaling section of main README.md](../README.md#k8s_nginx_sli).

Check syntax
```
helm lint reverse-proxy/
```
should return
```
==> Linting reverse-proxy/
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, no failures
```
Simulate installation
```
helm install reverse-proxy/ --debug --dry-run
```
should return:
```
[debug] Created tunnel using local port: '54096'

[debug] SERVER: "127.0.0.1:54096"

[debug] Original chart version: ""
[debug] CHART PATH: /Users/hisashi.asakura/SoftwareDevelopment/sandbox/k8s/nginx-ingress/helm/reverse-proxy

NAME:   mortal-kudu
REVISION: 1
RELEASED: Wed Aug 21 19:51:54 2019
CHART: reverse-proxy-0.1.0
USER-SUPPLIED VALUES:
{}

COMPUTED VALUES:
affinity: {}
deployment:
  backendService:
    containerPort: 8080
    name: backend
  monitoringService:
    containerPort: 8081
    name: monitoring
fullnameOverride: ""
image:
  pullPolicy: IfNotPresent
  repository: hasakura12/nginx-reverse-proxy
  tag: "1.00"
imagePullSecrets: []
ingress:
  annotations: {}
  enabled: false
  hosts:
  - host: chart-example.local
    paths: []
  tls: []
livenessProbe:
  path: /healthz
  port: 8080
nameOverride: ""
nodeSelector: {}
readinessProbe:
  path: /healthz
  port: 8080
replicaCount: 1
resources: {}
service:
  backendService:
    name: backend
    nodePort: 30050
    port: 8080
    targetPort: 8080
  monitoringService:
    name: monitoring
    nodePort: 30051
    port: 8081
    targetPort: 8081
  type: NodePort
tolerations: []

HOOKS:
---
# mortal-kudu-reverse-proxy-test-connection
apiVersion: v1
kind: Pod
metadata:
  name: "mortal-kudu-reverse-proxy-test-connection"
  labels:
    app.kubernetes.io/name: reverse-proxy
    helm.sh/chart: reverse-proxy-0.1.0
    app.kubernetes.io/instance: mortal-kudu
    app.kubernetes.io/version: "1.0"
    app.kubernetes.io/managed-by: Tiller
  annotations:
    "helm.sh/hook": test-success
spec:
  containers:
    - name: wget
      image: busybox
      command: ['wget']
      args:  ['mortal-kudu-reverse-proxy:']
  restartPolicy: Never
MANIFEST:

---
# Source: reverse-proxy/templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: mortal-kudu-reverse-proxy
  labels:
    app.kubernetes.io/name: reverse-proxy
    helm.sh/chart: reverse-proxy-0.1.0
    app.kubernetes.io/instance: mortal-kudu
    app.kubernetes.io/version: "1.0"
    app.kubernetes.io/managed-by: Tiller
spec:
  type: NodePort
  ports:
    - port: 8080
      targetPort: 8080
      protocol: TCP
      name: backend
      nodePort: 30050
    - port: 8081
      targetPort: 8081
      protocol: TCP
      name: monitoring
      nodePort: 30051
  selector:
    app.kubernetes.io/name: reverse-proxy
    app.kubernetes.io/instance: mortal-kudu
---
# Source: reverse-proxy/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mortal-kudu-reverse-proxy
  labels:
    app.kubernetes.io/name: reverse-proxy
    helm.sh/chart: reverse-proxy-0.1.0
    app.kubernetes.io/instance: mortal-kudu
    app.kubernetes.io/version: "1.0"
    app.kubernetes.io/managed-by: Tiller
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: reverse-proxy
      app.kubernetes.io/instance: mortal-kudu
  template:
    metadata:
      labels:
        app.kubernetes.io/name: reverse-proxy
        app.kubernetes.io/instance: mortal-kudu
    spec:
      containers:
        - name: reverse-proxy
          image: "hasakura12/nginx-reverse-proxy:1.00"
          imagePullPolicy: IfNotPresent
          ports:
            - name: backend
              containerPort: 8080
              protocol: TCP
            - name: monitoring
              containerPort: 8081
              protocol: TCP
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8080
          resources:
            {}
```

## Deploy Helm Chart <a name="deploy"></a>
Given that a Kubernetes cluster is up and running (e.g. `minikube start`), and Helm tiller server is deployed (e.g. 'helm init`), execute
```
helm install -n nginx-reverse-proxy --namespace dev reverse-proxy/
```
should return 
```
NAME:   nginx-reverse-proxy
LAST DEPLOYED: Wed Aug 21 19:53:32 2019
NAMESPACE: dev
STATUS: DEPLOYED

RESOURCES:
==> v1/Deployment
NAME                 READY  UP-TO-DATE  AVAILABLE  AGE
nginx-reverse-proxy  0/1    1           0          0s

==> v1/Pod(related)
NAME                                  READY  STATUS             RESTARTS  AGE
nginx-reverse-proxy-774d6c4d49-77n4g  0/1    ContainerCreating  0         0s

==> v1/Service
NAME                 TYPE      CLUSTER-IP    EXTERNAL-IP  PORT(S)                        AGE
nginx-reverse-proxy  NodePort  10.107.65.64  <none>       8080:30050/TCP,8081:30051/TCP  1s


NOTES:
1. Get the application URL by running these commands:
  export NODE_PORT=$(kubectl get --namespace dev -o jsonpath="{.spec.ports[0].nodePort}" services nginx-reverse-proxy)
  export NODE_IP=$(kubectl get nodes --namespace dev -o jsonpath="{.items[0].status.addresses[0].address}")
  echo http://$NODE_IP:$NODE_PORT
```

## How to Test <a name="test"></a>
Hit the Nginx reverse proxy's backend service endpoint
```
curl $(minikube ip):30050/healthz
```
should return
```
Hello from /healthz
```

Hit the Nginx reverse proxy's monitoring endpoint
```
curl $(minikube ip):30051/healthz
```
should return
```
Active connections: 1
server accepts handled requests
 47 47 47
Reading: 0 Writing: 1 Waiting: 0
```

## Refs <a name="refs"></a>
- [the official Helm Best Practice](https://helm.sh/docs/chart_best_practices)
- [Writing Your First Helm Chart](https://tech.paulcz.net/blog/getting-started-with-helm/)
- [How To Create Your First Helm Chart](https://docs.bitnami.com/kubernetes/how-to/create-your-first-helm-chart/)
- [Create, Install, Upgrade, and Rollback a Helm Chart](https://dzone.com/articles/create-install-upgrade-and-rollback-a-helm-chart-p)
- [Helm from basics to advanced](https://banzaicloud.com/blog/creating-helm-charts/)