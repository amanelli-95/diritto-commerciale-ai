# Tutor Diritto Commerciale - Streamlit

App Streamlit per studiare una dispensa PDF di Diritto Commerciale con AI.

## Funzioni

- Upload della dispensa PDF
- Riassunti per argomento
- Flashcard
- Simulazione orale stile professore
- Domande libere sulla dispensa
- Piano di ripasso da 7 giorni

## Avvio locale

```bash
pip install -r requirements.txt
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Apri `.streamlit/secrets.toml` e inserisci la tua chiave:

```toml
OPENAI_API_KEY = "sk-..."
```

Poi avvia:

```bash
streamlit run app.py
```

## Pubblicazione gratis su Streamlit Community Cloud

1. Crea un repository GitHub.
2. Carica questi file nel repository:
   - `app.py`
   - `requirements.txt`
   - `.gitignore`
3. Vai su Streamlit Community Cloud.
4. Crea una nuova app collegando il repository GitHub.
5. Nel pannello Secrets inserisci:

```toml
OPENAI_API_KEY = "sk-..."
```

6. Salva e pubblica.
7. Condividi il link alla tua amica.

## Nota sulla chiave API

Non inserire mai la chiave API dentro `app.py` e non caricare mai `.streamlit/secrets.toml` su GitHub.
La chiave va salvata solo nei Secrets di Streamlit Cloud.
