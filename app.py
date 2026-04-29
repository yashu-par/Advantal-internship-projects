import streamlit as st
import pickle
import pandas as pd
import scipy.sparse as sp
import numpy as np
from datetime import datetime
import re

def genre_tokenizer(text):
    return [g.strip() for g in text.split(',')]

# ── Load Models ───────────────────────────────────────────────────────────────
with open('knn_model.pkl', 'rb') as f:
    knn_model = pickle.load(f)
with open('rf_model.pkl', 'rb') as f:
    rf_model = pickle.load(f)
with open('vectorizer_mood.pkl', 'rb') as f:
    vectorizer_mood = pickle.load(f)
with open('feature_matrix.pkl', 'rb') as f:
    feature_matrix = pickle.load(f)
with open('df_with_mood.pkl', 'rb') as f:
    df = pickle.load(f)

# ── Session State ─────────────────────────────────────────────────────────────
for key, val in {
    'liked_songs': [], 'history': [], 'recently_played': [],
    'search_results': None, 'search_message': '', 'mood_counter': {},
    'mood_pool': {},
    'search_result_artists': [],
    'search_no_result': False,
    'search_no_result_query': '',
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Constants ─────────────────────────────────────────────────────────────────
MOOD_COLORS = {
    'sad': '#4A90D9', 'party': '#F5A623', 'happy': '#F8E71C',
    'chill': '#7ED321', 'romantic': '#E91429', 'energetic': '#FF6B35',
    'angry': '#D0021B', 'calm': '#9B59B6'
}
MOOD_EMOJI = {
    'sad': '😢', 'party': '🎉', 'happy': '😊', 'chill': '😌',
    'romantic': '❤️', 'energetic': '⚡', 'angry': '😤', 'calm': '🧘'
}

mood_keywords = {
    'sad': ['sad songs','breakup songs','heartbreak songs','crying songs','emotional songs',
            'dard bhari','dukh bhari','sad music','sad','cry','crying','depressed','heartbreak',
            'broken heart','lonely','alone','tears','upset','grief','sorrow','dukhi','dard',
            'dramatic','emotional','touching','teary','melancholy','painful','pain','missing',
            'breakup','tragedy','tragic','rona','tanha','judai','bichhad','aansu','udaas','gham'],
    'party': ['party songs','dance songs','club songs','party music','dance music','party',
              'dancing','club','dj','night out','celebration','banger','hype','disco','rave',
              'nacho','dhoom','dance party','nightclub'],
    'happy': ['happy songs','feel good songs','positive songs','fun songs','happy music',
              'happy','fun','cheerful','joyful','good vibes','positive','upbeat','excited',
              'khush','smile','joy','masti','khushi','anand','celebration'],
    'chill': ['chill songs','relax songs','lofi songs','background music','chill music',
              'chill','relax','relaxing','lazy','lofi','lo-fi','mellow','vibes','evening',
              'coffee','rainy day','rain','slow','night vibes','bedroom'],
    'romantic': ['love songs','romantic songs','romance songs','romantic music','romantic',
                 'romance','love','lover','date','crush','sweet','pyaar','ishq','mohabbat',
                 'valentine','wedding','pyar','dil','dildar'],
    'energetic': ['workout songs','gym songs','running songs','motivation songs','hip hop songs',
                  'rap songs','energetic music','workout','gym','running','exercise','pump',
                  'motivation','hustle','beast','fire','cardio','training','power','adrenaline','gains'],
    'angry': ['rock songs','metal songs','punk songs','aggressive songs','angry songs','rock music',
              'metal music','rock','metal','punk','hardcore','rage','angry','aggressive','rebel',
              'headbang','screamo','thrash'],
    'calm': ['sleep songs','study songs','meditation songs','devotional songs','classical songs',
             'instrumental songs','peaceful songs','calm music','sleep','study','meditation',
             'devotional','classical','instrumental','peaceful','piano','ambient','bhajan',
             'spiritual','mantra','yoga','focus','concentration','devotes','shanti','arati','pooja']
}
genre_map = {
    'punjabi':'punjabi','hindi':'hindi','bollywood':'hindi','classical':'classical',
    'jazz':'jazz','blues':'blues','country':'country','folk':'folk','indie':'indie',
    'metal':'metal','trap':'trap','edm':'edm','electronic':'electro','house':'house',
    'soul':'soul','reggae':'reggae','latin':'latin','kpop':'k-pop','afrobeat':'afrobeat',
    'lofi':'lofi','phonk':'phonk'
}
exact_genre_map = {
    'pop':'pop','rap':'rap','rock':'rock','english':'pop','western':'pop',
    'k-pop':'k-pop','korean':'k-pop','r&b':'r&b','rnb':'r&b','gospel':'gospel'
}

# ── Detect Functions ──────────────────────────────────────────────────────────
def detect_mood(txt):
    for mood, kws in mood_keywords.items():
        for kw in sorted(kws, key=len, reverse=True):
            if kw in txt: return mood
    return None

def detect_genre(txt):
    for k, v in genre_map.items():
        if k in txt: return v
    words = set(re.findall(r'\b\w[\w&-]*\b', txt))
    for k, v in exact_genre_map.items():
        if k in words: return v
    return None

def detect_artist(txt):
    for artist in df['artist_name'].unique():
        if len(artist) > 3 and re.search(r'\b'+re.escape(artist.lower())+r'\b', txt):
            return artist
    return None

def detect_song(txt):
    # ONLY exact match — no partial matching at all
    # This prevents "Feather" matching "White Feather", "Daylight" matching "Daylight Eyes" etc.
    txt_stripped = txt.strip()
    for song in df['track_name'].tolist():
        if song.lower() == txt_stripped:
            return song
    return None

# ── KNN Similar Songs — FIXED ─────────────────────────────────────────────────
def get_knn_similar(song_name, n):
    """
    Returns top-n KNN similar songs:
    - Excludes the searched song itself
    - Deduplicates by track_name (removes duplicate entries)
    - Tries to diversify artists (max 2 songs per artist)
    - Falls back to include same-artist songs if not enough diverse results
    """
    matches = df[df['track_name'].str.lower() == song_name.lower()]
    if matches.empty:
        return None

    position = df.index.get_loc(matches.index[0])
    original_song   = matches.iloc[0]['track_name']
    original_artist = matches.iloc[0]['artist_name']

    # Ask for many more neighbors to have room to filter
    k = min(n * 8 + 20, len(df) - 1)
    distances, indices = knn_model.kneighbors(feature_matrix[position], n_neighbors=k)

    result = df.iloc[indices[0][1:]]  # skip index 0 (the song itself)

    # Remove the searched song by exact name (handles duplicate rows)
    result = result[result['track_name'].str.lower() != original_song.lower()]

    # Deduplicate by track_name — keep first occurrence (closest neighbor)
    result = result.drop_duplicates(subset='track_name', keep='first')

    # Build diverse list: max 2 songs per artist
    artist_count = {}
    diverse_rows = []
    rest_rows    = []

    for _, row in result.iterrows():
        artist = row['artist_name']
        count  = artist_count.get(artist, 0)
        if count < 2:
            diverse_rows.append(row)
            artist_count[artist] = count + 1
        else:
            rest_rows.append(row)
        if len(diverse_rows) >= n:
            break

    # If still not enough, fill from rest
    if len(diverse_rows) < n:
        needed = n - len(diverse_rows)
        diverse_rows.extend(rest_rows[:needed])

    if not diverse_rows:
        return None

    return pd.DataFrame(diverse_rows).head(n)


# ── Smart Search — FIXED ──────────────────────────────────────────────────────
def smart_search(user_input, n):
    """
    Returns (DataFrame, message) or (None, None) if nothing found.

    Order:
    1. Exact song name match → KNN similar songs
    2. Artist name match → their top songs
    3. Mood keywords → mood songs
    4. Genre keywords → genre songs
    5. Nothing matched → NO RESULT (no RF fallback, no random songs)
    """
    txt = user_input.lower().strip()

    # 1. Exact song name
    song = detect_song(txt)
    if song:
        r = get_knn_similar(song, n)
        if r is not None and not r.empty:
            return r, f"🎵 Similar to: **{song}**"
        else:
            return None, None

    # 2. Artist name
    artist = detect_artist(txt)
    if artist:
        f = df[df['artist_name'].str.lower() == artist.lower()]
        if not f.empty:
            return f.nlargest(n, 'track_popularity'), f"🎤 Artist: **{artist}**"

    # 3. Mood keywords
    mood = detect_mood(txt)
    if mood:
        f = df[df['mood'] == mood]
        if not f.empty:
            return f.nlargest(n, 'track_popularity'), f"{MOOD_EMOJI.get(mood,'🎵')} **{mood.upper()}** mood"

    # 4. Genre keywords
    genre = detect_genre(txt)
    if genre:
        f = df[df['artist_genres'].str.contains(genre, case=False, na=False)]
        if not f.empty:
            return f.nlargest(n, 'track_popularity'), f"🎸 Genre: **{genre.upper()}**"

    # 5. Nothing matched — show no result, do NOT recommend random songs
    return None, None


# ── Personalized Recommendations — 50% mood + 50% artist ─────────────────────
def get_personalized(n=16):
    counter = st.session_state.mood_counter
    if not counter: return None

    # Songs already seen/liked — exclude from recommendations
    exclude = (
        {s["song"] for s in st.session_state.recently_played} |
        {s["song"] for s in st.session_state.liked_songs}
    )

    # ── Collect artists with priority score ───────────────────────────────────
    # Liked song artists → highest priority (+3)
    # History search result song artists → medium priority (+2)
    # Recently played (non-search) artists → lower priority (+1)
    artist_priority = {}

    for s in st.session_state.liked_songs:
        a = s.get("artist", "")
        if a:
            artist_priority[a] = artist_priority.get(a, 0) + 3

    for item in st.session_state.history:
        for sname in item.get("songs", []):
            match = df[df["track_name"] == sname]
            if not match.empty:
                a = match.iloc[0]["artist_name"]
                if a:
                    artist_priority[a] = artist_priority.get(a, 0) + 2

    for s in st.session_state.recently_played:
        if not s.get("is_search", False):
            a = s.get("artist", "")
            if a and a in df["artist_name"].values:
                artist_priority[a] = artist_priority.get(a, 0) + 1

    # Artists from search result songs (directly captured when search ran) — score +2
    for a in st.session_state.get("search_result_artists", []):
        if a:
            artist_priority[a] = artist_priority.get(a, 0) + 2

    # Top 6 artists by score
    unique_artists = [
        a for a, _ in sorted(artist_priority.items(), key=lambda x: x[1], reverse=True)
    ][:6]

    half        = n // 2    # 8 songs mood-based
    artist_half = n - half  # 8 songs artist-based

    # ── 50%: Mood-based ───────────────────────────────────────────────────────
    total = sum(counter.values())
    mood_collected, mood_exclude = [], set(exclude)
    for mood, count in sorted(counter.items(), key=lambda x: x[1], reverse=True):
        quota = max(1, round((count / total) * half))
        pool  = df[df["mood"] == mood]
        pool  = pool[~pool["track_name"].isin(mood_exclude)].drop_duplicates("track_name")
        pool  = pool.nlargest(quota + 5, "track_popularity").head(quota)
        if not pool.empty:
            mood_collected.append(pool)
            mood_exclude.update(pool["track_name"].tolist())
    mood_df = pd.concat(mood_collected).drop_duplicates("track_name") if mood_collected else pd.DataFrame()

    # ── 50%: Artist-based — songs from artists user interacted with ───────────
    artist_collected = []
    artist_exclude   = set(exclude) | set(mood_df["track_name"].tolist() if not mood_df.empty else [])

    if unique_artists:
        per_artist = max(1, artist_half // len(unique_artists))
        for artist in unique_artists:
            pool = df[df["artist_name"].str.lower() == artist.lower()]
            pool = pool[~pool["track_name"].isin(artist_exclude)].drop_duplicates("track_name")
            pool = pool.nlargest(per_artist + 3, "track_popularity").head(per_artist)
            if not pool.empty:
                artist_collected.append(pool)
                artist_exclude.update(pool["track_name"].tolist())

    artist_df = pd.concat(artist_collected).drop_duplicates("track_name") if artist_collected else pd.DataFrame()

    # ── Combine mood + artist, shuffle ────────────────────────────────────────
    frames = [f for f in [mood_df, artist_df] if not f.empty]
    if not frames: return None
    result = pd.concat(frames).drop_duplicates("track_name")
    rng = int(datetime.now().timestamp()) % 999
    return result.sample(frac=1, random_state=rng).reset_index(drop=True)


# ── Session Helpers ───────────────────────────────────────────────────────────
def update_mood_counter(mood):
    if mood:
        st.session_state.mood_counter[mood] = st.session_state.mood_counter.get(mood, 0) + 1

def add_recently_played(song_name, artist_name, mood, is_search=False, label=''):
    entry = {
        'song': song_name, 'artist': artist_name, 'mood': mood,
        'played_at': datetime.now().strftime("%I:%M %p"),
        'is_search': is_search, 'label': label
    }
    st.session_state.recently_played = [
        s for s in st.session_state.recently_played if s['song'] != song_name
    ]
    st.session_state.recently_played.insert(0, entry)
    if len(st.session_state.recently_played) > 20:
        st.session_state.recently_played = st.session_state.recently_played[:20]

def add_to_history(query, result_type, songs):
    ts = datetime.now().strftime("%d %b, %I:%M %p")
    # Avoid duplicate consecutive
    if st.session_state.history and st.session_state.history[0]['query'] == query:
        return
    st.session_state.history.insert(0, {
        'query': query, 'type': result_type, 'time': ts, 'songs': songs[:3]
    })
    if len(st.session_state.history) > 30:
        st.session_state.history = st.session_state.history[:30]

def is_liked(song_name):
    return any(s['song'] == song_name for s in st.session_state.liked_songs)

def toggle_like(song_name, artist_name, genre, mood, popularity):
    if is_liked(song_name):
        st.session_state.liked_songs = [
            s for s in st.session_state.liked_songs if s['song'] != song_name
        ]
    else:
        st.session_state.liked_songs.insert(0, {
            'song': song_name, 'artist': artist_name, 'genre': genre, 'mood': mood,
            'popularity': round(float(popularity)*100, 1),
            'liked_at': datetime.now().strftime("%d %b, %I:%M %p")
        })
        update_mood_counter(mood)
        add_recently_played(song_name, artist_name, mood)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0a0a0a !important; color: #FFFFFF; }
    section[data-testid="stSidebar"] { background-color: #000000; }

    .stTabs [data-baseweb="tab-list"] {
        background-color: #0a0a0a; border-bottom: 1px solid #1a1a1a; gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #6b6b6b; font-weight: 700; font-size: 13px;
        padding: 12px 20px; letter-spacing: 0.03em;
    }
    .stTabs [aria-selected="true"] {
        color: #FFFFFF !important; border-bottom: 2px solid #1DB954 !important;
    }

    .stButton > button {
        background-color: #1DB954 !important; color: #000 !important;
        border: none !important; border-radius: 50px !important;
        font-weight: 800 !important; font-size: 13px !important;
        padding: 10px 28px !important; letter-spacing: 0.06em;
        text-transform: uppercase; transition: all 0.2s;
    }
    .stButton > button:hover { background-color: #1ed760 !important; transform: scale(1.02); }

    .stTextInput > div > div > input {
        background-color: #1a1a1a !important; color: #FFFFFF !important;
        border: 1px solid #2a2a2a !important; border-radius: 8px !important;
        padding: 13px 20px !important; font-size: 14px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #1DB954 !important; box-shadow: 0 0 0 2px #1DB95430 !important;
    }

    .song-card {
        background: linear-gradient(135deg,#181818,#1c1c1c);
        border-radius: 12px; padding: 14px 18px; margin-bottom: 8px;
        border: 1px solid #252525; transition: all 0.2s ease;
    }
    .song-card:hover {
        background: linear-gradient(135deg,#222,#262626);
        border-color: #363636; transform: translateX(2px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.45);
    }
    .song-title  { font-size: 15px; font-weight: 700; color: #FFF; margin: 0 0 3px 0; }
    .song-artist { font-size: 13px; color: #B3B3B3; margin: 0 0 8px 0; }
    .mood-badge  {
        display: inline-block; padding: 3px 12px; border-radius: 50px;
        font-size: 11px; font-weight: 800; letter-spacing: 0.05em;
    }

    div[data-heart] > div > div > button {
        border-radius: 50% !important;
        width: 38px !important; height: 38px !important;
        min-width: 38px !important; padding: 0 !important;
        font-size: 16px !important; font-weight: 400 !important;
        text-transform: none !important; letter-spacing: 0 !important;
        line-height: 1 !important; transition: all 0.18s ease !important;
    }
    div[data-heart="off"] > div > div > button {
        background: #181818 !important; color: #888 !important;
        border: 1.5px solid #383838 !important;
    }
    div[data-heart="off"] > div > div > button:hover {
        background: #200808 !important; border-color: #E91429 !important;
        box-shadow: 0 0 10px rgba(233,20,41,0.3) !important;
        transform: scale(1.15) !important;
    }
    div[data-heart="on"] > div > div > button {
        background: #1a0505 !important; color: #E91429 !important;
        border: 1.5px solid #E91429 !important;
    }
    div[data-heart="on"] > div > div > button:hover {
        background: #2a0808 !important; transform: scale(1.1) !important;
    }

    .recently-card {
        background: linear-gradient(160deg,#181818,#141414);
        border-radius: 12px; padding: 16px 10px; text-align: center;
        border: 1px solid #222; transition: all 0.25s ease;
        min-height: 148px; display: flex; flex-direction: column;
        justify-content: center; align-items: center;
    }
    .recently-card:hover {
        background: linear-gradient(160deg,#242424,#1e1e1e);
        border-color: #1DB95450; box-shadow: 0 6px 24px rgba(29,185,84,0.1);
        transform: translateY(-3px);
    }

    .mfy-card {
        background: linear-gradient(135deg,#181818,#1c1c1c);
        border-radius: 12px; padding: 14px 14px; margin-bottom: 8px;
        border: 1px solid #252525; transition: all 0.2s ease;
        height: 100%;
    }
    .mfy-card:hover {
        background: #242424; border-color: #333;
        transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.5);
    }
    .mfy-title  { font-size: 13px; font-weight: 700; color: #FFF; margin: 6px 0 3px 0;
                  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .mfy-artist { font-size: 11px; color: #B3B3B3; margin: 0 0 6px 0;
                  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

    .sec-head { font-size: 21px; font-weight: 800; color: #FFF; margin: 28px 0 4px 0; letter-spacing:-0.02em; }
    .sec-sub  { font-size: 12px; color: #6b6b6b; margin: 0 0 14px 0; }
    .green-divider { height: 2px; background: linear-gradient(90deg,#1DB954,transparent); margin: 8px 0 22px 0; border-radius: 2px; }

    .liked-card {
        background: linear-gradient(135deg,#160404,#181818);
        border-radius: 12px; padding: 14px 18px; margin-bottom: 8px;
        border-left: 3px solid #E91429; transition: all 0.2s;
    }
    .liked-card:hover { background: linear-gradient(135deg,#1e0606,#1e1e1e); }

    .history-item {
        background: #141414; border-radius: 10px; padding: 14px 18px;
        margin-bottom: 8px; border-left: 3px solid #1DB954; transition: background 0.2s;
    }
    .history-item:hover { background: #1a1a1a; }

    .mood-chip {
        display: inline-block; border-radius: 50px;
        padding: 3px 11px; font-size: 11px; font-weight: 700; margin-right: 6px; margin-bottom:4px;
    }

    /* No result box */
    .no-result {
        background: #141414; border-radius: 14px; padding: 48px 24px;
        text-align: center; border: 1px dashed #333; margin-top: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ── Song card renderer ────────────────────────────────────────────────────────
def show_songs(result, key_prefix=""):
    for i, (idx, row) in enumerate(result.iterrows()):
        mood  = row['mood']
        color = MOOD_COLORS.get(mood, '#1DB954')
        emoji = MOOD_EMOJI.get(mood, '🎵')
        liked = is_liked(row['track_name'])
        pop   = round(float(row['track_popularity'])*100, 1)

        col1, col2 = st.columns([12, 1])
        with col1:
            st.markdown(f"""
            <div class="song-card">
                <p class="song-title">🎵 {row['track_name']}</p>
                <p class="song-artist">{row['artist_name']}</p>
                <div style="display:flex;align-items:center;gap:10px;">
                    <span class="mood-badge" style="background:{color}22;color:{color};border:1px solid {color}50">
                        {emoji} {mood}
                    </span>
                    <span style="color:#535353;font-size:11px;">📊 {pop}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            state = "on" if liked else "off"
            heart = "❤️" if liked else "🤍"
            st.markdown(f'<div data-heart="{state}">', unsafe_allow_html=True)
            if st.button(heart, key=f"like_{key_prefix}_{idx}"):
                toggle_like(row['track_name'], row['artist_name'],
                            row['artist_genres'], row['mood'], row['track_popularity'])
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ── Made For You grid ─────────────────────────────────────────────────────────
def show_mfy_grid(songs_df, key_prefix="mfy"):
    cols = st.columns(4)
    for i, (_, row) in enumerate(songs_df.iterrows()):
        mood  = row['mood']
        color = MOOD_COLORS.get(mood, '#1DB954')
        emoji = MOOD_EMOJI.get(mood, '🎵')
        liked = is_liked(row['track_name'])
        state = "on" if liked else "off"
        heart = "❤️" if liked else "🤍"
        with cols[i % 4]:
            st.markdown(f"""
            <div class="mfy-card">
                <div style="font-size:24px;">{emoji}</div>
                <p class="mfy-title">{row['track_name']}</p>
                <p class="mfy-artist">{row['artist_name']}</p>
                <span class="mood-badge" style="background:{color}22;color:{color};border:1px solid {color}50;font-size:10px;">
                    {mood}
                </span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f'<div data-heart="{state}">', unsafe_allow_html=True)
            if st.button(heart, key=f"{key_prefix}_{i}_{str(row.name)[:4]}"):
                toggle_like(row['track_name'], row['artist_name'],
                            row['artist_genres'], row['mood'], row['track_popularity'])
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:16px;padding:20px 0 12px 0;">
    <div style="background:linear-gradient(135deg,#1DB954,#17a349);border-radius:16px;
                width:54px;height:54px;display:flex;align-items:center;justify-content:center;
                font-size:26px;box-shadow:0 8px 24px rgba(29,185,84,0.35);">🎵</div>
    <div>
        <div style="font-size:25px;font-weight:900;color:#FFF;letter-spacing:-0.03em;">Music Recommender</div>
        <div style="font-size:11px;color:#6b6b6b;letter-spacing:0.05em;text-transform:uppercase;">
            KNN + Random Forest · Spotify Style
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

tab_home, tab_search, tab_liked, tab_history = st.tabs(["🏠 Home","🔍 Search","❤️ Liked","🕐 History"])

# ══════════════════════════ HOME TAB ═════════════════════════════════════════
with tab_home:

    # ── Recently Played ──────────────────────────────────────────────────────
    st.markdown('<div class="sec-head">🕐 Recently Played</div>', unsafe_allow_html=True)
    rp = st.session_state.recently_played
    if rp:
        st.markdown('<div class="sec-sub">Your searches & liked songs</div>', unsafe_allow_html=True)
        cols = st.columns(4)
        for i, song in enumerate(rp[:8]):
            mood     = song.get('mood','happy')
            color    = MOOD_COLORS.get(mood,'#1DB954')
            emoji    = MOOD_EMOJI.get(mood,'🎵')
            is_srch  = song.get('is_search', False)
            icon     = "🔍" if is_srch else emoji
            tag      = "SEARCH" if is_srch else mood.upper()
            subtitle = song.get('label', song['artist']) if is_srch else song['artist']
            with cols[i%4]:
                st.markdown(f"""
                <div class="recently-card">
                    <div style="font-size:30px;margin-bottom:8px;">{icon}</div>
                    <div style="font-size:12px;font-weight:700;color:#FFF;overflow:hidden;
                                text-overflow:ellipsis;white-space:nowrap;max-width:100%;padding:0 6px;">
                        {song['song'][:16]}{'…' if len(song['song'])>16 else ''}
                    </div>
                    <div style="font-size:10px;color:#B3B3B3;margin-top:2px;overflow:hidden;
                                text-overflow:ellipsis;white-space:nowrap;max-width:100%;padding:0 6px;">
                        {str(subtitle)[:22]}{'…' if len(str(subtitle))>22 else ''}
                    </div>
                    <span style="font-size:10px;color:{color};font-weight:800;margin-top:5px;display:block;">{tag}</span>
                    <div style="font-size:10px;color:#535353;margin-top:3px;">🕐 {song['played_at']}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:28px 0;color:#6b6b6b;">
            <div style="font-size:44px;">🎧</div>
            <div style="font-size:15px;color:#B3B3B3;font-weight:700;margin-top:10px;">Nothing here yet</div>
            <div style="font-size:12px;margin-top:5px;">Search songs or like them — they appear here</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="green-divider"></div>', unsafe_allow_html=True)

    # ── Made For You ─────────────────────────────────────────────────────────
    mfy = get_personalized(n=16)
    if mfy is not None and not mfy.empty:
        st.markdown('<div class="sec-head">✨ Made For You</div>', unsafe_allow_html=True)
        counter = st.session_state.mood_counter
        if counter:
            chips = "".join(
                f'<span class="mood-chip" style="background:{MOOD_COLORS.get(m,"#1DB954")}25;color:{MOOD_COLORS.get(m,"#1DB954")};">'
                f'{MOOD_EMOJI.get(m,"🎵")} {m}</span>'
                for m in sorted(counter, key=counter.get, reverse=True)[:5]
            )
            st.markdown(
                f'<div style="margin:4px 0 14px 0;color:#6b6b6b;font-size:12px;">'
                f'Based on your taste · {chips}</div>',
                unsafe_allow_html=True
            )
        show_mfy_grid(mfy, key_prefix="mfy")
        st.markdown('<div class="green-divider"></div>', unsafe_allow_html=True)

    # ── Liked Songs Preview ──────────────────────────────────────────────────
    if st.session_state.liked_songs:
        st.markdown('<div class="sec-head">❤️ Your Liked Songs</div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-sub">Songs you saved</div>', unsafe_allow_html=True)
        for song in st.session_state.liked_songs[:5]:
            mood  = song.get('mood','happy')
            color = MOOD_COLORS.get(mood,'#1DB954')
            emoji = MOOD_EMOJI.get(mood,'🎵')
            st.markdown(f"""
            <div class="liked-card">
                <p class="song-title">🎵 {song['song']}</p>
                <p class="song-artist" style="margin-bottom:8px;">{song['artist']}</p>
                <span class="mood-badge" style="background:{color}22;color:{color};border:1px solid {color}50">
                    {emoji} {mood}
                </span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('<div class="green-divider"></div>', unsafe_allow_html=True)

    # ── Popular Right Now ────────────────────────────────────────────────────
    st.markdown('<div class="sec-head">🔥 Popular Right Now</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Top songs on the platform</div>', unsafe_allow_html=True)
    top_songs = df.nlargest(8,'track_popularity')
    cols_pop  = st.columns(4)
    for i,(_,row) in enumerate(top_songs.iterrows()):
        mood  = row['mood']
        color = MOOD_COLORS.get(mood,'#1DB954')
        emoji = MOOD_EMOJI.get(mood,'🎵')
        with cols_pop[i%4]:
            st.markdown(f"""
            <div class="recently-card" style="margin-bottom:10px;">
                <div style="font-size:26px;margin-bottom:8px;">{emoji}</div>
                <div style="font-size:12px;font-weight:700;color:#FFF;overflow:hidden;
                            text-overflow:ellipsis;white-space:nowrap;max-width:100%;padding:0 4px;">
                    {str(row['track_name'])[:18]}{'…' if len(str(row['track_name']))>18 else ''}
                </div>
                <div style="font-size:11px;color:#B3B3B3;margin-top:3px;">{row['artist_name']}</div>
                <span style="font-size:10px;color:{color};font-weight:800;margin-top:5px;display:block;">{mood.upper()}</span>
                <div style="font-size:10px;color:#1DB954;margin-top:3px;">📊 {round(row['track_popularity']*100,1)}</div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════ SEARCH TAB ═══════════════════════════════════════
with tab_search:
    st.markdown('<p style="color:#B3B3B3;font-size:13px;margin-top:8px;">Search by mood, genre, artist, or song name</p>', unsafe_allow_html=True)
    st.markdown("""<p style="font-size:12px;color:#535353;">
        Try: <span style="color:#1DB954;">sad songs</span> ·
        <span style="color:#1DB954;">party songs</span> ·
        <span style="color:#1DB954;">Taylor Swift</span> ·
        <span style="color:#1DB954;">Let Her Go</span> ·
        <span style="color:#1DB954;">punjabi songs</span> ·
        <span style="color:#1DB954;">gym music</span>
    </p>""", unsafe_allow_html=True)

    col1, col2 = st.columns([4,1])
    with col1:
        user_input = st.text_input("", placeholder="🔍 Search songs, mood, artist...",
                                   key="search_input", label_visibility="collapsed")
    with col2:
        n2 = st.slider("", 1, 10, 5, key="slider2", label_visibility="collapsed")

    if st.button("Find Songs 🎧", key="btn_search"):
        if not user_input.strip():
            st.warning("Please type something!")
        else:
            # Reset both states at the start of every search
            st.session_state.search_results = None
            st.session_state.search_message = ''
            st.session_state['search_no_result'] = False
            st.session_state['search_no_result_query'] = ''

            with st.spinner("🎵 Finding songs..."):
                result, message = smart_search(user_input, n2)

                if result is not None and not result.empty:
                    st.session_state.search_results = result
                    st.session_state.search_message = message
                    st.session_state['search_no_result'] = False

                    add_to_history(user_input, message, result['track_name'].tolist())

                    # Store result artists in session for Made For You 50% artist split
                    result_artists = result['artist_name'].dropna().unique().tolist()
                    existing = st.session_state.get('search_result_artists', [])
                    for a in result_artists:
                        if a not in existing:
                            existing.append(a)
                    st.session_state['search_result_artists'] = existing[:20]

                    detected_mood = detect_mood(user_input.lower().strip())
                    add_recently_played(
                        song_name=user_input,
                        artist_name=message,
                        mood=detected_mood if detected_mood else 'happy',
                        is_search=True,
                        label=message
                    )
                    if detected_mood:
                        update_mood_counter(detected_mood)

                else:
                    # Nothing found — strictly show no-result, no random songs
                    st.session_state.search_results = None
                    st.session_state.search_message = ''
                    st.session_state['search_no_result'] = True
                    st.session_state['search_no_result_query'] = user_input

    # ── Results display ───────────────────────────────────────────────────────
    if st.session_state.get('search_no_result'):
        query_shown = st.session_state.get('search_no_result_query', '')
        st.markdown(f"""
        <div class="no-result">
            <div style="font-size:52px;margin-bottom:14px;">🔍</div>
            <div style="font-size:19px;font-weight:800;color:#FFF;">Not found in our database</div>
            <div style="font-size:13px;color:#6b6b6b;margin-top:10px;">
                "<span style="color:#B3B3B3;">{query_shown}</span>" is not in our music library.
            </div>
            <div style="margin-top:16px;font-size:12px;color:#535353;line-height:1.8;">
                💡 Try searching by:<br>
                <span style="color:#1DB954;">mood</span> — sad, happy, chill, party, romantic<br>
                <span style="color:#1DB954;">genre</span> — punjabi, lofi, rock, edm, jazz<br>
                <span style="color:#1DB954;">artist name</span> — Taylor Swift, Arijit Singh<br>
                <span style="color:#1DB954;">song in DB</span> — Blinding Lights, Kesariya
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif st.session_state.search_results is not None:
        st.markdown(
            f'<div style="color:#1DB954;font-weight:700;font-size:14px;margin:14px 0 10px;">'
            f'Results: {st.session_state.search_message}</div>',
            unsafe_allow_html=True
        )
        show_songs(st.session_state.search_results, key_prefix="s1")

# ══════════════════════════ LIKED TAB ════════════════════════════════════════
with tab_liked:
    st.markdown('<div style="font-size:22px;font-weight:800;margin:12px 0 16px;">❤️ Liked Songs</div>', unsafe_allow_html=True)
    if not st.session_state.liked_songs:
        st.markdown("""
        <div style="text-align:center;padding:60px;color:#6b6b6b;">
            <div style="font-size:60px;">🤍</div>
            <div style="font-size:17px;font-weight:700;color:#FFF;margin-top:12px;">No liked songs yet</div>
            <div style="font-size:13px;margin-top:8px;">Press 🤍 on any song to save it here</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        col1, col2 = st.columns([3,1])
        with col1:
            st.markdown(f'<p style="color:#1DB954;font-weight:700;">❤️ {len(st.session_state.liked_songs)} songs liked</p>', unsafe_allow_html=True)
        with col2:
            if st.button("Clear All", key="clear_liked"):
                st.session_state.liked_songs = []
                st.rerun()
        for i, song in enumerate(st.session_state.liked_songs):
            mood  = song.get('mood','happy')
            color = MOOD_COLORS.get(mood,'#1DB954')
            emoji = MOOD_EMOJI.get(mood,'🎵')
            col1, col2 = st.columns([11,1])
            with col1:
                st.markdown(f"""
                <div class="liked-card">
                    <p class="song-title">🎵 {song['song']}</p>
                    <p class="song-artist" style="margin-bottom:8px;">{song['artist']}</p>
                    <span class="mood-badge" style="background:{color}22;color:{color};border:1px solid {color}50">
                        {emoji} {mood}
                    </span>
                    <span style="color:#535353;font-size:11px;margin-left:10px;">🕐 {song.get('liked_at','')}</span>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown('<div data-heart="on">', unsafe_allow_html=True)
                if st.button("❤️", key=f"unlike_{i}_{song['song'][:5]}"):
                    st.session_state.liked_songs = [
                        s for s in st.session_state.liked_songs if s['song'] != song['song']
                    ]
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════ HISTORY TAB ══════════════════════════════════════
with tab_history:
    st.markdown('<div style="font-size:22px;font-weight:800;margin:12px 0 16px;">🕐 Search History</div>', unsafe_allow_html=True)
    if not st.session_state.history:
        st.markdown("""
        <div style="text-align:center;padding:60px;color:#6b6b6b;">
            <div style="font-size:60px;">🕐</div>
            <div style="font-size:17px;font-weight:700;color:#FFF;margin-top:12px;">No history yet</div>
            <div style="font-size:13px;margin-top:8px;">Your searches appear here automatically</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        col1, col2 = st.columns([3,1])
        with col1:
            st.markdown(f'<p style="color:#B3B3B3;">{len(st.session_state.history)} searches saved</p>', unsafe_allow_html=True)
        with col2:
            if st.button("Clear", key="clear_hist"):
                st.session_state.history = []
                st.rerun()
        for item in st.session_state.history:
            preview = " · ".join(item.get('songs',[])[:3])
            st.markdown(f"""
            <div class="history-item">
                <p style="margin:0;font-weight:700;color:#FFF;font-size:14px;">🔍 {item['query']}</p>
                <p style="margin:4px 0;font-size:12px;color:#1DB954;">{item['type']}</p>
                <p style="margin:3px 0;font-size:11px;color:#B3B3B3;">🎵 {preview}</p>
                <p style="margin:0;font-size:11px;color:#535353;">🕐 {item['time']}</p>
            </div>
            """, unsafe_allow_html=True)