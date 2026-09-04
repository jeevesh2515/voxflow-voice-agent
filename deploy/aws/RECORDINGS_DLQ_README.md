# VoxFlow - Recording Lambda Error Handling + DLQ (Retry Automatically)

Pairs with `deploy/aws/s3_recordings_handler.py` and `deploy/aws/dlq_redrive_handler.py` plus the UK contact flow. It makes failed recording uploads retry automatically, and quarantines what cannot be fixed by retrying.

---

## 1. Failure Taxonomy (Retry vs DLQ)

| Class | Examples | Handling |
| :--- | :--- | :--- |
| **Transient** | S3 throttling (503/SlowDown), Connect throttling, KMS throttling, network timeouts, 5xx, Lambda concurrency throttling | In-process retry `VOXFLOW_RETRY_ATTEMPTS` (default 3) with exponential backoff + jitter; then raise so Lambda async retries (max 2, up to 6h); then event -> DLQ via on-failure destination |
| **Permanent** | `NoSuchKey`, `AccessDenied`, `ResourceNotFound` (bad contact), malformed attributes, API 4xx (e.g. `call_not_found`) | Sent straight to the DLQ (`VOXFLOW_RECORDING_DLQ_URL`) so they never burn retry budget |

### Idempotency
- The object tag `voxflow:post-status=ok` is written only after the API POST succeeds.
- On any replay, the handler skips reprocessing.
- The server-side [`recording_service.persist_recording_and_consent`](file:///Users/jeeveshsingale/VoxFlow/voxflow-voice-agent/apps/api/voxflow_api/services/recording_service.py) already returns `already_persisted`, ensuring re-deliveries never double-write.

---

## 2. Deploy Steps

1. **Deploy CloudFormation stack** `recording_dlq_cfn.yaml` (param `RecordingHandlerName` = `VoxFlow-Recordings-Handler`, `AlarmEmail` = your ops mailbox). It creates:
   - `voxflow-recordings-dlq` (14-day retention, visibility 360s, redrive `maxReceiveCount` 5 to poison queue)
   - `voxflow-recordings-dlq-poison`
   - `AWS::Lambda::EventInvokeConfig` on the handler: `MaximumRetryAttempts: 2`, `MaximumEventAgeInSeconds: 21600`, `OnFailure` destination = DLQ
   - SNS topic + email subscription + CloudWatch alarm on DLQ depth (`ApproximateNumberOfMessagesVisible >= 1`)

2. **Attach IAM policy** `recording_dlq_iam_policy.json` to the handler's role (`SendMessage` to both queues) and to the redrive processor role (also grants `ReceiveMessage`/`DeleteMessage`/`GetQueueAttributes`).

3. **Re-deploy `s3_recordings_handler.py`** with env var:
   - `VOXFLOW_RECORDING_DLQ_URL=<DlqUrl from stack output>`

4. **Create Redrive Processor Lambda** `VoxFlow-Recordings-DLQ-Redrive` (Python 3.12, 256 MB, 60s timeout) using a package containing both `s3_recordings_handler.py` and `dlq_redrive_handler.py`.
   - Env vars: `VOXFLOW_API_URL`, `VOXFLOW_SECRET`, `CONNECT_INSTANCE_ID`, `CONNECT_REGION=eu-west-2`, `VOXFLOW_RECORDING_POISON_QUEUE_URL=<PoisonQueueUrl>`, `VOXFLOW_RECORDING_RETENTION_DAYS=30`.

5. **Add SQS Trigger** on the processor:
   - Source: `voxflow-recordings-dlq`
   - Batch size: 10
   - Function timeout: 60s (visibility timeout 360s >= 6x function timeout).

6. **Alert on the Poison Queue**:
   - Duplicate the CloudWatch alarm pattern for `QueueName: voxflow-recordings-dlq-poison` so stuck records alert immediately.

---

## 3. Configuration Values

| Setting | Value | Source |
| :--- | :--- | :--- |
| Lambda async default retries / max configurable | 2 | AWS CloudFormation Lambda::EventInvokeConfig |
| Lambda async max event age | 21,600s (6h); valid 60–21,600 | AWS PutFunctionEventInvokeConfig |
| S3->Lambda (async) retry count | 2, then discard unless destination configured | AWS invocation-retries |
| SQS visibility timeout | 360s (= 6x 60s timeout) | AWS SQS visibility-timeout docs |
| SQS redrive maxReceiveCount | 5 | AWS SetQueueAttributes / DLQ docs |
| SQS message retention | 14 days (1,209,600s) | AWS SQS welcome docs |
| DLQ alarm metric | `ApproximateNumberOfMessagesVisible` | AWS dead-letter-queues-alarms-cloudwatch |

---

## 4. Manual Recovery Runbook

- Messages in the poison queue always carry `reason` and the original S3 event `record`.
- Fix the root cause (e.g., enable recording on Connect instance, fix IAM), then:
  - Replay by sending message body back to `voxflow-recordings-dlq`, or
  - Re-push S3 event via `aws s3 cp s3://<bucket>/<key> s3://<bucket>/<key>`.
