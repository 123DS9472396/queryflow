terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# ---------------------------------------------------------
# AWS S3 Bucket: Raw Data Storage (Data Lake)
# ---------------------------------------------------------
resource "aws_s3_bucket" "raw_data_lake" {
  bucket = "enterprise-nyc-taxi-raw-data-lake"

  tags = {
    Environment = "Production"
    Project     = "QueryFlow_DataEngineering"
  }
}

resource "aws_s3_bucket_versioning" "raw_data_versioning" {
  bucket = aws_s3_bucket.raw_data_lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ---------------------------------------------------------
# AWS MSK: Managed Kafka Cluster for Real-Time Streaming
# ---------------------------------------------------------
resource "aws_msk_cluster" "streaming_cluster" {
  cluster_name           = "enterprise-kafka-stream"
  kafka_version          = "3.5.1"
  number_of_broker_nodes = 3

  broker_node_group_info {
    instance_type = "kafka.m5.large"
    client_subnets = [
      "subnet-0a1b2c3d",
      "subnet-0e1f2g3h",
      "subnet-0i1j2k3l"
    ]
    security_groups = ["sg-0123456789abcdef0"]
  }

  tags = {
    Environment = "Production"
  }
}

# ---------------------------------------------------------
# Note: ClickHouse Cloud requires their specific provider.
# Below is a theoretical representation of the ClickHouse Cloud deployment.
# ---------------------------------------------------------
resource "null_resource" "clickhouse_cloud_deployment" {
  provisioner "local-exec" {
    command = "echo 'Deploying ClickHouse Cloud cluster for analytical queries...'"
  }
}
