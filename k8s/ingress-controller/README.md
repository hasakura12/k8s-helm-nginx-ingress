# Kubernetes Nginx Ingress Controller for Minikube
There are two files in this folder:
- `deployment.yaml`
- `nginx.conf`

Both are created by executing `minikube addons enable ingress`.

## Ingress Controller
`deployment.yaml` was retrieved by:
```
kubectl get deploy \
  nginx-ingress-controller \
  -o yaml \
  --export \
  -n kube-system
```

## Nginx config 
`nginx.conf` was retrieved by:
```
kubectl exec -it \
  nginx-ingress-controller-5d9cf9c69f-rqnmk \
  -n kube-system cat nginx.conf
```