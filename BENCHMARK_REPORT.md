# ⚡ VoxFlow Voice Agent Latency & Throughput Benchmark Report

**Execution Timestamp:** `2026-08-24 00:30:41 UTC`  
**Benchmark Mode:** `MOCK`  
**Target Model:** `openai/gpt-oss-20b`  
**Evaluation Iterations:** `5`  

## 📈 Percentile Latency Distribution (ms)

| Pipeline Stage | Technology | Samples | Min (ms) | Mean (ms) | P50 (ms) | P90 (ms) | P95 (ms) | P99 (ms) | StdDev |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Speech-to-Text (STT)** | `Mock Whisper-v3-Turbo` | 5 | 167.8 | 188.5 | **187.9** | 209.5 | 212.6 | 215.2 | ±20.1 |
| **2. LLM Reasoning & TTFT** | `Mock openai/gpt-oss-20b (Simulated)` | 5 | 121.2 | 144.8 | **148.0** | 166.2 | 170.2 | 173.5 | ±21.6 |
| **3. Audio Synthesis (TTS)** | `Mock Edge-TTS (en-GB-SoniaNeural)` | 5 | 233.8 | 301.6 | **297.3** | 361.1 | 368.6 | 374.6 | ±57.1 |
| **4. End-to-End Glass-to-Glass** | `Full Pipeline (VAD + STT + AgentRunner + TTS)` | 5 | 514.1 | 605.9 | **566.1** | 722.6 | 764.4 | 797.9 | ±116.0 |

## 🔬 Detailed Component Breakdown & Metrics

### 1. Speech-to-Text (STT) (`Mock Whisper-v3-Turbo`)
- **Audio Duration Sec**: `1.5`
- **Real Time Factor Rtf**: `0.1257`
- **Rtf Description**: `8.0x faster than real-time`
- **Raw Samples (ms)**: `[171.0, 199.9, 215.8, 167.8, 187.9]`

### 2. LLM Reasoning & TTFT (`Mock openai/gpt-oss-20b (Simulated)`)
- **Ttft P50 Ms**: `148.0`
- **Total Turn P50 Ms**: `338.3`
- **Inter Token Latency Ms**: `7.59`
- **Generation Throughput Tps**: `131.8`
- **Avg Tokens Per Response**: `23.8`
- **Raw Samples (ms)**: `[121.2, 174.3, 126.2, 148.0, 154.2]`

### 3. Audio Synthesis (TTS) (`Mock Edge-TTS (en-GB-SoniaNeural)`)
- **Ttfb P50 Ms**: `153.0`
- **Total Synth P50 Ms**: `297.3`
- **Avg Audio Payload Kb**: `213.9`
- **Streaming Chunk Enabled**: `True`
- **Raw Samples (ms)**: `[338.6, 376.1, 233.8, 262.5, 297.3]`

### 4. End-to-End Glass-to-Glass (`Full Pipeline (VAD + STT + AgentRunner + TTS)`)
- **Glass To Glass P50 Ms**: `566.1`
- **Glass To Glass P90 Ms**: `722.6`
- **Glass To Glass P99 Ms**: `797.9`
- **Includes Database And Tools**: `True`
- **Raw Samples (ms)**: `[806.3, 546.2, 566.1, 597.0, 514.1]`

---
*Generated automatically by the VoxFlow High-Precision Latency Benchmark Suite.*