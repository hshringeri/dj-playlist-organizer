"""
DJ-focused track classification based on real mixing needs.

Inspired by: Four Tet, Skrillex, Boys Noize, Rufus Du Sol,
Floating Points, Burial, Aphex Twin, Peggy Gou
"""

from dataclasses import dataclass
from typing import Optional
from database import get_db


@dataclass
class DJFolder:
    """
    Defines a DJ folder based on when/how you'd use the track.

    Not generic "vibes" - actual mixing categories.
    """
    name: str
    description: str
    # Audio feature ranges
    bpm_min: float = 0.0
    bpm_max: float = 300.0
    energy_min: float = 0.0
    energy_max: float = 1.0
    valence_min: float = 0.0
    valence_max: float = 1.0
    danceability_min: float = 0.0
    danceability_max: float = 1.0
    # Weights for classification (how important each feature is)
    bpm_weight: float = 0.3
    energy_weight: float = 0.3
    valence_weight: float = 0.2
    danceability_weight: float = 0.2


# DJ folders based on real mixing needs and the artists' styles
DJ_FOLDERS = [
    # === SET POSITION / ENERGY ARC ===
    DJFolder(
        name="Openers",
        description="Warm-up tracks. Textural, patient, sets the mood without demanding attention. Think Floating Points vinyl-only sets.",
        bpm_min=95, bpm_max=122,
        energy_min=0.15, energy_max=0.45,
        valence_min=0.3, valence_max=0.7,
        danceability_min=0.3, danceability_max=0.6,
    ),
    DJFolder(
        name="Builders",
        description="Tracks that create momentum. Hypnotic, locked grooves that let you build without peaking too early. Four Tet mid-set energy.",
        bpm_min=118, bpm_max=130,
        energy_min=0.4, energy_max=0.65,
        valence_min=0.3, valence_max=0.6,
        danceability_min=0.5, danceability_max=0.8,
    ),
    DJFolder(
        name="Peak Time",
        description="Main room energy. The tracks people came for. Rufus Du Sol festival moments, Peggy Gou dancefloor weapons.",
        bpm_min=122, bpm_max=135,
        energy_min=0.65, energy_max=0.85,
        valence_min=0.5, valence_max=0.9,
        danceability_min=0.7, danceability_max=1.0,
    ),
    DJFolder(
        name="Weapons",
        description="Maximum impact. Drop these when the room is ready. Skrillex drops, Boys Noize bangers. Use sparingly.",
        bpm_min=125, bpm_max=150,
        energy_min=0.8, energy_max=1.0,
        valence_min=0.2, valence_max=0.8,
        danceability_min=0.6, danceability_max=1.0,
    ),
    DJFolder(
        name="Closers",
        description="Bring it down gracefully. Emotional, reflective, leaves them wanting more. Burial at 4am.",
        bpm_min=100, bpm_max=128,
        energy_min=0.2, energy_max=0.5,
        valence_min=0.2, valence_max=0.6,
        danceability_min=0.3, danceability_max=0.6,
    ),

    # === TEXTURE / FEEL ===
    DJFolder(
        name="Organic",
        description="Live instruments, samples, warmth. Four Tet's folk samples, Floating Points' jazz. Human feel.",
        bpm_min=100, bpm_max=135,
        energy_min=0.3, energy_max=0.7,
        valence_min=0.4, valence_max=0.8,
        danceability_min=0.4, danceability_max=0.8,
        # Higher valence weight for warmth detection
        valence_weight=0.35,
    ),
    DJFolder(
        name="Synthetic",
        description="Pure electronic. Clean, digital, precise. Boys Noize acid lines, Aphex Twin's machine music.",
        bpm_min=115, bpm_max=145,
        energy_min=0.5, energy_max=0.9,
        valence_min=0.2, valence_max=0.6,
        danceability_min=0.5, danceability_max=0.9,
    ),
    DJFolder(
        name="Gritty",
        description="Distorted, lo-fi, rough. Burial's crackle, Boys Noize distortion, Aphex Twin's chaos.",
        bpm_min=110, bpm_max=160,
        energy_min=0.4, energy_max=0.85,
        valence_min=0.1, valence_max=0.45,
        danceability_min=0.3, danceability_max=0.7,
    ),

    # === RHYTHM TYPE ===
    DJFolder(
        name="4x4 Locked",
        description="Steady four-on-the-floor. Hypnotic, driving. The backbone.",
        bpm_min=120, bpm_max=135,
        energy_min=0.5, energy_max=0.8,
        valence_min=0.3, valence_max=0.7,
        danceability_min=0.65, danceability_max=1.0,
        danceability_weight=0.4,
    ),
    DJFolder(
        name="Broken Beat",
        description="UK garage, 2-step, broken rhythms. Burial's shuffles, Four Tet's off-grid percussion.",
        bpm_min=125, bpm_max=140,
        energy_min=0.4, energy_max=0.75,
        valence_min=0.25, valence_max=0.6,
        danceability_min=0.4, danceability_max=0.7,
        # Lower danceability for broken beats
        danceability_weight=0.35,
    ),
    DJFolder(
        name="Halftime / Slow",
        description="Half-speed feel, trippy. Skrillex halftime drops, downtempo moments.",
        bpm_min=65, bpm_max=90,
        energy_min=0.4, energy_max=0.8,
        valence_min=0.2, valence_max=0.6,
        danceability_min=0.3, danceability_max=0.6,
    ),
    DJFolder(
        name="Fast & Chaotic",
        description="160+ BPM, jungle, breakcore, IDM. Aphex Twin drill n bass, Squarepusher territory.",
        bpm_min=155, bpm_max=180,
        energy_min=0.6, energy_max=1.0,
        valence_min=0.1, valence_max=0.7,
        danceability_min=0.3, danceability_max=0.8,
    ),

    # === EMOTIONAL TONE ===
    DJFolder(
        name="Melancholic",
        description="Beautiful sadness. Minor keys, emotional weight. Burial's rain-soaked London, Floating Points' Promises.",
        bpm_min=100, bpm_max=135,
        energy_min=0.2, energy_max=0.55,
        valence_min=0.1, valence_max=0.35,
        danceability_min=0.3, danceability_max=0.7,
        valence_weight=0.4,
    ),
    DJFolder(
        name="Euphoric",
        description="Pure joy. Major keys, uplifting. Rufus Du Sol sunsets, Peggy Gou's 'It Makes You Forget'.",
        bpm_min=118, bpm_max=132,
        energy_min=0.55, energy_max=0.85,
        valence_min=0.6, valence_max=1.0,
        danceability_min=0.6, danceability_max=0.95,
        valence_weight=0.4,
    ),
    DJFolder(
        name="Hypnotic",
        description="Trance-inducing repetition. Minimal changes, deep focus. Ricardo Villalobos territory.",
        bpm_min=118, bpm_max=130,
        energy_min=0.35, energy_max=0.6,
        valence_min=0.3, valence_max=0.55,
        danceability_min=0.55, danceability_max=0.8,
    ),
    DJFolder(
        name="Aggressive",
        description="Industrial, hard, confrontational. Boys Noize at full tilt, gabber-adjacent.",
        bpm_min=130, bpm_max=160,
        energy_min=0.75, energy_max=1.0,
        valence_min=0.1, valence_max=0.4,
        danceability_min=0.5, danceability_max=0.85,
    ),

    # === FUNCTIONAL ===
    DJFolder(
        name="Transitions",
        description="Tools for moving between sections. Ambient breakdowns, builds without drops, DJ tools.",
        bpm_min=100, bpm_max=140,
        energy_min=0.2, energy_max=0.5,
        valence_min=0.3, valence_max=0.7,
        danceability_min=0.2, danceability_max=0.5,
    ),
    DJFolder(
        name="Curveballs",
        description="Unexpected selections. Weird edits, genre-bending. Aphex Twin unpredictability, Four Tet playing 'Angel' by Massive Attack.",
        bpm_min=80, bpm_max=160,
        energy_min=0.3, energy_max=0.8,
        valence_min=0.2, valence_max=0.8,
        danceability_min=0.2, danceability_max=0.7,
    ),
]


