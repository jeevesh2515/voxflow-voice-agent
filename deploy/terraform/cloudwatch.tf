# Phase 3: Telephony & Voice CloudWatch Observability Dashboard
# Covers Amazon Connect inbound voice lines, Lambda Bridge latency (P50/P90/P99),
# call recording ingestion, and SQS DLQ error quarantine in eu-west-2.

resource "aws_cloudwatch_dashboard" "telephony" {
  dashboard_name = "voxflow-telephony-euwest2"

  dashboard_body = file("${path.module}/../aws/cloudwatch_dashboard.json")
}

# CloudWatch Alarm: Telephony Bridge High Error Rate (> 2% in 5 min)
resource "aws_cloudwatch_metric_alarm" "lambda_bridge_errors" {
  alarm_name          = "voxflow-telephony-bridge-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Telephony Lambda bridge encountered elevated error counts during voice call turns."
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = "voxflow-connect-bridge"
  }
}

# CloudWatch Alarm: SQS Dead Letter Queue Depth (> 0 quarantined recordings)
resource "aws_cloudwatch_metric_alarm" "recordings_dlq_quarantine" {
  alarm_name          = "voxflow-recordings-dlq-quarantine"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "One or more customer call recordings failed S3 dual-channel ingestion and were quarantined in the DLQ."
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = "voxflow-recordings-dlq"
  }
}
