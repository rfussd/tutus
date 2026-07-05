from __future__ import annotations

import os
from typing import Any

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def get_spotify() -> Any:
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
            scope="user-read-playback-state user-modify-playback-state user-read-currently-playing",
        )
    )


def _get_active_device() -> Any:
    sp = get_spotify()
    devices = sp.devices()["devices"]
    if not devices:
        raise Exception("Spotify no tiene dispositivos activos. Ábrelo primero.")
    return sp, devices[0]["id"]


def spotify_play(query: str) -> str:
    try:
        import re
        import unicodedata

        def _norm(s: str) -> str:
            s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
            return re.sub(r"[^a-z0-9\s]", "", s.lower()).strip()

        sp, device_id = _get_active_device()

        # Extraer canción y artista de la query
        song_part, artist_part = query, ""
        for sep in (" de ", " del ", " por ", " - ", " by "):
            if sep in query.lower():
                parts = re.split(sep, query, maxsplit=1, flags=re.IGNORECASE)
                song_part = parts[0].strip().strip("'\"¿?¡!")
                artist_part = parts[1].strip().strip("'\"¿?¡!")
                break

        # Intentar búsqueda específica con formato Spotify
        search_queries = [query]
        if artist_part:
            search_queries.insert(0, f"track:{song_part} artist:{artist_part}")

        all_tracks = []
        for sq in search_queries:
            results = sp.search(q=sq, type="track", limit=10)
            all_tracks.extend(results["tracks"]["items"])

        # Dedicar resultados por URI
        seen = set()
        tracks = []
        for t in all_tracks:
            if t["uri"] not in seen:
                seen.add(t["uri"])
                tracks.append(t)

        if not tracks:
            return f"No encontré '{query}' en Spotify."

        sn = _norm(song_part)
        an = _norm(artist_part) if artist_part else ""

        best = tracks[0]
        best_score = -1

        for t in tracks:
            tn = _norm(t["name"])
            ta = _norm(" ".join(a["name"] for a in t["artists"]))
            score = 0

            # Coincidencia exacta de canción (lo más importante)
            if tn == sn:
                score += 50
            elif sn in tn or tn in sn:
                score += 30

            # Coincidencia de palabras de la canción
            sn_words = set(sn.split())
            tn_words = set(tn.split())
            common = sn_words & tn_words
            score += len(common) * 5

            # Coincidencia de artista
            if an:
                if ta == an:
                    score += 20
                elif an in ta or ta in an:
                    score += 10

            if score > best_score:
                best_score = score
                best = t

        sp.start_playback(device_id=device_id, uris=[best["uri"]])
        artists = ", ".join(a["name"] for a in best["artists"])
        return f"Reproduciendo: {best['name']} — {artists}"
    except Exception as e:
        return f"Error Spotify: {str(e)}"


def spotify_pause() -> str:
    try:
        sp, _ = _get_active_device()
        sp.pause_playback()
        return "Spotify pausado."
    except Exception as e:
        return f"Error: {str(e)}"


def spotify_next() -> str:
    try:
        sp, _ = _get_active_device()
        sp.next_track()
        return "Siguiente canción."
    except Exception as e:
        return f"Error: {str(e)}"


def spotify_previous() -> str:
    try:
        sp, _ = _get_active_device()
        sp.previous_track()
        return "Canción anterior."
    except Exception as e:
        return f"Error: {str(e)}"


def spotify_volume(volume: int = 50) -> str:
    try:
        sp, device_id = _get_active_device()
        sp.volume(int(volume), device_id=device_id)
        return f"Volumen al {volume}%."
    except Exception as e:
        return f"Error: {str(e)}"


def spotify_playlist(query: str) -> str:
    try:
        sp, device_id = _get_active_device()
        results = sp.search(q=query, type="playlist", limit=5)
        playlists = [p for p in results["playlists"]["items"] if p]
        if not playlists:
            return f"No encontré playlist '{query}'."
        playlist = playlists[0]
        sp.start_playback(device_id=device_id, context_uri=playlist["uri"])
        return f"Reproduciendo playlist: {playlist['name']}"
    except Exception as e:
        return f"Error playlist: {str(e)}"
