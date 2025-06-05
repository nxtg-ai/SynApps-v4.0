# Kubernetes Deployment

This directory contains Kubernetes manifests for deploying SynApps to a Kubernetes cluster.

## Prerequisites

- A Kubernetes cluster (e.g., GKE, EKS, AKS, or local kind/minikube)
- kubectl configured to access your cluster
- Docker images pushed to a container registry (e.g., ghcr.io)

## Secrets

Before deploying, you need to create the required secrets:

1. Copy the secrets template and update with your values:
   ```bash
   cp secrets.yaml.template secrets.yaml
   ```

2. Edit `secrets.yaml` and replace the placeholder values with base64-encoded API keys:
   ```bash
   echo -n "your_openai_api_key" | base64
   echo -n "your_stability_api_key" | base64
   ```

3. Apply the secrets:
   ```bash
   kubectl apply -f secrets.yaml
   ```

## Deployment

Apply the manifests in the following order:

1. Create the orchestrator deployment and service:
   ```bash
   kubectl apply -f orchestrator.yaml
   ```

2. Set up autoscaling:
   ```bash
   kubectl apply -f autoscaling.yaml
   ```

## Verifying the Deployment

Check the status of your deployed resources:

```bash
kubectl get deployments
kubectl get pods
kubectl get services
kubectl get hpa
```

## Accessing the API

The API is exposed through an Ingress at `api.synapps.ai`. Make sure your DNS is configured correctly to point to your ingress controller's IP.

To get the IP of your ingress controller:

```bash
kubectl get ingress synapps-orchestrator-ingress
```

## Scaling

The HorizontalPodAutoscaler will automatically scale the number of pods based on CPU and memory utilization. You can adjust the scaling parameters in `autoscaling.yaml`.

## Troubleshooting

Check the logs of the orchestrator:

```bash
kubectl logs -l app=synapps-orchestrator
```

Check the events:

```bash
kubectl get events
```

## Cleanup

To remove all deployed resources:

```bash
kubectl delete -f autoscaling.yaml
kubectl delete -f orchestrator.yaml
kubectl delete -f secrets.yaml
```
