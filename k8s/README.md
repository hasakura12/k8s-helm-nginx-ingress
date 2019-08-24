# Get Started With Kubernetes Nginx Ingress Controller
Index
- [Assumptions](#assumptions)
- [Decision Points](#decision_points)
- [Step by Step Guide](#step_by_step)
  - [TL;DR](#tldr)
  - [1. Start Minikube and Enable CNI Network Plugin](#start_minikube)
  - [2. Deploy Nginx Ingress Controller](#deploy_ingress_controller)
    - [a. Minikube addons for Ingress](#ingress_controller_minikube_addon)
    - [b. Manually create Ingress Controller and necessary resources (ConfigMap, ServiceAccount, Secret, etc)](#ingress_controller_manual)
    - [c. Deploy using Helm chart](#ingress_controller_helm_chart)
  - [3. Install Weave CNI Plugin](#install_weave_cni_plugin)
  - [4. Create Deployment and Service for Backend](#create_backend)
  - [5. Deploy Ingress Resouces](#deploy_ingress_resources)
  - [6. Enable Monitoring via K8s Dashboard, Prometheus, and Grafana](#enable_monitoring)
    - [Deploy K8s Dashboard](#k8s_dashboard)
    - [Deploy Prometheus](#prometheus)
    - [Deploy Grafana](#grafana)
    - [Deploy Prometheus and Grafana Manually](#prometheus_grafana_manual)
  - [7. Define and Implement SLI for Nginx](#defnie_sli)
    - [Update/Rollback](#k8s_nginx_sli_update_rollback)
    - [Autoscaling](#k8s_nginx_sli_autoscalling)
    - [How To Test](#k8s_nginx_sli_test)
- [Documentations](#doc)
- [Refs](#refs)

## Assumptions <a name="assumptions"></a>
What we will accomplish is following:
```
my-service.my-company.com -> minikube ip (where Nginx Ingress Controller is running) -> my-service.my-company.com  my-service:9090
```
- Ingress controller listening on port 80, 443, 18080 (these are default)
- Ingress resource (virtual host `my-service.my-company.com` proxies a request to the backend service `my-service` at port 9090)
- Pod's IP CIDR of `10.0.0.0/24`
- Monitoring at port 8081 using Prometheus and Grafana (K8s Dashboard optional)


## Decision Points <a name="decision_points"></a>
Kubernetes has optional _Ingress Controller_ resource which enables a few things when combined with _Ingress_ resource such as:
- load balancing
- reverse proxy
- TLS termination
- name-based virtual hosting

[The Ingress Controller doc](https://kubernetes.io/docs/concepts/services-networking/ingress-controllers/) ([K8s ingress-nginx Git repo](https://github.com/kubernetes/ingress-nginx)) details a variety of choices for Ingress Controller. 

Among them, the following two are maintained and supported by Kubernetes:
- NGINX
- GCE (beta version)

Other well known options are:
- HA Proxy (L4 and L7 load balancing)
- Kong
- Contour
- Traefik

We will use NGINX as it's K8s supported Ingress Controller and satisfies the requirement to load-balance and reverse proxy HTTP traffic.

## Step by Step Guide <a name="step_by_step"></a>
Here are the receipe:
1. Start Minikube and Enable CNI Network Plugin
2. Deploy Nginx Ingress Controller
3. Install Weave CNI Plugin
4. Create Deployment and Service for Backend
5. Deploy Ingress Resouces
6. Enable monitoring via Dashboard, Prometheus, and Grafana


### TL;DR <a name="tldr"></a>
```
## 
## Setup cluster via minikube and enable CNI Plugin
##
$ minikube start \
  --network-plugin=cni \
  --enable-default-cni \
  --extra-config=kubelet.authentication-token-webhook=true

## 
## Ingress Controller
##
$ minikube addons enable ingress
$ minikube addons enable heapster

## 
## Edit Ingress Controller
##
$ kubectl edit deploy \
  nginx-ingress-controller \
  -n kube-system

# Then add the last line "hostNetwork: true" 
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
spec:
  template:
    spec:
      hostNetwork: true

## 
## Deploy Weave CNI 
##
$ kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$(kubectl version | base64 | tr -d '\n')&env.IPALLOC_RANGE=10.0.0.0/24"


## Deploy metric-server
$ kubectl apply -f metrics-server/deploy/1.8+

## 
## Backend Deployment & Service
##
$ kubectl create namespace dev
$ kubectl apply -f k8s/echo-server/deployment.yaml
$ kubectl apply -f k8s/echo-server/service.yaml
$ kubectl apply -f k8s/echo-server/horizontal-pod-autoscaler.yaml

$ curl $(minikube service my-service -n dev --url)

## 
## Ingress Resource
##
$ kubectl apply -f k8s/ingress-resources/ingress.yaml

## 
## Verify the Nginx Ingress Controller is reachable
##

## WARNING: make sure there is no dupliate entry for my-service.my-company.com!!
$ echo "$(minikube ip) my-service.my-company.com" | sudo tee -a /etc/hosts
$ curl my-service.my-company.com

## 
## Deploy Prometheus & Grafana via Helm chart
##
$ helm init
$ helm repo update
$ helm install stable/prometheus \
    --name prometheus \
    --namespace prometheus
$ helm install stable/grafana \
    --name grafana \
    --namespace grafana \
    --set adminPassword="admin" \
    --set datasources."datasources\.yaml".apiVersion=1 \
    --set datasources."datasources\.yaml".datasources[0].name=Prometheus \
    --set datasources."datasources\.yaml".datasources[0].type=prometheus \
    --set datasources."datasources\.yaml".datasources[0].url=http://prometheus-server.prometheus.svc.cluster.local \
    --set datasources."datasources\.yaml".datasources[0].access=proxy \
    --set datasources."datasources\.yaml".datasources[0].isDefault=true 

## 
## Verify Grafana Dashboard is working
##
$ export GRAFANA_POD_NAME=$(kubectl get pods --namespace grafana -l "app=grafana,release=grafana" -o jsonpath="{.items[0].metadata.name}")
$ kubectl --namespace grafana port-forward $GRAFANA_POD_NAME 8081:3000
```
Visit the URL. Username and password is `admin`.
```
localhost:8081
```
End results
![alt text](../imgs/grafana.png "Grafana Dashboard")
And kubernetes cluster should look like
```
$ kubectl get service,deployment,hpa --all-namespaces

NAMESPACE     NAME                                    TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)                         AGE
default       service/kubernetes                      ClusterIP   10.96.0.1        <none>        443/TCP                         42m
dev           service/my-service                      NodePort    10.110.240.111   <none>        9090:32724/TCP                  17m
dev           service/nginx-reverse-proxy             NodePort    10.111.180.201   <none>        8080:30050/TCP,8081:30051/TCP   36m
grafana       service/grafana                         ClusterIP   10.107.244.170   <none>        80/TCP                          13m
kube-system   service/heapster                        ClusterIP   10.106.6.160     <none>        80/TCP                          42m
kube-system   service/kube-dns                        ClusterIP   10.96.0.10       <none>        53/UDP,53/TCP,9153/TCP          42m
kube-system   service/metrics-server                  ClusterIP   10.98.219.109    <none>        443/TCP                         39m
kube-system   service/monitoring-grafana              NodePort    10.98.200.43     <none>        80:30002/TCP                    42m
kube-system   service/monitoring-influxdb             ClusterIP   10.104.6.8       <none>        8083/TCP,8086/TCP               42m
kube-system   service/tiller-deploy                   ClusterIP   10.111.58.93     <none>        44134/TCP                       40m
prometheus    service/prometheus-alertmanager         ClusterIP   10.101.132.147   <none>        80/TCP                          15m
prometheus    service/prometheus-kube-state-metrics   ClusterIP   None             <none>        80/TCP                          15m
prometheus    service/prometheus-node-exporter        ClusterIP   None             <none>        9100/TCP                        15m
prometheus    service/prometheus-pushgateway          ClusterIP   10.97.58.9       <none>        9091/TCP                        15m
prometheus    service/prometheus-server               ClusterIP   10.100.120.232   <none>        80/TCP                          15m

NAMESPACE     NAME                                            READY   UP-TO-DATE   AVAILABLE   AGE
dev           deployment.apps/echo-server                     2/2     2            2           18m
dev           deployment.apps/nginx-reverse-proxy             2/2     2            2           36m
grafana       deployment.apps/grafana                         1/1     1            1           13m
kube-system   deployment.apps/coredns                         2/2     2            2           42m
kube-system   deployment.apps/metrics-server                  1/1     1            1           39m
kube-system   deployment.apps/nginx-ingress-controller        1/1     1            1           42m
kube-system   deployment.apps/tiller-deploy                   1/1     1            1           40m
prometheus    deployment.apps/prometheus-alertmanager         1/1     1            1           15m
prometheus    deployment.apps/prometheus-kube-state-metrics   1/1     1            1           15m
prometheus    deployment.apps/prometheus-pushgateway          1/1     1            1           15m
prometheus    deployment.apps/prometheus-server               1/1     1            1           15m

NAMESPACE   NAME                                                      REFERENCE                        TARGETS   MINPODS   MAXPODS   REPLICAS   AGE
dev         horizontalpodautoscaler.autoscaling/echo-server           Deployment/echo-server           0%/50%    2         5         2          17m
dev         horizontalpodautoscaler.autoscaling/nginx-reverse-proxy   Deployment/nginx-reverse-proxy   2%/50%    2         5         2          36m
```


Let's get started.

### 1. Start Minikube and Enable CNI Network Plugin <a name="start_minikube"></a>
Since we want to specify a Pod IP range, let's enable cni:
```
$ minikube start \
  --network-plugin=cni \
  --enable-default-cni \
  --extra-config=kubelet.authentication-token-webhook=true
```

However, Minikube Ingress doesn't work with CNI plugin (a known issue [here](https://github.com/kubernetes/minikube/issues/1987), [here](https://github.com/kubernetes/minikube/issues/2840), and [here](https://stackoverflow.com/questions/55891795/is-ingress-useable-only-for-minikube-it-is-not-working-in-ubuntu-installation)), so need to add a workaround by applying `spec.template.spec.hostNetwork = true` in a deployment.yaml for nginx-ingress-controller.

```
$ kubectl edit deploy \
  nginx-ingress-controller \
  -n kube-system
```
then add
```
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
spec:
  template:
    spec:
      hostNetwork: true
```

### 2. Deploy Nginx Ingress Controller <a name="deploy_ingress_controller"></a>
We have two ways to deploy Ingress Controller:
- Minikube addons for Ingress
- Manually create Ingress Controller and necessary resources (ConfigMap, ServiceAccount, Secret, etc)
- Deploy using Helm chart (easiest)

The official docs ["Set up Ingress on Minikube with the NGINX Ingress Controller"](https://kubernetes.io/docs/tasks/access-application-cluster/ingress-minikube/) and [Kubernetes Nginx Ingress Controller Installation Guide](https://kubernetes.github.io/ingress-nginx/deploy/#minikube) guides you through the steps to deploy the Nginx Ingress Controller.

#### a. Minikube addons for Ingress <a name="ingress_controller_minikube_addon"></a>
An easier way is to just enable ingress addons for minikube.

```
$ minikube addons enable ingress
```
will create necessary resources such as:
- Ingress Controller
- Ingress service
- configmap
- service account
- secret

#### b. Manually create Ingress Controller and necessary resources (ConfigMap, ServiceAccount, Secret, etc) <a name="ingress_controller_manual"></a>
Alternatively, we could deploy them one by one as per [the Nginx Github - Kubernetes Ingress Controller Installation](https://github.com/nginxinc/kubernetes-ingress/blob/master/docs/installation.md).

#### c. Deploy using Helm chart <a name="ingress_controller_helm_chart"></a>
Refs:
- [Kubernetes Nginx Ingress Controller - Installation Guide using Helm](https://kubernetes.github.io/ingress-nginx/deploy/#using-helm)
- [Github Helm Chart for Nginx Ingress](https://github.com/helm/charts/tree/master/stable/nginx-ingress)
- [Setup Nginx INgress on K8s using Helm](https://www.digitalocean.com/community/tutorials/how-to-set-up-an-nginx-ingress-on-digitalocean-kubernetes-using-helm)

### 3. Install Weave CNI Plugin <a name="install_weave_cni_plugin"></a>
We will specify a Pod IP range using `weave` cni plugin and passing a IP range variable.

Install `weave` network plugin and set pod IP range `10.0.0.0/24` by passing an environment value for weave network plugin ([the doc](https://github.com/weaveworks/weave/blob/master/site/kubernetes/kube-addon.md)):
```
$ kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$(kubectl version | base64 | tr -d '\n')&env.IPALLOC_RANGE=10.0.0.0/24"
```
Confirm the `--ipalloc-range` argument for `weave` service is properly set:
```
$ minikube ssh
$ ps aux | grep weaver | grep range
root     16186  1.3  3.9 408936 79100 ?        Sl   17:07   0:00 /home/weave/weaver --port=6783 --datapath=datapath --name=ba:ca:44:b3:a3:d9 --host-root=/host --http-addr=127.0.0.1:6784 --metrics-addr=0.0.0.0:6782 --docker-api= --no-dns --db-prefix=/weavedb/weave-net --ipalloc-range=10.0.0.0/24 --nickname=minikube --ipalloc-init consensus=1 --conn-limit=100 --expect-npc 10.0.2.15
```
and the line `--ipalloc-range=10.0.0.0/24` confirms the correct config for pod IP range.

### 4. Create Deployment and Service for Backend <a name="create_backend"></a>
```
$ kubectl create namespace dev
$ kubectl apply -f k8s/echo-server/deployment.yaml
$ kubectl apply -f k8s/echo-server/service.yaml
```
##### note: yaml could be generated by running
```
$ kubectl run echo-server \
  --image=gcr.io/kubernetes-e2e-test-images/echoserver:2.1 \
  --port=8080 \
  --expose \
  --dry-run \
  -o yaml
```
and then manually add `namespace: dev` under `metadata` since `kubectl run` doesn't accept `namespace` argument.

Confirm pods are running with a correct IP range `10.0.0.0/24`:
```
$ kubectl get pod -o wide -n dev

NAME                          READY   STATUS    RESTARTS   AGE   IP         NODE       NOMINATED NODE   READINESS GATES
echo-server-d7d4b5b46-22wkx   1/1     Running   0          68s   10.0.0.3   minikube   <none>           <none>
echo-server-d7d4b5b46-625nr   1/1     Running   0          68s   10.0.0.2   minikube   <none>           <none>
```

Get the endpoint through the nodeport:
```
$ curl $(minikube service echo-server-svc -n dev --url)

Hostname: echo-server-74dc9b7fc8-ctxxr

Pod Information:
	-no pod information available-

Server values:
	server_version=nginx: 1.12.2 - lua: 10010

Request Information:
	client_address=10.0.0.1
	method=GET
	real path=/
	query=
	request_version=1.1
	request_scheme=http
	request_uri=http://192.168.99.104:8080/

Request Headers:
	accept=*/*
	host=192.168.99.104:30777
	user-agent=curl/7.54.0

Request Body:
	-no body in request-
```
Notice
```
Request Information:
	client_address=10.0.0.1
  ...
  request_uri=http://192.168.99.104:8080/
```
and 
```
Request Headers:
	accept=*/*
	host=192.168.99.104:30777
```
`192.168.99.104` is the minikube IP:
```
$ minikube ip
192.168.99.104
```
and the port 30777 is the service's nodeport:
```
# get service's exposed nodeport
$ kubectl get service echo-server-svc -n dev
NAME              TYPE       CLUSTER-IP       EXTERNAL-IP   PORT(S)          AGE
echo-server-svc   NodePort   10.102.237.192   <none>        9090:30777/TCP   9m15s
```
##### ref: The doc "[Source IP for Services with Type=NodePort](https://kubernetes.io/docs/tutorials/services/source-ip/#source-ip-for-services-with-type-nodeport)"

### 5. Deploy Ingress Resouces <a name="deploy_ingress_resources"></a>
```
$ kubectl apply -f k8s/ingress-resources/ingress.yaml
```
Verify
```
$ kubectl get ingress -o wide -n dev

NAME                  HOSTS            ADDRESS   PORTS   AGE
echo-server-ingress   my-company.com             80      12s
```
```
$ kubectl describe ingress echo-server-ingress -n dev
```

Add host-IP mapping to `/etc/host` (necessary if running K8s cluster on minikube)
```
$ echo "$(minikube ip) my-service.my-company.com" | sudo tee -a /etc/hosts
```

Verify you can hit the endpoint via the hostname:
```
$ curl my-service.my-company.com
Hostname: echo-server-d7d4b5b46-tkjfb

Pod Information:
	-no pod information available-

Server values:
	server_version=nginx: 1.12.2 - lua: 10010

Request Information:
	client_address=10.0.0.1
	method=GET
	real path=/
	query=
	request_version=1.1
	request_scheme=http
	request_uri=http://my-service.my-company.com:8080/

Request Headers:
	accept=*/*
	host=my-service.my-company.com
	user-agent=curl/7.54.0
	x-forwarded-for=192.168.99.1
	x-forwarded-host=my-service.my-company.com
	x-forwarded-port=80
	x-forwarded-proto=http
	x-original-uri=/
	x-real-ip=192.168.99.1
	x-request-id=108d12f2cdc5fae89baa68633bd09486
	x-scheme=http

Request Body:
	-no body in request-
```

##### note: you can't `curl $(minikube ip)` and get a response because in the ingress.yaml, it explicitely listens to the host name:
```
spec:
  rules:
  - host: my-service.my-company.com
```

### 6. Enable Monitoring via K8s Dashboard, Prometheus, and Grafana <a name="enable_monitoring"></a>
- Deploy K8s Dashboard
- Deploy using Helm chart
  - Install Helm
    - for RBAC user
    - for NON-RBAC user
  - Deploy Prometheus
  - Deploy Grafana
- Deploy manually via `kubectl`

#### Deploy K8s Dashboard <a name="k8s_dashboard"></a>
Refs:
- [Deploying the Dashboard UI](https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/#deploying-the-dashboard-ui)
- [Github Kubernetes Dashboard - Creating sample user](https://github.com/kubernetes/dashboard/wiki/Creating-sample-user)
- [eks workshop - deploy official dashboard](https://eksworkshop.com/dashboard/dashboard/)

Dashboard doesn't come with a cluster by default. We need to deploy it.

```
$ kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v1.10.1/src/deploy/recommended/kubernetes-dashboard.yaml
$ kubectl apply -f k8s/dashboard/service-account.yaml
$ kubectl apply -f k8s/dashboard/cluster-role-binding.yaml

$ kubectl -n kube-system describe secret $(kubectl -n kube-system get secret | grep admin-user | awk '{print $1}')

Name:         admin-user-token-22hpd
Namespace:    kube-system
Labels:       <none>
Annotations:  kubernetes.io/service-account.name: admin-user
              kubernetes.io/service-account.uid: 96e2c6cb-58e1-4737-b723-b93439ba94c6

Type:  kubernetes.io/service-account-token

Data
====
ca.crt:     1066 bytes
namespace:  11 bytes
token:      eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJhZG1pbi11c2VyLXRva2VuLTIyaHBkIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImFkbWluLXVzZXIiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiI5NmUyYzZjYi01OGUxLTQ3MzctYjcyMy1iOTM0MzliYTk0YzYiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6a3ViZS1zeXN0ZW06YWRtaW4tdXNlciJ9.LL2GJkW1biUV_kVHfTv2_B-5NmYr8FEtEMsNpie34MKrom2ionVcuh3KYZ48Px_bSVvheI0QTn35qE4X8NZQ7M5PlquLcsuHUM9COk7b5CzSFJHq5LTTvfxQ5UCa7YFFxce9DJ_FSLXDZrbhgyo3yPeGjbRF77aRsTmh7jwSWCi2OS9JZE5165zwRhGFTj4-ttDZ5MD7dPzUQG3Gwy1XkyvFJPteWN8ukgxMl11SBiN-Qr-anJIoKqBJ255pSzob02C2rEMwHZ2pjO3x4qCEqlR8M8JMWfnHCfSYhb1xvLR4KzOTedv6EZ_uuLJSc2RN5ql4al9E6l0_urM-gYDpNA
```
Copy the token value
```
token:      eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJhZG1pbi11c2VyLXRva2VuLTIyaHBkIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImFkbWluLXVzZXIiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiI5NmUyYzZjYi01OGUxLTQ3MzctYjcyMy1iOTM0MzliYTk0YzYiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6a3ViZS1zeXN0ZW06YWRtaW4tdXNlciJ9.LL2GJkW1biUV_kVHfTv2_B-5NmYr8FEtEMsNpie34MKrom2ionVcuh3KYZ48Px_bSVvheI0QTn35qE4X8NZQ7M5PlquLcsuHUM9COk7b5CzSFJHq5LTTvfxQ5UCa7YFFxce9DJ_FSLXDZrbhgyo3yPeGjbRF77aRsTmh7jwSWCi2OS9JZE5165zwRhGFTj4-ttDZ5MD7dPzUQG3Gwy1XkyvFJPteWN8ukgxMl11SBiN-Qr-anJIoKqBJ255pSzob02C2rEMwHZ2pjO3x4qCEqlR8M8JMWfnHCfSYhb1xvLR4KzOTedv6EZ_uuLJSc2RN5ql4al9E6l0_urM-gYDpNA
```
Then access Dashboard
```
$ kubectl proxy --port=8081
Starting to serve on 127.0.0.1:8081
```
Visit the dashboard URL from a browser and paste the token:
```
http://localhost:8081/api/v1/namespaces/kube-system/services/https:kubernetes-dashboard:/proxy/#!/login
```
![alt text](../imgs/dashboard_login.png "Dashboard Login")
![alt text](../imgs/dashboard.png "Dashboard")

#### Install Helm
For installing Helm for RBAC user, check [the official helm doc](https://helm.sh/docs/using_helm/#role-based-access-control) or [eks workshop - install Helm CLI](https://eksworkshop.com/helm_root/helm_intro/install/).
```
$ cat <<EoF > ~/environment/rbac.yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tiller
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: tiller
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: tiller
    namespace: kube-system
EoF

$ kubectl apply -f ~/environment/rbac.yaml
$ helm init --service-account tiller
```

For installing Helm for NON-RBAC user:
```
$ helm init
$ kubectl get all --all-namespaces | grep tiller

kube-system     pod/tiller-deploy-5dc46c877-t99s2               1/1     Running   0          72s
kube-system     service/tiller-deploy       ClusterIP   10.100.151.249   <none>        44134/TCP                72s
kube-system     deployment.apps/tiller-deploy              1/1     1            1           72s
kube-system     replicaset.apps/tiller-deploy-5dc46c877               1         1         1       72s
```

#### Deploy Prometheus <a name="prometheus"></a>
![alt text](../imgs/prometheus_architecture.png "Prometheus Architecture")
Refs: 
- [eksworkshop - deploy Prometheus and Grafana](https://eksworkshop.com/monitoring/)
- [Trying Prometheus Operator with Helm + Minikube](https://medium.com/faun/trying-prometheus-operator-with-helm-minikube-b617a2dccfa3)
- [Kubernetes monitoring with Prometheus in 15 minutes](https://itnext.io/kubernetes-monitoring-with-prometheus-in-15-minutes-8e54d1de2e13)
- [Amazon EKS Control Plane Metrics with Prometheus](https://aws.amazon.com/blogs/opensource/amazon-eks-control-plane-metrics-prometheus/)

```
$ helm repo update
$ helm install stable/prometheus \
    --name prometheus \
    --namespace prometheus
```
which should return
```
NOTES:
The Prometheus server can be accessed via port 80 on the following DNS name from within your cluster:
prometheus-server.prometheus.svc.cluster.local


Get the Prometheus server URL by running these commands in the same shell:
  export POD_NAME=$(kubectl get pods --namespace prometheus -l "app=prometheus,component=server" -o jsonpath="{.items[0].metadata.name}")
  kubectl --namespace prometheus port-forward $POD_NAME 9090
```
Check resources created:
```
$ kubectl get all -n prometheus

NAME                                                 READY   STATUS    RESTARTS   AGE
pod/prometheus-alertmanager-5bc4ccf9df-69d8w         2/2     Running   0          2m53s
pod/prometheus-kube-state-metrics-58bc4f85dd-g6tzb   1/1     Running   0          2m53s
pod/prometheus-node-exporter-qjh5l                   1/1     Running   0          2m53s
pod/prometheus-pushgateway-7ff56774d-5jl8f           1/1     Running   0          2m53s
pod/prometheus-server-584577c559-s4xvv               2/2     Running   0          2m53s

NAME                                    TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)    AGE
service/prometheus-alertmanager         ClusterIP   10.108.88.46     <none>        80/TCP     2m53s
service/prometheus-kube-state-metrics   ClusterIP   None             <none>        80/TCP     2m53s
service/prometheus-node-exporter        ClusterIP   None             <none>        9100/TCP   2m53s
service/prometheus-pushgateway          ClusterIP   10.108.201.112   <none>        9091/TCP   2m53s
service/prometheus-server               ClusterIP   10.101.92.186    <none>        80/TCP     2m53s

NAME                                      DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR   AGE
daemonset.apps/prometheus-node-exporter   1         1         1       1            1           <none>          2m53s

NAME                                            READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/prometheus-alertmanager         1/1     1            1           2m53s
deployment.apps/prometheus-kube-state-metrics   1/1     1            1           2m53s
deployment.apps/prometheus-pushgateway          1/1     1            1           2m53s
deployment.apps/prometheus-server               1/1     1            1           2m53s

NAME                                                       DESIRED   CURRENT   READY   AGE
replicaset.apps/prometheus-alertmanager-5bc4ccf9df         1         1         1       2m53s
replicaset.apps/prometheus-kube-state-metrics-58bc4f85dd   1         1         1       2m53s
replicaset.apps/prometheus-pushgateway-7ff56774d           1         1         1       2m53s
replicaset.apps/prometheus-server-584577c559               1         1         1       2m53s
```
Enable port forwarding:
```
$ export PROMETHEUS_POD_NAME=$(kubectl get pods --namespace prometheus -l "app=prometheus,component=server" -o jsonpath="{.items[0].metadata.name}")

$ kubectl --namespace prometheus port-forward $PROMETHEUS_POD_NAME 8081:9090
```
Access Prometheus dashboard:
```
localhost:8081
```
![alt text](../imgs/prometheus.png "Prometheus Dashboard")

#### Deploy Grafana <a name="grafana"></a>
Refs: 
- [eksworkshop - deploy Prometheus and Grafana](https://eksworkshop.com/monitoring/)
- [Kubernetes monitoring with Prometheus in 15 minutes](https://itnext.io/kubernetes-monitoring-with-prometheus-in-15-minutes-8e54d1de2e13)

```
$ helm install stable/grafana \
    --name grafana \
    --namespace grafana \
    --set adminPassword="admin" \
    --set datasources."datasources\.yaml".apiVersion=1 \
    --set datasources."datasources\.yaml".datasources[0].name=Prometheus \
    --set datasources."datasources\.yaml".datasources[0].type=prometheus \
    --set datasources."datasources\.yaml".datasources[0].url=http://prometheus-server.prometheus.svc.cluster.local \
    --set datasources."datasources\.yaml".datasources[0].access=proxy \
    --set datasources."datasources\.yaml".datasources[0].isDefault=true 
```
which should return
```
NOTES:
1. Get your 'admin' user password by running:

   kubectl get secret --namespace grafana grafana -o jsonpath="{.data.admin-password}" | base64 --decode ; echo

2. The Grafana server can be accessed via port 80 on the following DNS name from within your cluster:

   grafana.grafana.svc.cluster.local

   Get the Grafana URL to visit by running these commands in the same shell:

     export POD_NAME=$(kubectl get pods --namespace grafana -l "app=grafana,release=grafana" -o jsonpath="{.items[0].metadata.name}")
     kubectl --namespace grafana port-forward $POD_NAME 3000

3. Login with the password from step 1 and the username: admin
```
Enable port forwarding:
```
$ export GRAFANA_POD_NAME=$(kubectl get pods --namespace grafana -l "app=grafana,release=grafana" -o jsonpath="{.items[0].metadata.name}")

$ kubectl --namespace grafana port-forward $GRAFANA_POD_NAME 8081:3000
```
Access Grafana dashboard:
```
localhost:8081
```
![alt text](../imgs/grafana.png "Grafana Dashboard")

##### Deploy Prometheus and Grafana Manually <a name="prometheus_grafana_manual"></a>
Ref: [The K8s Nginx Ingress Controller - Prometheus and Grafana Installation](https://kubernetes.github.io/ingress-nginx/user-guide/monitoring/).

Deploy Prometheus:
```
$ kubectl create namespace ingress-nginx
$ kubectl apply --kustomize github.com/kubernetes/ingress-nginx/deploy/prometheus/

serviceaccount/prometheus-server created
role.rbac.authorization.k8s.io/prometheus-server created
rolebinding.rbac.authorization.k8s.io/prometheus-server created
configmap/prometheus-configuration-bc6bcg7b65 created
service/prometheus-server created
deployment.apps/prometheus-server created
```
Visit the dashboard URL
```
$ minikube service prometheus-server -n ingress-nginx --url

http://192.168.99.107:32739
```

Deploy Grafana:
```
$ kubectl apply --kustomize github.com/kubernetes/ingress-nginx/deploy/grafana/

$ minikube service grafana -n ingress-nginx --url

http://192.168.99.107:32538
```

### 7. Define and Implement SLI for Nginx <a name="defnie_sli"></a>
For the backend Pods to be performant, reliable, and scalable, we will define strategies for update, rollback, and scaling in [deployment.yaml](k8s/echo-server/deployment.yaml) and [horizontal-pod-autoscaler.yaml](k8s/echo-server/horizontal-pod-autoscaler.yaml).

For demo purpose, let's define our SLI such that:
- no more than 25% of desired Nginx instance counts should be unavailable during update/rollback
- auto-scale Nginx instance counts by CPU usage when it's over 50%
- there should be no downtime during update/rollback

For the above SLI, we are interested in `rollingUpdate` strategy and `HorizontalPodAutoscaler` resource.

#### Update/Rollback <a name="k8s_nginx_sli_update_rollback"></a>
In [deployment.yaml](k8s/echo-server/deployment.yaml)
```
strategy:
  rollingUpdate:
    maxSurge: 25%
    maxUnavailable: 25%
  type: RollingUpdate
```
This will ensure that at least 75% of the desired number of Pods are up (25% max unavailable) when updating or rolling back.

#### Autoscaling <a name="k8s_nginx_sli_autoscalling"></a>
![alt text](../imgs/horizontal_pod_autoscaler.png "Horizontal Pod Autoscaler")

Ref:
- [K8s Horizontal Pod Autoscaler Walkthrough](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/)
- [Minikube horizontal pod autoscaling error: unable to get metrics for resource cpu: no metrics returned](https://stackoverflow.com/questions/48325627/minikube-horizontal-pod-autoscaling-error-unable-to-get-metrics-for-resource-cp)
- [Docker Kubernetes (Mac) - Autoscaler unable to find metrics](https://stackoverflow.com/questions/54106725/docker-kubernetes-mac-autoscaler-unable-to-find-metrics)

Before we begin with [horizontal-pod-autoscaler.yaml](k8s/echo-server/horizontal-pod-autoscaler.yaml), we need to set up metric-servier so that horizontal pod autoscaler can get pod metrics.

For Minikube, we need to enable `heapster` addons:
```
$ minikube addons enable heapster
```

Next, generate a yaml file for `HorizontalPodAutoscaler`, which is located in [horizontal-pod-autoscaler.yaml](k8s/echo-server/horizontal-pod-autoscaler.yaml)
```
apiVersion: autoscaling/v1
kind: HorizontalPodAutoscaler
metadata:
  creationTimestamp: null
  name: nginx-reverse-proxy
  namespace: dev
spec:
  maxReplicas: 5
  minReplicas: 2
  scaleTargetRef:
    apiVersion: extensions/v1beta1
    kind: Deployment
    name: nginx-reverse-proxy
  targetCPUUtilizationPercentage: 50
status:
  currentReplicas: 0
  desiredReplicas: 0
```
##### note: the yaml can be generated by the below command
```
$ kubectl autoscale deployment nginx-reverse-proxy \
  -n dev \
  --cpu-percent=50 \
  --min=2 \
  --max=5 \
  --dry-run \
  -o yaml \
  > helm/reverse-proxy/templates/horizontal-pod-autoscaler.yaml
```

Also, for HPA to be able to collect metrics, a Pod definition must have request for resources, as mentioned in [the doc](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/).

>Please note that if some of the pod’s containers do not have the relevant resource request set, CPU utilization for the pod will not be defined and the autoscaler will not take any action for that metric.

So in [deployment.yaml](k8s/echo-server/deployment.yaml), add requests for CPU:
```
resources:
  # We usually recommend not to specify default resources and to leave this as a conscious
  # choice for the user. This also increases chances charts run on environments with little
  # resources, such as Minikube. If you do want to specify resources, uncomment the following
  # lines, adjust them as necessary, and remove the curly braces after 'resources:'.
  # limits:
  #   cpu: 100m
  #   memory: 128Mi
  requests:
    cpu: 100m
    memory: 128Mi
```

Finally, we need to deploy metric-server and we could do it by `minikube addons enable metric-server`, but there is a known issue ([Docker Kubernetes (Mac) - Autoscaler unable to find metrics](https://stackoverflow.com/questions/54106725/docker-kubernetes-mac-autoscaler-unable-to-find-metrics)). So we need to have a workaround by editing a deployment.yaml.
```
$ git clone https://github.com/kubernetes-incubator/metrics-server.git
```
Edit the deploy/1.8+/metrics-server-deployment.yaml 
```
containers:
- name: metrics-server
    image: k8s.gcr.io/metrics-server-amd64:v0.3.1
    command:
      - /metrics-server
      - --kubelet-insecure-tls
      - --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname
```
Apply
```
$ kubectl apply -f metrics-server/deploy/1.8+
```
Now metric-server should respond:
```
$ kubectl get --raw /apis/metrics.k8s.io/v1beta1

{"kind":"APIResourceList","apiVersion":"v1","groupVersion":"metrics.k8s.io/v1beta1","resources":[{"name":"nodes","singularName":"","namespaced":false,"kind":"NodeMetrics","verbs":["get","list"]},{"name":"pods","singularName":"","namespaced":true,"kind":"PodMetrics","verbs":["get","list"]}]}
```
Then redeploy the helm chart
```
$ helm del --purge nginx-reverse-proxy
$ helm install -n nginx-reverse-proxy --namespace dev helm/reverse-proxy/
```
Takes about a few minutes before CPU usage is available for horizontal pod autoscaler.
Make sure the TARGET column shows some %, which means a Pod metrics is avaibale.
```
$ kubectl get hpa -n dev nginx-reverse-proxy
NAME                  REFERENCE                        TARGETS   MINPODS   MAXPODS   REPLICAS   AGE
nginx-reverse-proxy   Deployment/nginx-reverse-proxy   1%/50%    2         5         2          3m47s
```

#### How To Test <a name="k8s_nginx_sli_test"></a>
![alt text](../imgs/test_auto_scaling.png "Test Auto Scaling")
From another shell, create another pod and get shell
```
$ kubectl run -i --tty load-generator --image=busybox -n dev /bin/sh
```
Load test the `nginx-reverse-proxy` service from within the pod
```
$ while true; do wget -q -O- http://nginx-reverse-proxy
:8081/nginx_status; done
```

And you will see new replicas being created by scaling up (note: autoscaling takes a few mins)
```
$ kubectl get hpa -n dev nginx-reverse-proxy
NAME                  REFERENCE                        TARGETS   MINPODS   MAXPODS   REPLICAS   AGE
nginx-reverse-proxy   Deployment/nginx-reverse-proxy   71%/50%   2         5         3
```

Note that there is a delay in how fast auto scaling kicks in due to the event loop:
> The Horizontal Pod Autoscaler is implemented as a control loop, with a period controlled by the controller manager’s --horizontal-pod-autoscaler-sync-period flag (with a default value of 15 seconds)

## Documentations <a name="doc"></a>
### Kubernetes Networking <a name="nginx_helm_chart"></a>
- [Kubernetes Networking from CloudNativeLabs](https://cloudnativelabs.github.io/post/2017-04-18-kubernetes-networking/)

### Service IP range <a name="nginx_helm_chart"></a>
Range is set when starting `kube-apiserver` service. 
```
$ ps aux | grep kube-apiserver | grep range
```
which returns the following:
```
root      3243  3.5 13.6 403628 272332 ?       Ssl  14:27   3:29 kube-apiserver --advertise-address=192.168.99.103 --allow-privileged=true --authorization-mode=Node,RBAC --client-ca-file=/var/lib/minikube/certs/ca.crt --enable-admission-plugins=NamespaceLifecycle,LimitRanger,ServiceAccount,DefaultStorageClass,DefaultTolerationSeconds,NodeRestriction,MutatingAdmissionWebhook,ValidatingAdmissionWebhook,ResourceQuota --enable-bootstrap-token-auth=true --etcd-cafile=/var/lib/minikube/certs/etcd/ca.crt --etcd-certfile=/var/lib/minikube/certs/apiserver-etcd-client.crt --etcd-keyfile=/var/lib/minikube/certs/apiserver-etcd-client.key --etcd-servers=https://127.0.0.1:2379 --insecure-port=0 --kubelet-client-certificate=/var/lib/minikube/certs/apiserver-kubelet-client.crt --kubelet-client-key=/var/lib/minikube/certs/apiserver-kubelet-client.key --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname --proxy-client-cert-file=/var/lib/minikube/certs/front-proxy-client.crt --proxy-client-key-file=/var/lib/minikube/certs/front-proxy-client.key --requestheader-allowed-names=front-proxy-client --requestheader-client-ca-file=/var/lib/minikube/certs/front-proxy-ca.crt --requestheader-extra-headers-prefix=X-Remote-Extra- --requestheader-group-headers=X-Remote-Group --requestheader-username-headers=X-Remote-User --secure-port=8443 --service-account-key-file=/var/lib/minikube/certs/sa.pub --service-cluster-ip-range=10.96.0.0/12 --tls-cert-file=/var/lib/minikube/certs/apiserver.crt --tls-private-key-file=/var/lib/minikube/certs/apiserver.key
```
Notice the argument which defines service IP range:
```
--service-cluster-ip-range=10.96.0.0/12
```

`kube-apiserver` service log can be found at
```
/var/log/pods
```

### Pod IP range <a name="nginx_helm_chart"></a>
Range is set when starting `kubelet` service. 
```
$ ps aux | grep kubelet | grep cni
```
which returns the following:
```
root      2885  3.8  4.8 1345656 95752 ?       Ssl  14:27   3:49 /usr/bin/kubelet --authorization-mode=Webhook --bootstrap-kubeconfig=/etc/kubernetes/bootstrap-kubelet.conf --cgroup-driver=cgroupfs --client-ca-file=/var/lib/minikube/certs/ca.crt --cluster-dns=10.96.0.10 --cluster-domain=cluster.local --container-runtime=docker --fail-swap-on=false --hostname-override=minikube --kubeconfig=/etc/kubernetes/kubelet.conf --network-plugin=cni --pod-manifest-path=/etc/kubernetes/manifests
```
Notice the argument which defines a network plugin:
```
--network-plugin=cni 
```
Let's cat the config
```
{
  "cniVersion": "0.3.0",
  "name": "rkt.kubernetes.io",
  "type": "bridge",
  "bridge": "mybridge",
  "mtu": 1460,
  "addIf": "true",
  "isGateway": true,
  "ipMasq": true,
  "ipam": {
    "type": "host-local",
    "subnet": "10.1.0.0/16",
    "gateway": "10.1.0.1",
    "routes": [
      {
        "dst": "0.0.0.0/0"
      }
    ]
  }
}
```
The line `"subnet": "10.1.0.0/16"` defines a CIDR for pods.

### Set Pod IP range <a name="nginx_helm_chart"></a>
[A known issue with minikube extra-config arg for proxy](https://github.com/kubernetes/minikube/issues/4070)
```
$ minikube start \
  --network-plugin=cni \
  --enable-default-cni \
  --extra-config=proxy.ClusterCIDR=10.0.0.0/24 \
  --extra-config=kubelet.PodCIDR=10.0.0.0/24
```

## Refs <a name="nginx_helm_chart"></a>
Articles:
- [Getting Started with Kubernetes Ingress-Nginx on Minikube](https://medium.com/@awkwardferny/getting-started-with-kubernetes-ingress-nginx-on-minikube-d75e58f52b6c)
- [Setting up Nginx Ingress on Kubernetes](https://medium.com/solanz/setting-up-nginx-ingress-on-kubernetes-d86f05af8c7c)
- [How to Set Up Ingress On Kubernetes Using Nginx Controller](https://devopscube.com/setup-ingress-kubernetes-nginx-controller/)
- [How To Set Up an Nginx Ingress on DigitalOcean Kubernetes Using Helm](https://www.digitalocean.com/community/tutorials/how-to-set-up-an-nginx-ingress-on-digitalocean-kubernetes-using-helm)
- [Kubernetes Nginx Ingress Controller](https://akomljen.com/kubernetes-nginx-ingress-controller/)
- [Setting up Ingress on minikube](https://medium.com/@Oskarr3/setting-up-ingress-on-minikube-6ae825e98f82)
- [eksworkshop - deploy Prometheus and Grafana](https://eksworkshop.com/monitoring/)
- [Trying Prometheus Operator with Helm + Minikube](https://medium.com/faun/trying-prometheus-operator-with-helm-minikube-b617a2dccfa3)
- [Kubernetes monitoring with Prometheus in 15 minutes](https://itnext.io/kubernetes-monitoring-with-prometheus-in-15-minutes-8e54d1de2e13)
- [Amazon EKS Control Plane Metrics with Prometheus](https://aws.amazon.com/blogs/opensource/amazon-eks-control-plane-metrics-prometheus/)
- [eks workshop - deploy official dashboard](https://eksworkshop.com/dashboard/dashboard/)

Official Docs:
- [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Kubernetes Nginx Controller Installation Guide](https://kubernetes.github.io/ingress-nginx/deploy/#minikube)
- [Kubernetes Nginx Controller Prometheus and Grafana installation](https://kubernetes.github.io/ingress-nginx/user-guide/monitoring/)
- [Github Helm Chart for Nginx Ingress Controller](https://github.com/helm/charts/tree/master/stable/nginx-ingress)
- [Github Nginx Ingress for K8s](https://github.com/nginxinc/kubernetes-ingress)
- [Kubernetes Nginx Ingress Controller - Installation Guide using Helm](https://kubernetes.github.io/ingress-nginx/deploy/#using-helm)
- [Github Helm Chart for Nginx Ingress](https://github.com/helm/charts/tree/master/stable/nginx-ingress)
- [Deploying the Dashboard UI](https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/#deploying-the-dashboard-ui)
- [Github Kubernetes Dashboard - Creating sample user](https://github.com/kubernetes/dashboard/wiki/Creating-sample-user)


Get Further:
- [(Advanced) Kubernetes Networking from CloudNativeLabs](https://cloudnativelabs.github.io/post/2017-04-18-kubernetes-networking)
- [(Advanced) Illustrated guide to K8s networking](https://itnext.io/an-illustrated-guide-to-kubernetes-networking-part-1-d1ede3322727)
- [How K8s Networking works - basics](https://neuvector.com/network-security/kubernetes-networking/)
- [Setting ingress K8s Nginx controller](https://devopscube.com/setup-ingress-kubernetes-nginx-controller/)
- [(Advanced) K8s Ingress Controllers: how to choose the right one](https://itnext.io/kubernetes-ingress-controllers-how-to-choose-the-right-one-part-1-41d3554978d2)
- [(Advanced) K8s network deep dive](https://itnext.io/kubernetes-network-deep-dive-7492341e0ab5)
- [(Advanced) K8s Ingress with AWS ALB Ingress Controller](https://aws.amazon.com/blogs/opensource/kubernetes-ingress-aws-alb-ingress-controller/)
- [(Advanced) Painless Nginx Ingres](https://danielfm.me/posts/painless-nginx-ingress.html)
- [AWS ALB Ingress Controller for Kubernetes](https://akomljen.com/aws-alb-ingress-controller-for-kubernetes/)
- [Github aws-workshop-for-kubernetes Add Ingress Controllers to Kubernetes cluster](https://github.com/aws-samples/aws-workshop-for-kubernetes/tree/master/04-path-security-and-networking/405-ingress-controllers)
