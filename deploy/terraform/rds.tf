###############################################################################
# RDS PostgreSQL — eu-west-2, private subnet, encrypted at rest
###############################################################################

# Generate a strong random password stored in Secrets Manager (not .env)
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = { Name = "${local.name_prefix}-db-subnet-group" }
}

resource "aws_db_instance" "postgres" {
  identifier = "${local.name_prefix}-postgres"

  engine               = "postgres"
  engine_version       = "15.19"
  instance_class       = var.db_instance_class
  allocated_storage    = 20
  max_allocated_storage = 100   # auto-scaling up to 100 GB
  storage_type         = "gp3"
  storage_encrypted    = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Automated backups — 7-day retention, PITR enabled automatically
  backup_retention_period   = 7
  backup_window             = "03:00-04:00"   # 03:00-04:00 UTC (low-traffic)
  maintenance_window        = "Mon:04:00-Mon:05:00"
  delete_automated_backups  = false

  # Protect against accidental deletion
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "${local.name_prefix}-postgres-final-${local.suffix}"

  performance_insights_enabled = false  # costs extra; enable in Phase 6

  tags = { Name = "${local.name_prefix}-postgres" }
}

###############################################################################
# Store DB credentials in Secrets Manager (Phase 1 DoD: no .env in prod)
###############################################################################
resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "${local.name_prefix}/db/credentials"
  description             = "VoxFlow RDS PostgreSQL credentials"
  recovery_window_in_days = 7

  tags = { Name = "${local.name_prefix}-db-credentials" }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
    host     = aws_db_instance.postgres.address
    port     = aws_db_instance.postgres.port
    dbname   = var.db_name
    url      = "postgresql://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.postgres.address}:${aws_db_instance.postgres.port}/${var.db_name}"
  })
}
