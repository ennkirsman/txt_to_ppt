# txt_to_ppt

Esimene prototüüp rakendusest, mis muudab ühe teema õppematerjalid õpetaja PowerPointiks.

## Mida v0.1 teeb

- küsib **enne failide laadimist** algteksti keelt ja slaidide keelt;
- võtab sisendiks PDF-i, Wordi `.docx` faili või fotod (`png/jpg/jpeg/webp`);
- loeb PDF/DOCX teksti otse ning kasutab piltide ja skannitud PDF-lehtede puhul OpenAI visuaalset tekstilugemist;
- teeb pikast tekstist vahekokkuvõtte ja koostab sellest õpetamiseks sobiva slaidikava;
- võib Responses API veebitööriista abil lisada väikese hulga täiendavaid huvitavaid fakte;
- kasutab võimalusel lähtefailidest leitud illustratsioone;
- otsib puuduvad illustratsioonid Wikimedia Commonsist ning lisab pildi krediidi PowerPointi Notes-väljale;
- genereerib `.pptx` faili;
- kirjutab iga sisuslaidi juurde õpetaja jaoks **Notes / Speaker notes** teksti;
- lisab kasutatud veebiallikad lõpus eraldi slaidile.

> Tegemist on esimese prototüübiga. Enne klassis kasutamist tuleb AI lisatud faktid ja automaatselt valitud pildid üle kontrollida.

## Käivitamine Windowsis

Vajalik on Python 3.11 või uuem.

```powershell
git clone https://github.com/ennkirsman/txt_to_ppt.git
cd txt_to_ppt
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Brauseris avaneb rakendus tavaliselt aadressil `http://localhost:8501`.

## OpenAI API võti

Kõige lihtsam on sisestada võti rakenduse vasakus külgpaneelis. Võtit ei kirjutata faili ega GitHubi.

Soovi korral võib kasutada keskkonnamuutujat:

```powershell
$env:OPENAI_API_KEY="sk-..."
$env:OPENAI_MODEL="gpt-5-mini"
streamlit run app.py
```

Mudeli nime saab ka rakenduses muuta, et repo ei sõltuks ühest kindlast mudeliversioonist.

## Failide töötlemine

### PDF

Tekstikiht loetakse PyMuPDF abil. Kui leheküljel praktiliselt puudub tekstikiht, renderdatakse leht pildiks ja proovitakse tekst lugeda OpenAI visuaalsisendi abil. PDF-ist proovitakse kätte saada ka piisavalt suured manustatud rasterpildid.

### DOCX

Loetakse lõigud ja tabelid. `word/media` kaustast võetakse kasutatavad rasterpildid.

### Fotod

Foto saadetakse tekstilugemiseks OpenAI mudelile. Algteksti keele valik aitab mudelil OCR-i paremini tõlgendada.

## Pildid ja autoriõigus

Veebist otsitakse selles versioonis pilte ainult **Wikimedia Commonsist**. Rakendus loeb Commonsi metaandmetest autori/litsentsi info ja lisab selle vastava slaidi Notes-väljale. Litsentsitingimused võivad pilditi erineda, seetõttu tasub lõplik krediit alati üle vaadata.

## Struktuur

```text
app.py                  Streamliti kasutajaliides ja töövoog
src/ai.py               OCR, pildikirjeldus, kokkuvõte ja slaidiplaan
src/extractors.py       PDF/DOCX/piltide töötlemine
src/images.py           Wikimedia Commons pildiotsing
src/ppt_builder.py      PowerPoint + speaker notes
requirements.txt
.env.example
```

## Teadaolevad piirangud v0.1-s

1. Vanemat `.doc` formaati ei toetata, ainult `.docx`.
2. Keerukad matemaatilised valemid lähevad esialgu PowerPointi tavalise Unicode/plain-text kujul, mitte Office Equation objektina.
3. Väga mahukate materjalide puhul tehakse tekstist osade kaupa vahekokkuvõte; seetõttu võib mõni sekundaarne detail välja jääda.
4. Veebist lisatud faktid sõltuvad kasutatava OpenAI mudeli veebitööriista toest. Kui veebitööriist pole saadaval, jätkab rakendus ilma selleta.
5. Pildi automaatne sobitamine on semantiline ja võib eksida. Commonsi pildiotsing on teadlikult konservatiivne.
6. Slaidikujundus on praegu üks lihtne 16:9 õpetamisvaade. Mallide valik tuleb järgmises versioonis.

## Järgmise versiooni mõistlikud täiendused

- enne PPT genereerimist visuaalne slaidiredaktor: pealkiri, bulletid, pilt ja Notes eraldi muudetavad;
- mitu kujundusmalli ja kooli logo/värvide mall;
- Office Equation / LaTeX valemite parem renderdamine;
- piltide valiku eelvaade ja käsitsi asendamine;
- allikaviited fakti tasemel;
- PPTX kõrval PDF ja Google Slides eksport;
- lokaalne OCR valik neile, kes ei soovi pilte API-sse saata.
