# Chaos Engineering on Amazon EKS

This lab shows you how to run some basic chaos engineering experiments on [Amazon Elastic Kubernetes Service](https://aws.amazon.com/eks/) or EKS.

The examples build on the existing [chaostoolkit-demos](https://github.com/chaosiq/chaostoolkit-demos) repository, but uses an EKS cluster rather than a self-hosted cluster.

## Prerequisites

You will need an AWS account with sufficient permissions to create an EKS repository and related constructs.

## Setup

### Repositories

First, clone the [chaostoolkit-demos](https://github.com/chaosiq/chaostoolkit-demos) repository into a working directory.

    export WORKDIR=<path to a new working directory>
    mkdir -p $WORKDIR
    cd $WORKDIR
    git clone https://github.com/chaosiq/chaostoolkit-demos.git

Note that these instructions are based on that repository at commit `0db25e0`.

Next, clone this repository:

    git clone https://github.com/aws-samples/chaos-engineering-on-amazon-eks

The second repository has additional labs and supporting material.  Let's copy it into the first repository's directory.

    cd chaostoolkit-demos
    cp ../chaos-engineering-on-amazon-eks/eks.yaml .
    cp -r ../chaos-engineering-on-amazon-eks/lab6 .
    cp -r ../chaos-engineering-on-amazon-eks/lab7 .
    cp -r ../chaos-engineering-on-amazon-eks/apps/cw apps/
    cp ../chaos-engineering-on-amazon-eks/manifests/eks.yaml manifests

### Create a new EKS cluster

You will need to install `eksctl` and make sure that you have enough free room in your account to create a new VPC.  See the [quick setup](https://docs.aws.amazon.com/eks/latest/userguide/getting-started-eksctl.html) guide for more details.

Then run:

    eksctl create cluster -f eks.yaml

This creates an EKS cluster with a managed node group, and configures `kubectl` to use the new cluster as the default context.

### Prometheus

Install Prometheus, but change to a different working directory first.

    cd $WORKDIR
    git clone https://github.com/prometheus-operator/kube-prometheus
    cd kube-prometheus
    kubectl apply -f manifests/setup/
    kubectl apply -f manifests/

Check deployment status:

    kubectl -n monitoring get all

### Chaos Mesh

Run:
    
    cd $WORKDIR
    curl -sSL https://mirrors.chaos-mesh.org/v1.0.2/install.sh | bash

Check deployment status:

    kubectl -n chaos-testing get all

The dashboard is at:

    kubectl -n chaos-testing port-forward --address 0.0.0.0 service/chaos-dashboard 2333:2333
    http://localhost:2333/dashboard/overview

### Ingress

Run:

    cd $WORKDIR
    cd chaostoolkit-demos
    kubectl apply -f manifests/traefik.yaml

### Chaos extensions

Run:

    pip install chaostoolkit-kubernetes chaostoolkit-prometheus chaostoolkit-addons jsonpath2

### Vegeta

#### Linux

Go to a temporary directory and run:

    cd /tmp
    wget https://github.com/tsenart/vegeta/releases/download/v12.8.4/vegeta_12.8.4_linux_386.tar.gz
    tar -zxf vegeta_12.8.4_linux_386.tar.gz
    sudo cp ./vegeta /usr/local/bin/
    sudo chmod +x /usr/local/bin/vegeta

#### Mac

    brew update && brew install vegeta

### Applications

The default applications are already built.  Just run:

    cd $WORKDIR
    cd chaostoolkit-demos
    kubectl apply -f manifests/all.yaml

## Experiments

### Experiment 1: Killing a pod

First we need to set up port forwarding for the ingress.

    kubectl port-forward --address 0.0.0.0 service/traefik-ingress-service 30080:80

Now run the experiment.

    rm -f lab1/vegeta_results.json
    export PYTHONPATH=`pwd`/ctkextensions
    chaos run lab1/experiment.json 

Let's scale the middle service to fix the problem.

    kubectl scale --replicas=2 deployment/middle
    rm -f lab1/vegeta_results.json
    chaos run lab1/experiment.json 

### Experiment 2: Latency

This lab has no definitive resolution.  It could result in a fail-fast degradation or an effort to put requests into a queue for later service.

    chaos run --rollback-strategy=always lab2/experiment.json 

### Experiment 3: Network outage

This experiment does not seem to return an error properly.  It should produce an error because the back-end service is cut off from the network.

    chaos run --rollback-strategy=always lab3/experiment.json 

### Experiment 4: Prometheus

This experiment repeats Lab 3 but with Prometheus used for monitoring.

    kubectl -n monitoring port-forward --address 0.0.0.0 service/prometheus-k8s 9090:9090
    export PROMETHEUS_URL=http://localhost:9090
    chaos run --rollback-strategy=always lab4/experiment.json 

### Experiment 5: Safeguards

This experiment adds a safeguard so the experiment doesn't get out of control.

    kubectl apply -f manifests/failingapp.yaml

### Experiment 6: Kill k8s worker

This experiment terminates a random node out of the worker group.

First, get the autoscaling group name for the EKS node group from the EKS console.

Next, check the list of existing instances:

    aws ec2 describe-instances --filters Name=tag:eks:cluster-name,Values=chaoscluster | jq '.Reservations[].Instances[] | .InstanceId + " - " + .State.Name'

In the experiment file, edit the following fields:

* `aws_region`
* `aws_profile_name`
* `asg_names`

Now run the experiment:

    chaos run lab6/experiment.json 

Confirm that one of the instances is stopped.  It'll be replaced when the health check times out.

    aws ec2 describe-instances --filters Name=tag:eks:cluster-name,Values=chaoscluster | jq '.Reservations[].Instances[] | .InstanceId + " - " + .State.Name'

### Experiment 7: Simulate a CloudWatch outage

This experiment takes away permission for a pod to send metrics to CloudWatch.

To start we need to build a new Docker image.  This simple application publishes metrics to CloudWatch.

    cd apps/cw
    ./build_and_push.sh cwpod

Note that image URL output, and substitute it on line 24 of `manifests/cw.yaml`.  Now apply the manifest:

    cd $WORKDIR
    cd chaostoolkit-demos
    kubectl -n cw-metric-writer apply -f manifests/cw.yaml

Set up port forwarding for port 8000:

    kubectl -n cw-metric-writer port-forward --address 0.0.0.0 service/cwpod 8000:8000

Go to `http://localhost:8000` and refresh the page a few times.  Now in CloudWatch you should see some metrics in the `chaos` namespace, under the `app=cw` dimension.

Next, find the role that we use for the service account for this pod.  The name will look something like this:

    eksctl-chaoscluster-addon-iamserviceaccount-Role1-G9YIIYY2SK4H

Enter the role name in the `role_name` field in `lab7/experiment.json`.  

Also edit these fields in `lab7/experiment.json`:

* `aws_region`
* `aws_profile_name`

Now run the experiment:

    chaos run lab7/experiment.json 

The experiment should fail, as the pod is no longer allowed to write to CloudWatch.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
