###############################################################################
# Outputs
###############################################################################

output "ec2_public_ip" {
  description = "Elastic IP — point your DuckDNS A record to this"
  value       = aws_eip.ec2.public_ip
}

output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}

output "rds_endpoint" {
  description = "RDS endpoint (private — reachable only from EC2)"
  value       = aws_db_instance.postgres.address
  sensitive   = true
}

output "db_secret_arn" {
  description = "Secrets Manager ARN for DB credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "app_secret_arn" {
  description = "Secrets Manager ARN for app secrets"
  value       = aws_secretsmanager_secret.app_secrets.arn
}

output "ssh_command" {
  description = "SSH into your EC2 instance"
  value       = "ssh -i ~/.ssh/id_ed25519 ec2-user@${aws_eip.ec2.public_ip}"
}

output "next_steps" {
  description = "What to do after terraform apply"
  value = <<-EOT
    ===== NEXT STEPS =====
    1. Update DuckDNS A record → ${aws_eip.ec2.public_ip}
       https://www.duckdns.org/domains
    2. Populate secrets: ./scripts/migrate-secrets-to-aws.sh
    3. SSH in: ssh -i ~/.ssh/id_ed25519 ec2-user@${aws_eip.ec2.public_ip}
    4. Deploy app: ./scripts/deploy-to-ec2.sh
    5. Run DB migration: ./scripts/migrate-db-to-rds.sh
    6. Verify: https://${var.domain}/api/health
    =====================
  EOT
}
