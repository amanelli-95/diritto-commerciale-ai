import json
import re
from dataclasses import dataclass
from typing import List, Dict

import streamlit as st
from openai import OpenAI
from pypdf import PdfReader

APP_TITLE = "Tutor Diritto Commerciale"
MODEL_DEFAULT = "gpt-4.1-mini"

st.set_page_config(page_title=APP_TITLE, page_icon="⚖️", layout="centered")

st.markdown("""
<style>
.main .block-container {max-width: 920px; padding-top: 2rem;}
.small-note {font-size: 0.9rem; opacity: 0.75;}
.card {border: 1px solid rgba(128,128,128,.25); border-radius: 14px; padding: 16px; margin: 10px 0;}
</style>
""", unsafe_allow_html=True)

@dataclass
class Chunk:
    text: str
    pages: str

TOPICS = {
    "Introduzione": (2, 5),
    "L'imprenditore e l'azienda": (6, 18),
    "Titoli di credito": (19, 31),
    "Crisi d'impresa": (32, 75),
    "Società e figure affini": (76, 81),
    "Società di persone": (82, 91),
    "Società di capitali - premessa": (92, 94),
    "S.p.A.": (95, 143),
    "S.r.l.": (144, 157),
    "Libri sociali e bilancio": (158, 163),
    "Scioglimento": (164, 166),
    "Società cooperative": (167, 174),
    "Società quotate": (175, 180),
    "Gruppi di società": (181, 188),
    "Trasformazione, fusione e scissione": (189, 200),
}

SYSTEM_BASE = """
Sei un tutor esperto di Diritto Commerciale per una studentessa di Giurisprudenza alla Cattolica.
Devi prepararla all'esame orale usando soprattutto la dispensa caricata.
Rispondi in italiano, con terminologia giuridica precisa, ma spiegazioni chiare.
Quando pertinente, cita articoli del codice civile o riferimenti normativi.
Non inventare contenuti non presenti nel contesto: se manca qualcosa, dillo e proponi come integrarlo.
""".strip()


def get_api_key() -> str:
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return ""


def client() -> OpenAI:
    api_key = get_api_key()
    if not api_key:
        st.error("Manca OPENAI_API_KEY nei Secrets di Streamlit.")
        st.stop()
    return OpenAI(api_key=api_key)


@st.cache_data(show_spinner=False)
def extract_pages(file_bytes: bytes) -> List[str]:
    import io
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for p in reader.pages:
        try:
            txt = p.extract_text() or ""
        except Exception:
            txt = ""
        pages.append(re.sub(r"\s+", " ", txt).strip())
    return pages


def get_topic_context(pages: List[str], topic: str) -> str:
    start, end = TOPICS[topic]
    # Le pagine della dispensa sono 1-based, l'indice Python è 0-based.
    selected = pages[max(0, start-1):min(len(pages), end)]
    body = "\n\n".join(f"[Pag. {start+i}] {txt}" for i, txt in enumerate(selected) if txt)
    return body[:35000]


def build_chunks(pages: List[str], chunk_size: int = 4500, overlap: int = 500) -> List[Chunk]:
    chunks: List[Chunk] = []
    for i, txt in enumerate(pages, start=1):
        if not txt:
            continue
        start = 0
        while start < len(txt):
            piece = txt[start:start+chunk_size]
            chunks.append(Chunk(piece, str(i)))
            if start + chunk_size >= len(txt):
                break
            start += chunk_size - overlap
    return chunks


def score_chunk(query: str, chunk: Chunk) -> int:
    q_words = set(re.findall(r"[a-zàèéìòù0-9]{4,}", query.lower()))
    c = chunk.text.lower()
    return sum(3 if w in c else 0 for w in q_words) + sum(c.count(w) for w in q_words)