def init_folders(folders: list[DJFolder] = None):
    """Initialize DJ folder categories in database."""
    folders = folders or DJ_FOLDERS

    with get_db() as conn:
        for folder in folders:
            conn.execute("""
                INSERT INTO vibes (name, description, energy_min, energy_max,
                                   valence_min, valence_max, bpm_min, bpm_max)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    description = excluded.description,
                    energy_min = excluded.energy_min,
                    energy_max = excluded.energy_max,
                    valence_min = excluded.valence_min,
                    valence_max = excluded.valence_max,
                    bpm_min = excluded.bpm_min,
                    bpm_max = excluded.bpm_max
            """, (
                folder.name, folder.description,
                folder.energy_min, folder.energy_max,
                folder.valence_min, folder.valence_max,
                folder.bpm_min, folder.bpm_max,
            ))

    print(f"Initialized {len(folders)} DJ folders")


def classify_track(track_id: str, folders: list[DJFolder] = None) -> list[tuple[str, float]]:
    """
    Classify a track into DJ folders based on audio features.

    Returns list of (folder_name, confidence) tuples, sorted by confidence.
    """
    folders = folders or DJ_FOLDERS

    with get_db() as conn:
        features = conn.execute("""
            SELECT bpm, energy, valence, danceability
            FROM audio_features WHERE track_id = ?
        """, (track_id,)).fetchone()

        if not features:
            return []

        bpm, energy, valence, danceability = features

    matches = []
    for folder in folders:
        confidence = calculate_folder_confidence(
            bpm, energy, valence, danceability, folder
        )
        if confidence > 0.3:  # Minimum threshold
            matches.append((folder.name, confidence))

    return sorted(matches, key=lambda x: x[1], reverse=True)


