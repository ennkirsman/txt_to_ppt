from __future__ import annotations

import os

import streamlit as st
from openai import OpenAI

from src.ai import LANGUAGES, describe_image, generate_deck_plan, summarize_source
from src.extractors import extract_uploaded_files
from src.images import search_commons_image
from src.ppt_builder import build_pptx


st.set_page_config(page_title="Õppetekst → PowerPoint", page_icon="🎓", layout="wide")
st.title("🎓 Õppetekst → PowerPoint")
st.caption("Laadi ühe teema õppematerjalid ja genereeri õpetamiseks kokkuvõtlikud slaidid koos õpetaja märkmetega.")

with st.sidebar:
    st.header("Seaded")
    api_key = st.text_input(
        "OpenAI API key",
        value=os.getenv("OPENAI_API_KEY", ""),
        type="password",
        help="Võtit kasutatakse ainult selle brauserisessiooni jooksul ja seda ei salvestata repositooriumisse.",
    )
    model = st.text_input("OpenAI mudel", value=os.getenv("OPENAI_MODEL", "gpt-5-mini"))
    use_web = st.checkbox("Leia veebist täiendavaid huvitavaid fakte", value=True)
    use_web_images = st.checkbox("Otsi vajadusel pilte Wikimedia Commonsist", value=True)
    max_pdf_pages = st.number_input("PDF-i maksimaalne lehekülgede arv", min_value=5, max_value=300, value=80, step=5)

st.subheader("1. Keeled")
col1, col2 = st.columns(2)
with col1:
    input_language = st.selectbox("Mis keeles on algtekstid?", LANGUAGES, index=0)
with col2:
    output_language = st.selectbox("Mis keeles slaide soovid?", LANGUAGES, index=0)

st.info("Failide laadimine on allpool meelega alles pärast keelevalikut — eriti fotode OCR vajab algteksti keelt.")

st.subheader("2. Laadi õppematerjalid")
uploaded_files = st.file_uploader(
    "PDF, Word (.docx) või fotod",
    type=["pdf", "docx", "png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
)

st.subheader("3. Slaidide ülesehitus")
c1, c2 = st.columns(2)
with c1:
    slide_count = st.slider("Sisuslaidide arv", min_value=4, max_value=24, value=10)
with c2:
    audience = st.text_input("Sihtrühm", value="põhikooli või gümnaasiumi õpilased")

if uploaded_files:
    st.write("**Valitud failid:**", ", ".join(f.name for f in uploaded_files))

if st.button("Genereeri PowerPoint", type="primary", disabled=not uploaded_files):
    if not api_key:
        st.error("Piltidelt teksti lugemiseks ja slaidide genereerimiseks sisesta OpenAI API key.")
        st.stop()

    client = OpenAI(api_key=api_key)
    progress = st.progress(0, text="Loen failidest teksti ja pilte…")

    try:
        extracted = extract_uploaded_files(
            uploaded_files,
            client=client,
            language=input_language,
            model=model,
            max_pdf_pages=int(max_pdf_pages),
        )
    except Exception as exc:
        st.exception(exc)
        st.stop()

    if extracted.warnings:
        for warning in extracted.warnings:
            st.warning(warning)
    if not extracted.text.strip():
        st.error("Failidest ei õnnestunud piisavalt teksti kätte saada.")
        st.stop()

    progress.progress(22, text="Kirjeldan võimalikke lähtefailide illustratsioone…")
    image_descriptions: list[str] = []
    for asset in extracted.images[:12]:
        try:
            description = describe_image(client, asset.data, asset.mime_type, model)
        except Exception:
            description = f"Image from {asset.name}"
        asset.description = description
        image_descriptions.append(description)

    progress.progress(38, text="Teen õppetekstist sisulise kokkuvõtte…")
    source_summary = summarize_source(client, extracted.text, input_language, model)

    progress.progress(58, text="Koostan slaidide plaani ja õpetaja märkmed…")
    try:
        plan = generate_deck_plan(
            client=client,
            source_summary=source_summary,
            input_language=input_language,
            output_language=output_language,
            slide_count=slide_count,
            audience=audience,
            image_descriptions=image_descriptions,
            model=model,
            use_web=use_web,
        )
    except Exception as exc:
        st.exception(exc)
        st.stop()

    resolved_images = []
    slides = plan.get("slides", [])
    for idx, slide in enumerate(slides):
        pct = 60 + int(25 * (idx + 1) / max(1, len(slides)))
        progress.progress(pct, text=f"Otsin illustratsioone… {idx + 1}/{len(slides)}")
        image = None
        uploaded_index = slide.get("uploaded_image_index")
        if use_web_images and not uploaded_index:
            try:
                image = search_commons_image(str(slide.get("image_query", "")))
            except Exception:
                image = None
        resolved_images.append(image)

    progress.progress(90, text="Ehitan PowerPointi ja lisan Notes-väljad…")
    pptx_bytes = build_pptx(plan, extracted.images, resolved_images)
    progress.progress(100, text="Valmis!")

    st.success(f"Valmis: {len(slides)} sisuslaidi + tiitelslaid" + (" + allikad" if plan.get("references") else ""))
    st.download_button(
        "⬇️ Laadi PowerPoint alla",
        data=pptx_bytes,
        file_name="oppematerjal_slaidid.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        type="primary",
    )

    with st.expander("Vaata genereeritud slaidikava"):
        st.json(plan)
    with st.expander("Vaata failidest loetud teksti"):
        st.text_area("Ekstraheeritud tekst", extracted.text, height=350)
