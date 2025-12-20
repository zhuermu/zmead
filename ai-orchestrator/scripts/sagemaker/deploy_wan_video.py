#!/usr/bin/env python3
"""Deploy Wan2.2 video model to AWS SageMaker.

This script creates a SageMaker endpoint for the Wan2.2 video generation model.
"""

import argparse
import time

import boto3
from botocore.exceptions import ClientError


def create_model(
    sagemaker_client,
    model_name: str,
    execution_role_arn: str,
    image_uri: str,
    model_data_url: str,
) -> str:
    """Create SageMaker model.

    Args:
        sagemaker_client: Boto3 SageMaker client
        model_name: Name for the model
        execution_role_arn: IAM role ARN for SageMaker
        image_uri: Docker image URI for inference
        model_data_url: S3 URL to model artifacts

    Returns:
        Model ARN
    """
    try:
        response = sagemaker_client.create_model(
            ModelName=model_name,
            PrimaryContainer={
                "Image": image_uri,
                "ModelDataUrl": model_data_url,
                "Environment": {
                    "MODEL_NAME": "wan2.2",
                    "SAGEMAKER_PROGRAM": "inference.py",
                },
            },
            ExecutionRoleArn=execution_role_arn,
        )
        print(f"✓ Model created: {response['ModelArn']}")
        return response["ModelArn"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ValidationException":
            print(f"✓ Model {model_name} already exists")
            return f"arn:aws:sagemaker:*:*:model/{model_name}"
        raise


def create_endpoint_config(
    sagemaker_client,
    config_name: str,
    model_name: str,
    instance_type: str = "ml.g5.2xlarge",
) -> str:
    """Create SageMaker endpoint configuration.

    Args:
        sagemaker_client: Boto3 SageMaker client
        config_name: Name for the endpoint configuration
        model_name: Name of the model to use
        instance_type: EC2 instance type for hosting (video needs more GPU)

    Returns:
        Endpoint config ARN
    """
    try:
        response = sagemaker_client.create_endpoint_config(
            EndpointConfigName=config_name,
            ProductionVariants=[
                {
                    "VariantName": "AllTraffic",
                    "ModelName": model_name,
                    "InitialInstanceCount": 1,
                    "InstanceType": instance_type,
                    "InitialVariantWeight": 1.0,
                }
            ],
        )
        print(f"✓ Endpoint config created: {response['EndpointConfigArn']}")
        return response["EndpointConfigArn"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ValidationException":
            print(f"✓ Endpoint config {config_name} already exists")
            return f"arn:aws:sagemaker:*:*:endpoint-config/{config_name}"
        raise


def create_endpoint(
    sagemaker_client,
    endpoint_name: str,
    config_name: str,
) -> str:
    """Create SageMaker endpoint.

    Args:
        sagemaker_client: Boto3 SageMaker client
        endpoint_name: Name for the endpoint
        config_name: Name of the endpoint configuration

    Returns:
        Endpoint ARN
    """
    try:
        response = sagemaker_client.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=config_name,
        )
        print(f"✓ Endpoint creation started: {response['EndpointArn']}")
        return response["EndpointArn"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ValidationException":
            print(f"✓ Endpoint {endpoint_name} already exists")
            return f"arn:aws:sagemaker:*:*:endpoint/{endpoint_name}"
        raise


def wait_for_endpoint(sagemaker_client, endpoint_name: str, timeout: int = 900):
    """Wait for endpoint to be in service.

    Args:
        sagemaker_client: Boto3 SageMaker client
        endpoint_name: Name of the endpoint
        timeout: Maximum wait time in seconds (video models take longer)
    """
    print(f"Waiting for endpoint {endpoint_name} to be in service...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        response = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
        status = response["EndpointStatus"]

        if status == "InService":
            print(f"✓ Endpoint {endpoint_name} is in service!")
            return
        elif status == "Failed":
            raise Exception(f"Endpoint creation failed: {response.get('FailureReason')}")

        print(f"  Status: {status}... (elapsed: {int(time.time() - start_time)}s)")
        time.sleep(30)

    raise TimeoutError(f"Endpoint creation timed out after {timeout}s")


def main():
    parser = argparse.ArgumentParser(description="Deploy Wan2.2 video model to SageMaker")
    parser.add_argument("--region", default="us-west-2", help="AWS region")
    parser.add_argument("--model-name", default="wan-video-model", help="Model name")
    parser.add_argument("--endpoint-name", default="wan-video-endpoint", help="Endpoint name")
    parser.add_argument("--role-arn", required=True, help="SageMaker execution role ARN")
    parser.add_argument("--image-uri", required=True, help="Docker image URI")
    parser.add_argument("--model-data", required=True, help="S3 URL to model artifacts")
    parser.add_argument("--instance-type", default="ml.g5.2xlarge", help="Instance type")
    parser.add_argument("--wait", action="store_true", help="Wait for endpoint to be ready")

    args = parser.parse_args()

    # Create SageMaker client
    sagemaker_client = boto3.client("sagemaker", region_name=args.region)

    print("=" * 60)
    print("Deploying Wan2.2 Video Model to SageMaker")
    print("=" * 60)

    # Create model
    model_arn = create_model(
        sagemaker_client,
        args.model_name,
        args.role_arn,
        args.image_uri,
        args.model_data,
    )

    # Create endpoint configuration
    config_name = f"{args.endpoint_name}-config"
    config_arn = create_endpoint_config(
        sagemaker_client,
        config_name,
        args.model_name,
        args.instance_type,
    )

    # Create endpoint
    endpoint_arn = create_endpoint(
        sagemaker_client,
        args.endpoint_name,
        config_name,
    )

    # Wait for endpoint if requested
    if args.wait:
        wait_for_endpoint(sagemaker_client, args.endpoint_name)

    print("\n" + "=" * 60)
    print("Deployment Summary")
    print("=" * 60)
    print(f"Model ARN:          {model_arn}")
    print(f"Config ARN:         {config_arn}")
    print(f"Endpoint ARN:       {endpoint_arn}")
    print(f"Endpoint Name:      {args.endpoint_name}")
    print("\nAdd to your .env file:")
    print(f"SAGEMAKER_WAN_VIDEO_ENDPOINT={args.endpoint_name}")


if __name__ == "__main__":
    main()