def calculate_folder_confidence(
    bpm: float,
    energy: float,
    valence: float,
    danceability: float,
    folder: DJFolder,
) -> float:
    """Calculate how well a track fits a DJ folder."""

    def range_score(value, min_val, max_val):
        """Score based on how well value fits in range."""
        if min_val <= value <= max_val:
            # Inside range - score based on position
            center = (min_val + max_val) / 2
            range_size = max_val - min_val
            if range_size == 0:
                return 1.0
            # Perfect center = 1.0, edges = 0.7
            distance = abs(value - center) / (range_size / 2)
            return 1.0 - (distance * 0.3)
        else:
            # Outside range - penalty based on distance
            if value < min_val:
                distance = (min_val - value) / (max_val - min_val + 0.01)
            else:
                distance = (value - max_val) / (max_val - min_val + 0.01)
            return max(0, 1.0 - distance * 1.5)

    bpm_score = range_score(bpm, folder.bpm_min, folder.bpm_max)
    energy_score = range_score(energy, folder.energy_min, folder.energy_max)
    valence_score = range_score(valence, folder.valence_min, folder.valence_max)
    dance_score = range_score(danceability, folder.danceability_min, folder.danceability_max)

    # Weighted combination
    total_weight = (folder.bpm_weight + folder.energy_weight +
                    folder.valence_weight + folder.danceability_weight)

    weighted = (
        (bpm_score * folder.bpm_weight) +
        (energy_score * folder.energy_weight) +
        (valence_score * folder.valence_weight) +
        (dance_score * folder.danceability_weight)
    ) / total_weight

    # Hard requirements: BPM must be somewhat close
    if bpm_score < 0.2:
        return 0.0

    return round(weighted, 3)


def classify_all_tracks() -> dict:
    """Classify all analyzed tracks into DJ folders."""
    with get_db() as conn:
        tracks = conn.execute("SELECT track_id FROM audio_features").fetchall()

        results = {"classified": 0, "total": len(tracks)}

        for (track_id,) in tracks:
            folders = classify_track(track_id)

            # Clear old classifications
            conn.execute("DELETE FROM track_vibes WHERE track_id = ?", (track_id,))

            # Store top 3 folder matches
            for folder_name, confidence in folders[:3]:
                vibe_id = conn.execute(
                    "SELECT id FROM vibes WHERE name = ?", (folder_name,)
                ).fetchone()
                if vibe_id:
                    conn.execute("""
                        INSERT INTO track_vibes (track_id, vibe_id, confidence)
                        VALUES (?, ?, ?)
                    """, (track_id, vibe_id[0], confidence))

            if folders:
                results["classified"] += 1

        return results


def get_folder_summary() -> list[dict]:
    """Get summary of tracks per folder, ordered by total plays."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                v.name,
                v.description,
                COUNT(DISTINCT tv.track_id) as track_count,
                COALESCE(SUM(ts.play_count), 0) as total_plays,
                ROUND(AVG(af.bpm), 1) as avg_bpm,
                ROUND(MIN(af.bpm), 0) as min_bpm,
                ROUND(MAX(af.bpm), 0) as max_bpm
            FROM vibes v
            LEFT JOIN track_vibes tv ON v.id = tv.vibe_id
            LEFT JOIN audio_features af ON tv.track_id = af.track_id
            LEFT JOIN track_stats ts ON tv.track_id = ts.track_id
            GROUP BY v.id
            ORDER BY total_plays DESC
        """).fetchall()

        return [dict(row) for row in rows]