def retrieve_context(pages: List[str], query: str, k: int = 8) -> str:
    chunks = build_chunks(pages)
    ranked = sorted(chunks, key=lambda ch: score_chunk(query, ch), reverse=True)[:k]
    parts = [f"[Pag. {ch.pages}] {ch.text}" for ch in ranked if ch.text]
    return "\n\n".join(parts)[:30000]


def ask_model(prompt: str, context: str, temperature: float = 0.25) -> str:
    c = client()
    model = st.session_state.get("model", MODEL_DEFAULT)
    full_input = f"CONTESTO DALLA DISPENSA:\n{context}\n\nRICHIESTA:\n{prompt}"
    response = c.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_BASE},
            {"role": "user", "content": full_input},
        ],
        temperature=temperature,
    )
    return response.output_text


def require_pdf():
    uploaded = st.session_state.get("uploaded_pdf")
    if uploaded is None:
        st.info("Carica la dispensa PDF dalla barra laterale per iniziare.")
        st.stop()
    return extract_pages(uploaded)


st.title("⚖️ Tutor Diritto Commerciale")
st.caption("Riassunti, flashcard, simulazione orale e domande libere dalla dispensa del corso.")

with st.sidebar:
    st.header("Configurazione")
    file = st.file_uploader("Carica la dispensa PDF", type=["pdf"])
    if file:
        st.session_state["uploaded_pdf"] = file.getvalue()
        st.success("PDF caricato correttamente")

    st.session_state["model"] = st.selectbox(
        "Modello OpenAI",
        ["gpt-4.1-mini", "gpt-4.1", "gpt-5-mini", "gpt-5"],
        index=0,
        help="Per studiare conviene partire da gpt-4.1-mini: costa meno ed è veloce."
    )
    st.markdown("<p class='small-note'>La chiave API va inserita nei Secrets di Streamlit, non nel codice.</p>", unsafe_allow_html=True)

pages = None
if "uploaded_pdf" in st.session_state:
    pages = extract_pages(st.session_state["uploaded_pdf"])
    st.sidebar.write(f"Pagine lette: {len(pages)}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Riassunti", "Flashcard", "Orale", "Domande", "Metodo"])

with tab1:
    st.subheader("Genera riassunto")
    pages = require_pdf()
    topic = st.selectbox("Argomento", list(TOPICS.keys()))
    level = st.radio("Livello", ["Sintetico", "Medio", "Approfondito"], horizontal=True)
    if st.button("Genera riassunto", type="primary"):
        context = get_topic_context(pages, topic)
        prompt = f"""
Crea un riassunto {level.lower()} sull'argomento: {topic}.
Struttura obbligatoria:
1. Definizione e inquadramento
2. Requisiti / elementi essenziali
3. Distinzioni importanti
4. Normativa rilevante
5. Errori da evitare all'esame
6. Mini-schema finale da memorizzare
""".strip()
        with st.spinner("Genero il riassunto..."):
            st.markdown(ask_model(prompt, context))

with tab2:
    st.subheader("Genera flashcard")
    pages = require_pdf()
    topic_f = st.selectbox("Argomento flashcard", list(TOPICS.keys()), key="topic_f")
    n_cards = st.slider("Numero flashcard", 5, 20, 10)
    difficulty = st.selectbox("Difficoltà", ["base", "media", "avanzata", "mista"])
    if st.button("Genera flashcard", type="primary"):
        context = get_topic_context(pages, topic_f)
        prompt = f"""
Genera {n_cards} flashcard su {topic_f}, difficoltà {difficulty}.
Rispondi in JSON valido con questa struttura:
[
  {{"domanda":"...", "risposta":"...", "livello":"base|medio|avanzato"}}
]
La risposta deve essere breve ma precisa, adatta a ripasso orale.
""".strip()
        with st.spinner("Creo le flashcard..."):
            raw = ask_model(prompt, context, temperature=0.1)
        try:
            data = json.loads(re.search(r"\[[\s\S]*\]", raw).group(0))
            for i, card in enumerate(data, start=1):
                with st.expander(f"{i}. {card.get('domanda','Domanda')}"):
                    st.write(card.get("risposta", ""))
                    st.caption(f"Livello: {card.get('livello','')}")
        except Exception:
            st.markdown(raw)

