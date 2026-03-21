"""
Quranic Arabic Corpus — Interactive Dashboard
Run: python3 -m streamlit run app.py
"""

import sqlite3
import pandas as pd
import streamlit as st

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Quranic Corpus Explorer",
    page_icon="📖",
    layout="wide",
)

# RTL CSS for Arabic text
st.markdown("""
<style>
    .arabic { direction: rtl; text-align: right; font-size: 1.4em; font-family: 'Traditional Arabic', 'Amiri', 'Noto Naskh Arabic', serif; line-height: 2; }
    .arabic-large { direction: rtl; text-align: right; font-size: 2em; font-family: 'Traditional Arabic', 'Amiri', 'Noto Naskh Arabic', serif; line-height: 2.2; }
    .metric-card { background: #f0f2f6; border-radius: 10px; padding: 15px; text-align: center; }
    .stDataFrame td { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)


# ── Database connection ─────────────────────────────────────────────────────
@st.cache_resource
def get_db():
    return sqlite3.connect("quran.db", check_same_thread=False)

def sql(query, params=None):
    return pd.read_sql_query(query, get_db(), params=params)


# ── Sidebar ─────────────────────────────────────────────────────────────────
st.sidebar.title("📖 Quran Explorer")
page = st.sidebar.radio("Pagina", [
    "🔍 Vers opzoeken",
    "🌳 Wortel zoeken",
    "📊 Statistieken",
    "📝 Vrije SQL query",
])


# ── Page: Vers opzoeken ────────────────────────────────────────────────────
if page == "🔍 Vers opzoeken":
    st.title("🔍 Vers opzoeken")

    col1, col2 = st.columns(2)
    surah = col1.number_input("Soera", min_value=1, max_value=114, value=1)

    max_ayah = sql("SELECT MAX(ayah) as m FROM ayat WHERE surah = ?", [surah]).iloc[0]['m']
    ayah = col2.number_input("Vers", min_value=1, max_value=int(max_ayah), value=1)

    # Show verse
    verse = sql("SELECT verse_ar FROM ayat WHERE surah = ? AND ayah = ?", [surah, ayah])
    if not verse.empty:
        st.markdown(f'<div class="arabic-large">{verse.iloc[0]["verse_ar"]}</div>', unsafe_allow_html=True)

    # Show word-by-word breakdown
    st.subheader("Woord-voor-woord analyse")
    words = sql("""
        SELECT word, form_ar, pos, lemma_ar, root_ar, aspect, verb_form, 
               gender, number, "case"
        FROM corpus 
        WHERE surah = ? AND ayah = ? AND segment_type = 'STEM'
        ORDER BY word
    """, [surah, ayah])
    st.dataframe(words, use_container_width=True, hide_index=True)

    # Show all segments
    with st.expander("Alle segmenten (incl. prefixen en suffixen)"):
        segments = sql("""
            SELECT word, segment, form_ar, tag, segment_type, pos, lemma_ar, root_ar
            FROM corpus 
            WHERE surah = ? AND ayah = ?
            ORDER BY word, segment
        """, [surah, ayah])
        st.dataframe(segments, use_container_width=True, hide_index=True)


# ── Page: Wortel zoeken ────────────────────────────────────────────────────
elif page == "🌳 Wortel zoeken":
    st.title("🌳 Wortel zoeken")

    root = st.text_input("Arabische wortel (bijv. رحم, علم, كتب)", value="رحم")

    if root:
        # Summary
        stats = sql("""
            SELECT COUNT(*) as voorkomens,
                   COUNT(DISTINCT lemma) as unieke_lemmas,
                   COUNT(DISTINCT surah) as in_soeras
            FROM corpus WHERE root_ar = ?
        """, [root])
        
        if not stats.empty and stats.iloc[0]['voorkomens'] > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("Voorkomens", f"{stats.iloc[0]['voorkomens']:,}")
            c2.metric("Unieke lemma's", stats.iloc[0]['unieke_lemmas'])
            c3.metric("In soera's", stats.iloc[0]['in_soeras'])

            # Derived forms
            st.subheader("Afgeleide vormen")
            derivations = sql("""
                SELECT lemma_ar, pos, COUNT(*) as freq,
                       GROUP_CONCAT(DISTINCT form_ar) as vormen
                FROM corpus WHERE root_ar = ?
                GROUP BY lemma_ar, pos
                ORDER BY freq DESC
            """, [root])
            st.dataframe(derivations, use_container_width=True, hide_index=True)

            # Verses containing this root
            st.subheader("Verzen met deze wortel")
            verses = sql("""
                SELECT DISTINCT c.surah, c.ayah, c.form_ar, a.verse_ar
                FROM corpus c
                JOIN ayat a ON c.surah = a.surah AND c.ayah = a.ayah
                WHERE c.root_ar = ?
                ORDER BY c.surah, c.ayah
                LIMIT 50
            """, [root])
            for _, row in verses.iterrows():
                st.markdown(
                    f"**{row['surah']}:{row['ayah']}** — "
                    f'<span class="arabic">{row["verse_ar"]}</span>',
                    unsafe_allow_html=True
                )
        else:
            st.warning(f"Wortel '{root}' niet gevonden.")


# ── Page: Statistieken ─────────────────────────────────────────────────────
elif page == "📊 Statistieken":
    st.title("📊 Corpus Statistieken")

    # Global stats
    c1, c2, c3, c4 = st.columns(4)
    total = sql("SELECT COUNT(*) as n FROM corpus").iloc[0]['n']
    roots = sql("SELECT COUNT(DISTINCT root) as n FROM corpus WHERE root IS NOT NULL").iloc[0]['n']
    verbs = sql("SELECT COUNT(*) as n FROM corpus WHERE pos='V'").iloc[0]['n']
    nouns = sql("SELECT COUNT(*) as n FROM corpus WHERE pos='N'").iloc[0]['n']
    c1.metric("Totaal segmenten", f"{total:,}")
    c2.metric("Unieke wortels", f"{roots:,}")
    c3.metric("Werkwoorden", f"{verbs:,}")
    c4.metric("Zelfst. naamwoorden", f"{nouns:,}")

    # Top roots
    st.subheader("Top 20 meest voorkomende wortels")
    top_roots = sql("""
        SELECT root_ar, COUNT(*) as freq
        FROM corpus WHERE root_ar IS NOT NULL
        GROUP BY root_ar ORDER BY freq DESC LIMIT 20
    """)
    st.bar_chart(top_roots.set_index('root_ar'), horizontal=True)

    # POS distribution
    st.subheader("Woordsoorten verdeling")
    pos_dist = sql("""
        SELECT pos, COUNT(*) as freq
        FROM corpus WHERE pos IS NOT NULL
        GROUP BY pos ORDER BY freq DESC
    """)
    st.bar_chart(pos_dist.set_index('pos'))

    # Verb aspects
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Werkwoord aspect")
        aspects = sql("""
            SELECT aspect, COUNT(*) as freq
            FROM corpus WHERE pos='V' AND aspect IS NOT NULL
            GROUP BY aspect ORDER BY freq DESC
        """)
        st.bar_chart(aspects.set_index('aspect'))

    with col2:
        st.subheader("Werkwoordvormen (أوزان)")
        forms = sql("""
            SELECT COALESCE(verb_form, 'I') as form, COUNT(*) as freq
            FROM corpus WHERE pos='V'
            GROUP BY form ORDER BY 
                CASE form 
                    WHEN 'I' THEN 1 WHEN 'II' THEN 2 WHEN 'III' THEN 3 
                    WHEN 'IV' THEN 4 WHEN 'V' THEN 5 WHEN 'VI' THEN 6
                    WHEN 'VII' THEN 7 WHEN 'VIII' THEN 8 WHEN 'IX' THEN 9
                    WHEN 'X' THEN 10 WHEN 'XI' THEN 11 WHEN 'XII' THEN 12
                END
        """)
        st.bar_chart(forms.set_index('form'))

    # Words per surah
    st.subheader("Woorden per soera")
    wps = sql("""
        SELECT surah, COUNT(DISTINCT ayah || '-' || word) as woorden
        FROM corpus GROUP BY surah ORDER BY surah
    """)
    st.bar_chart(wps.set_index('surah'))


# ── Page: Vrije SQL query ──────────────────────────────────────────────────
elif page == "📝 Vrije SQL query":
    st.title("📝 Vrije SQL query")
    st.caption("Tabellen: `corpus` | Views: `words`, `ayat`")

    query = st.text_area("SQL Query", value="SELECT * FROM ayat WHERE surah = 112", height=100)

    if st.button("Uitvoeren", type="primary"):
        try:
            result = sql(query)
            st.success(f"{len(result):,} rijen")
            st.dataframe(result, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Fout: {e}")

    with st.expander("Schema referentie"):
        st.markdown("""
        **Tabel `corpus`** — alle morphologische segmenten:
        `surah, ayah, word, segment, form_bw, form_ar, tag, segment_type, pos, 
        lemma, lemma_ar, root, root_ar, aspect, verb_form, voice, derivation,
        person, gender, number, "case", mood, state, prefix, suffix_pron, special`
        
        **View `words`** — per woord: `surah, ayah, word, word_ar, word_bw`
        
        **View `ayat`** — per vers: `surah, ayah, verse_ar`
        """)
