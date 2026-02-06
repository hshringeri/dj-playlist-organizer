import numpy as np
import librosa
from pathlib import Path
from typing import Optional
from database import get_db


def analyze_audio(file_path: str | Path) -> dict:
    """
    Analyze an audio file and extract DJ-relevant features.

    Returns dict with: bpm, energy, key, mode, loudness, danceability, valence estimates
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # Load audio (mono, standard sample rate)
    y, sr = librosa.load(file_path, sr=22050, mono=True)

    features = {}

    # BPM detection
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    features["bpm"] = float(tempo[0]) if hasattr(tempo, '__len__') else float(tempo)

    # RMS Energy (0-1 normalized)
    rms = librosa.feature.rms(y=y)[0]
    features["energy"] = float(np.mean(rms) / np.max(rms)) if np.max(rms) > 0 else 0.0

    # Loudness (dB, typically -60 to 0)
    features["loudness"] = float(20 * np.log10(np.mean(rms) + 1e-10))

    # Spectral features for "vibe" estimation
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    features["spectral_centroid"] = float(np.mean(spectral_centroid))

    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    features["spectral_rolloff"] = float(np.mean(spectral_rolloff))

    # Zero crossing rate (higher = more percussive/noisy)
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    features["zero_crossing_rate"] = float(np.mean(zcr))

    # Key detection using chroma features
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)
    features["key"] = int(np.argmax(chroma_mean))  # 0-11 (C, C#, D, ...)

    # Mode estimation (major vs minor) - simplified
    # Compare major vs minor chord profiles
    major_profile = np.array([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])  # Major scale
    minor_profile = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0])  # Minor scale

    # Rotate profiles to detected key
    key = features["key"]
    major_rotated = np.roll(major_profile, key)
    minor_rotated = np.roll(minor_profile, key)

    major_corr = np.corrcoef(chroma_mean, major_rotated)[0, 1]
    minor_corr = np.corrcoef(chroma_mean, minor_rotated)[0, 1]
    features["mode"] = 1 if major_corr > minor_corr else 0  # 1=major, 0=minor

    # Danceability estimate (based on beat strength and tempo regularity)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    pulse = librosa.beat.plp(onset_envelope=onset_env, sr=sr)
    features["danceability"] = float(np.mean(pulse))

    # Valence estimate (brightness/positivity proxy)
    # Higher spectral centroid + major mode = more "positive"
    brightness = features["spectral_centroid"] / (sr / 2)  # Normalize to 0-1
    mode_factor = 0.6 if features["mode"] == 1 else 0.4
    features["valence"] = float(np.clip(brightness * 1.5 * mode_factor + 0.2, 0, 1))

    return features


def analyze_and_store(track_id: str, file_path: str | Path) -> dict:
    """Analyze audio and store features in database."""
    features = analyze_audio(file_path)

    with get_db() as conn:
        conn.execute("""
            INSERT INTO audio_features
                (track_id, bpm, energy, danceability, valence, loudness,
                 key, mode, spectral_centroid, spectral_rolloff, zero_crossing_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(track_id) DO UPDATE SET
                bpm = excluded.bpm,
                energy = excluded.energy,
                danceability = excluded.danceability,
                valence = excluded.valence,
                loudness = excluded.loudness,
                key = excluded.key,
                mode = excluded.mode,
                spectral_centroid = excluded.spectral_centroid,
                spectral_rolloff = excluded.spectral_rolloff,
                zero_crossing_rate = excluded.zero_crossing_rate,
                analyzed_at = CURRENT_TIMESTAMP
        """, (
            track_id,
            features["bpm"],
            features["energy"],
            features["danceability"],
            features["valence"],
            features["loudness"],
            features["key"],
            features["mode"],
            features["spectral_centroid"],
            features["spectral_rolloff"],
            features["zero_crossing_rate"],
        ))

    return features


def get_key_name(key: int, mode: int) -> str:
    """Convert numeric key/mode to Camelot notation."""
    keys = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    # Camelot wheel mapping
    camelot_major = ["8B", "3B", "10B", "5B", "12B", "7B", "2B", "9B", "4B", "11B", "6B", "1B"]
    camelot_minor = ["5A", "12A", "7A", "2A", "9A", "4A", "11A", "6A", "1A", "8A", "3A", "10A"]

    key_name = keys[key]
    mode_name = "maj" if mode == 1 else "min"
    camelot = camelot_major[key] if mode == 1 else camelot_minor[key]

    return f"{key_name} {mode_name} ({camelot})"


def batch_analyze(file_paths: list[tuple[str, Path]], progress_callback=None) -> dict:
    """
    Analyze multiple files.

    file_paths: list of (track_id, file_path) tuples
    Returns: dict with success/failure counts and results
    """
    results = {"success": 0, "failed": 0, "tracks": []}

    for i, (track_id, file_path) in enumerate(file_paths):
        try:
            features = analyze_and_store(track_id, file_path)
            results["success"] += 1
            results["tracks"].append({
                "track_id": track_id,
                "bpm": features["bpm"],
                "key": get_key_name(features["key"], features["mode"]),
                "energy": features["energy"],
            })
        except Exception as e:
            results["failed"] += 1
            results["tracks"].append({
                "track_id": track_id,
                "error": str(e),
            })

        if progress_callback:
            progress_callback(i + 1, len(file_paths))

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python audio_analysis.py <audio_file>")
        print("\nExample: python audio_analysis.py ~/Music/track.mp3")
        sys.exit(1)

    file_path = sys.argv[1]
    print(f"Analyzing: {file_path}")
    print("-" * 40)

    try:
        features = analyze_audio(file_path)
        print(f"BPM:          {features['bpm']:.1f}")
        print(f"Key:          {get_key_name(features['key'], features['mode'])}")
        print(f"Energy:       {features['energy']:.2f}")
        print(f"Danceability: {features['danceability']:.2f}")
        print(f"Valence:      {features['valence']:.2f}")
        print(f"Loudness:     {features['loudness']:.1f} dB")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