with tab3:
    st.subheader("Simulazione orale")
    pages = require_pdf()
    topic_o = st.selectbox("Argomento orale", ["Casuale"] + list(TOPICS.keys()), key="topic_o")

    if "oral_messages" not in st.session_state:
        st.session_state["oral_messages"] = []

    col_a, col_b = st.columns(2)
    with col_a:
        start_oral = st.button("Inizia nuova interrogazione", type="primary")
    with col_b:
        if st.button("Reset"):
            st.session_state["oral_messages"] = []
            st.rerun()

    if start_oral:
        if topic_o == "Casuale":
            context = retrieve_context(pages, "domande generali diritto commerciale imprenditore società crisi impresa titoli credito")
        else:
            context = get_topic_context(pages, topic_o)
        prompt = f"""
Simula il Prof. Presti all'orale. Argomento: {topic_o}.
Fai una sola domanda iniziale, chiara ma universitaria. Non dare ancora la risposta.
""".strip()
        with st.spinner("Preparo la prima domanda..."):
            first = ask_model(prompt, context)
        st.session_state["oral_context"] = context
        st.session_state["oral_messages"] = [{"role": "assistant", "content": first}]

    for msg in st.session_state.get("oral_messages", []):
        with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
            st.markdown(msg["content"])

    answer = st.chat_input("Scrivi la risposta della studentessa...")
    if answer:
        st.session_state["oral_messages"].append({"role": "user", "content": answer})
        history = "\n".join(f"{m['role']}: {m['content']}" for m in st.session_state["oral_messages"][-8:])
        context = st.session_state.get("oral_context", retrieve_context(pages, answer))
        prompt = f"""
Questa è la conversazione dell'orale:
{history}

Correggi l'ultima risposta della studentessa con:
- valutazione: ✅ buona / ⚠️ incompleta / ❌ errata
- cosa va bene
- cosa manca o cosa correggere
Poi fai UNA nuova domanda collegata, senza dare la risposta.
""".strip()
        with st.spinner("Valuto e preparo la prossima domanda..."):
            reply = ask_model(prompt, context)
        st.session_state["oral_messages"].append({"role": "assistant", "content": reply})
        st.rerun()

with tab4:
    st.subheader("Domanda libera")
    pages = require_pdf()
    q = st.text_area("Fai una domanda sulla dispensa", placeholder="Es. Differenza tra nullità e annullabilità nella società? Come funziona il concordato preventivo?")
    if st.button("Rispondi", type="primary") and q.strip():
        context = retrieve_context(pages, q)
        prompt = f"""
Rispondi alla domanda: {q}
Usa una struttura chiara:
1. Risposta breve
2. Spiegazione completa
3. Riferimenti normativi se presenti
4. Esempio pratico
5. Come dirlo all'orale
""".strip()
        with st.spinner("Cerco nella dispensa e rispondo..."):
            st.markdown(ask_model(prompt, context))

with tab5:
    st.subheader("Metodo di studio")
    pages = require_pdf()
    if st.button("Crea piano di ripasso da 7 giorni"):
        context = "\n".join(pages[:3])
        prompt = """
Crea un piano di ripasso di 7 giorni per l'esame orale di diritto commerciale usando l'indice della dispensa.
Per ogni giorno indica: argomenti, obiettivo, output da produrre, domande di autoverifica.
""".strip()
        with st.spinner("Creo il piano..."):
            st.markdown(ask_model(prompt, context))

st.divider()
st.caption("Nota: l'app supporta lo studio, ma la studentessa deve sempre verificare sul materiale ufficiale e sul programma d'esame.")
