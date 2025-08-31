"""
Real-time voice testing via WebSocket streaming
Streams actual Swedish audio files as 20ms PCM chunks to Alice ASR
"""

import asyncio
import base64
import json
import time
import wave
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import websockets
import librosa
from dataclasses import dataclass


@dataclass
class VoiceTestResult:
    """Voice test execution results"""
    scenario_id: str
    wer: float
    asr_partial_ms: Optional[float]
    asr_final_ms: Optional[float]
    vad_start_delay_ms: Optional[float]
    transcription: str
    ground_truth: str
    confidence: float
    audio_duration_s: float
    processing_errors: List[str]


class VoiceTestRunner:
    """Execute real-time voice tests using WebSocket streaming"""
    
    def __init__(self, config):
        self.config = config
        self.ws_url = config.WS_ASR.replace("http://", "ws://").replace("https://", "wss://")
        
    async def execute(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Execute voice test scenario"""
        scenario_id = scenario.get("id", "unknown")
        print(f"🎤 Executing voice scenario: {scenario_id}")
        
        # Load audio files and ground truth
        audio_files = self._load_audio_files(scenario)
        if not audio_files:
            return {"error": "No audio files found", "slo_pass": False}
            
        ground_truth = self._load_ground_truth(scenario)
        
        # Mix with background noise if specified
        if scenario.get("mix_with_noise"):
            audio_files = await self._mix_with_noise(audio_files, scenario)
            
        # Test each audio file
        results = []
        for audio_file, expected_text in zip(audio_files, ground_truth):
            try:
                result = await self._test_single_audio(audio_file, expected_text)
                results.append(result)
            except Exception as e:
                print(f"❌ Error testing {audio_file}: {e}")
                results.append(VoiceTestResult(
                    scenario_id=scenario_id,
                    wer=1.0,  # 100% error rate
                    asr_partial_ms=None,
                    asr_final_ms=None,
                    vad_start_delay_ms=None,
                    transcription="",
                    ground_truth=expected_text,
                    confidence=0.0,
                    audio_duration_s=0.0,
                    processing_errors=[str(e)]
                ))
        
        # Aggregate results
        return self._aggregate_results(scenario_id, results, scenario)
    
    async def _test_single_audio(self, audio_file: Path, expected_text: str) -> VoiceTestResult:
        """Test recognition of a single audio file"""
        print(f"  🔊 Testing: {audio_file.name}")
        
        # Load and prepare audio
        audio_data, sample_rate = librosa.load(audio_file, sr=16000, mono=True)
        audio_duration_s = len(audio_data) / sample_rate
        
        # Convert to PCM bytes
        pcm_data = (audio_data * 32767).astype(np.int16).tobytes()
        
        # Stream audio and collect results
        start_time = time.time()
        partial_time = None
        final_time = None
        transcription = ""
        confidence = 0.0
        processing_errors = []
        
        try:
            async with websockets.connect(self.ws_url, timeout=30) as ws:
                # Send audio in 20ms chunks (320 bytes for 16kHz mono)
                chunk_size = 320  # 20ms at 16kHz = 320 bytes
                
                for i in range(0, len(pcm_data), chunk_size):
                    chunk = pcm_data[i:i + chunk_size]
                    chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                    
                    message = {
                        "type": "audio",
                        "pcm_base64": chunk_b64,
                        "timestamp": time.time() - start_time
                    }
                    
                    await ws.send(json.dumps(message))
                    
                    # Check for partial results
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=0.1)
                        data = json.loads(response)
                        
                        if data.get("event") == "partial" and partial_time is None:
                            partial_time = time.time() - start_time
                            
                    except asyncio.TimeoutError:
                        continue  # No response yet, keep streaming
                        
                    # Simulate real-time streaming
                    await asyncio.sleep(0.02)  # 20ms delay
                
                # Send end-of-stream signal
                await ws.send(json.dumps({"type": "end"}))
                
                # Wait for final result
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(response)
                    
                    if data.get("event") == "final":
                        final_time = time.time() - start_time
                        transcription = data.get("text", "")
                        confidence = data.get("confidence", 0.0)
                        
                except asyncio.TimeoutError:
                    processing_errors.append("Timeout waiting for final result")
                    
        except Exception as e:
            processing_errors.append(f"WebSocket error: {e}")
            
        # Calculate Word Error Rate (WER)
        wer = self._calculate_wer(transcription, expected_text)
        
        return VoiceTestResult(
            scenario_id="single_test",
            wer=wer,
            asr_partial_ms=partial_time * 1000 if partial_time else None,
            asr_final_ms=final_time * 1000 if final_time else None,
            vad_start_delay_ms=partial_time * 1000 if partial_time else None,
            transcription=transcription,
            ground_truth=expected_text,
            confidence=confidence,
            audio_duration_s=audio_duration_s,
            processing_errors=processing_errors
        )
    
    def _calculate_wer(self, hypothesis: str, reference: str) -> float:
        """Calculate Word Error Rate between hypothesis and reference"""
        # Simple WER calculation - in production use jiwer library
        hyp_words = hypothesis.lower().split()
        ref_words = reference.lower().split()
        
        if len(ref_words) == 0:
            return 1.0 if len(hyp_words) > 0 else 0.0
            
        # Levenshtein distance at word level
        distance = self._levenshtein_distance(hyp_words, ref_words)
        wer = distance / len(ref_words)
        
        return min(wer, 1.0)  # Cap at 100% error rate
    
    def _levenshtein_distance(self, s1: List[str], s2: List[str]) -> int:
        """Calculate Levenshtein distance between two sequences"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
            
        if len(s2) == 0:
            return len(s1)
            
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
            
        return previous_row[-1]
    
    def _load_audio_files(self, scenario: Dict[str, Any]) -> List[Path]:
        """Load audio files matching the scenario pattern"""
        data_glob = scenario.get("data_glob", "")
        if not data_glob:
            return []
            
        # Convert glob pattern to pathlib
        base_path = Path(".")
        if data_glob.startswith("/"):
            # Absolute path - use relative to current directory
            data_glob = data_glob[1:]
            
        audio_files = list(base_path.glob(data_glob))
        audio_files = [f for f in audio_files if f.suffix.lower() in ['.wav', '.mp3', '.flac']]
        
        print(f"  📁 Found {len(audio_files)} audio files")
        return sorted(audio_files)[:10]  # Limit to 10 files for testing
    
    def _load_ground_truth(self, scenario: Dict[str, Any]) -> List[str]:
        """Load ground truth transcriptions"""
        truth_file = scenario.get("ground_truth", "")
        if not truth_file or not Path(truth_file).exists():
            return ["sample swedish text"] * 100  # Fallback for testing
            
        try:
            with open(truth_file, 'r', encoding='utf-8') as f:
                if truth_file.endswith('.tsv'):
                    # TSV format: filename\ttranscription
                    lines = [line.strip().split('\t')[1] for line in f.readlines()]
                else:
                    # Plain text format
                    lines = [line.strip() for line in f.readlines()]
            return lines
        except Exception as e:
            print(f"❌ Error loading ground truth: {e}")
            return ["fallback text"] * 100
    
    async def _mix_with_noise(self, audio_files: List[Path], scenario: Dict[str, Any]) -> List[Path]:
        """Mix audio files with background noise"""
        noise_file = scenario.get("mix_with_noise", "")
        snr_db = scenario.get("snr_db", 10)
        
        if not noise_file or not Path(noise_file).exists():
            print(f"⚠️  Noise file not found: {noise_file}, using clean audio")
            return audio_files
            
        # Load background noise
        try:
            noise_data, _ = librosa.load(noise_file, sr=16000, mono=True)
        except Exception as e:
            print(f"❌ Error loading noise file: {e}")
            return audio_files
            
        # Mix each audio file with noise
        mixed_files = []
        output_dir = Path("./temp/mixed_audio")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for audio_file in audio_files:
            try:
                # Load clean audio
                clean_data, _ = librosa.load(audio_file, sr=16000, mono=True)
                
                # Ensure noise is long enough
                if len(noise_data) < len(clean_data):
                    noise_data = np.tile(noise_data, (len(clean_data) // len(noise_data)) + 1)
                    
                noise_segment = noise_data[:len(clean_data)]
                
                # Calculate mixing ratios based on SNR
                signal_power = np.mean(clean_data ** 2)
                noise_power = np.mean(noise_segment ** 2)
                
                if noise_power > 0:
                    noise_scale = np.sqrt(signal_power / (noise_power * (10 ** (snr_db / 10))))
                    mixed_data = clean_data + noise_scale * noise_segment
                else:
                    mixed_data = clean_data
                    
                # Save mixed audio
                output_file = output_dir / f"mixed_{audio_file.name}"
                librosa.output.write_wav(str(output_file), mixed_data, 16000)
                mixed_files.append(output_file)
                
            except Exception as e:
                print(f"❌ Error mixing {audio_file}: {e}")
                mixed_files.append(audio_file)  # Use original file
                
        return mixed_files
    
    def _aggregate_results(self, scenario_id: str, results: List[VoiceTestResult], 
                          scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate individual test results into scenario summary"""
        if not results:
            return {"error": "No results to aggregate", "slo_pass": False}
            
        # Calculate aggregate metrics
        avg_wer = np.mean([r.wer for r in results])
        avg_partial_ms = np.mean([r.asr_partial_ms for r in results if r.asr_partial_ms is not None])
        avg_final_ms = np.mean([r.asr_final_ms for r in results if r.asr_final_ms is not None])
        avg_confidence = np.mean([r.confidence for r in results])
        
        # P95 calculations
        final_times = [r.asr_final_ms for r in results if r.asr_final_ms is not None]
        p95_final_ms = np.percentile(final_times, 95) if final_times else None
        
        # Check SLO compliance
        slo_targets = scenario.get("slo_targets", {})
        slo_pass = True
        
        if "wer" in slo_targets and avg_wer > slo_targets["wer"]:
            slo_pass = False
            
        if "asr_final_ms" in slo_targets and p95_final_ms and p95_final_ms > slo_targets["asr_final_ms"]:
            slo_pass = False
            
        # Count processing errors
        total_errors = sum(len(r.processing_errors) for r in results)
        
        return {
            "scenario_id": scenario_id,
            "scenario_kind": "voice",
            "wer": round(avg_wer, 4),
            "asr_partial_ms": round(avg_partial_ms, 1) if not np.isnan(avg_partial_ms) else None,
            "asr_final_ms": round(avg_final_ms, 1) if not np.isnan(avg_final_ms) else None,
            "asr_final_p95_ms": round(p95_final_ms, 1) if p95_final_ms else None,
            "confidence": round(avg_confidence, 3),
            "samples_tested": len(results),
            "processing_errors": total_errors,
            "slo_pass": slo_pass,
            "slo_targets": slo_targets,
            "summary": f"WER: {avg_wer:.1%}, Final P95: {p95_final_ms:.0f}ms" if p95_final_ms else f"WER: {avg_wer:.1%}"
        }