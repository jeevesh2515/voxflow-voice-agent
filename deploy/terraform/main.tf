###############################################################################
# VoxFlow — Phase 1 AWS Infrastructure (EC2 + RDS — ~$16/mo)
# Region: eu-west-2 (London)
# Architecture: Single EC2 t3.small + Docker Compose + Caddy (TLS)
#               RDS PostgreSQL in private subnet (same VPC)
#
# Why EC2 over Fargate for Phase 1:
#   - No NAT Gateway ($33/mo saved)
#   - No ALB ($16/mo saved)
#   - Same Docker Compose workflow already proven on Oracle VM
#   - Terraform-managed → SOC 2 auditable when Phase 6 arrives
#   - Migrate to Fargate in Phase 3/6 when revenue justifies it
###############################################################################

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Uncomment after running bootstrap once:
  # backend "s3" {
  #   bucket         = "voxflow-tfstate-031247250483"
  #   key            = "phase1/terraform.tfstate"
  #   region         = "eu-west-2"
  #   dynamodb_table = "voxflow-tfstate-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "voxflow"
      Phase     = "1"
      ManagedBy = "terraform"
    }
  }
}

resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  name_prefix = "voxflow-${var.environment}"
  suffix      = random_id.suffix.hex
}