def get_tracks_in_folder(folder_name: str, bpm_min: float = 0, bpm_max: float = 300) -> list[dict]:
    """Get tracks in a folder, optionally filtered by BPM."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                t.id, t.name, t.artist,
                af.bpm, af.energy, af.valence, af.key, af.mode,
                tv.confidence,
                COALESCE(ts.play_count, 0) as play_count
            FROM tracks t
            JOIN track_vibes tv ON t.id = tv.track_id
            JOIN vibes v ON tv.vibe_id = v.id
            JOIN audio_features af ON t.id = af.track_id
            LEFT JOIN track_stats ts ON t.id = ts.track_id
            WHERE v.name = ?
              AND af.bpm >= ? AND af.bpm <= ?
            ORDER BY ts.play_count DESC, tv.confidence DESC
        """, (folder_name, bpm_min, bpm_max)).fetchall()

        return [dict(row) for row in rows]


def get_bpm_buckets_for_folder(folder_name: str, bucket_size: int = 5) -> list[dict]:
    """Get BPM distribution within a folder."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                CAST(af.bpm / ? AS INT) * ? as bpm_bucket,
                COUNT(*) as track_count,
                SUM(COALESCE(ts.play_count, 0)) as total_plays
            FROM tracks t
            JOIN track_vibes tv ON t.id = tv.track_id
            JOIN vibes v ON tv.vibe_id = v.id
            JOIN audio_features af ON t.id = af.track_id
            LEFT JOIN track_stats ts ON t.id = ts.track_id
            WHERE v.name = ?
            GROUP BY bpm_bucket
            ORDER BY total_plays DESC
        """, (bucket_size, bucket_size, folder_name)).fetchall()

        return [
            {
                "bpm_range": f"{row['bpm_bucket']}-{row['bpm_bucket'] + bucket_size}",
                "track_count": row["track_count"],
                "total_plays": row["total_plays"],
            }
            for row in rows
        ]


def print_folder_tree():
    """Print DJ folders organized by category."""
    categories = {
        "SET POSITION": ["Openers", "Builders", "Peak Time", "Weapons", "Closers"],
        "TEXTURE": ["Organic", "Synthetic", "Gritty"],
        "RHYTHM": ["4x4 Locked", "Broken Beat", "Halftime / Slow", "Fast & Chaotic"],
        "EMOTIONAL": ["Melancholic", "Euphoric", "Hypnotic", "Aggressive"],
        "FUNCTIONAL": ["Transitions", "Curveballs"],
    }

    folder_map = {f.name: f for f in DJ_FOLDERS}

    for category, folder_names in categories.items():
        print(f"\n{'='*60}")
        print(f"  {category}")
        print(f"{'='*60}")
        for name in folder_names:
            if name in folder_map:
                f = folder_map[name]
                print(f"\n  {f.name}")
                print(f"    {f.description[:70]}...")
                print(f"    BPM: {f.bpm_min:.0f}-{f.bpm_max:.0f} | "
                      f"Energy: {f.energy_min:.1f}-{f.energy_max:.1f}")


if __name__ == "__main__":
    from database import init_db

    init_db()

    print("\n" + "="*60)
    print("  DJ FOLDER STRUCTURE")
    print("="*60)

    print_folder_tree()

    print("\n\nInitializing folders in database...")
    init_folders()

    print("\nClassifying tracks...")
    results = classify_all_tracks()
    print(f"Classified {results['classified']}/{results['total']} tracks")

    summary = get_folder_summary()
    if any(s["track_count"] > 0 for s in summary):
        print("\n" + "="*60)
        print("  FOLDER SUMMARY (by plays)")
        print("="*60)
        for s in summary:
            if s["track_count"] > 0:
                bpm_info = f"BPM {s['min_bpm']:.0f}-{s['max_bpm']:.0f}" if s['min_bpm'] else ""
                print(f"  {s['name']:20} | {s['track_count']:3} tracks | "
                      f"{s['total_plays']:4} plays | {bpm_info}")
