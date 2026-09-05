variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "domain" {
  description = "Domain name for Caddy TLS (e.g. yourdomain.com or voxflow.duckdns.org)"
  type        = string
}

variable "acme_email" {
  description = "Email for Let's Encrypt via Caddy"
  type        = string
}

variable "db_instance_class" {
  description = "RDS instance class (db.t3.micro = Free Tier)"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  type    = string
  default = "voxflow"
}

variable "db_username" {
  type    = string
  default = "voxflow_admin"
}

variable "ec2_instance_type" {
  description = "EC2 instance type (t3.small recommended for Docker Compose)"
  type        = string
  default     = "t3.small"
}

variable "ssh_public_key" {
  description = "Your SSH public key content (paste from ~/.ssh/id_ed25519.pub)"
  type        = string
}
