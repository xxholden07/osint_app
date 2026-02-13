import io
from typing import Dict, List, Tuple

import pandas as pd
import requests
import streamlit as st
from PIL import ExifTags, Image

from osint_core import OSINTCore


def set_dark_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Space+Grotesk:wght@400;600&display=swap');
        :root {
            --bg: #0b0f14;
            --panel: #121825;
            --accent: #42ff8b;
            --accent-2: #00c2ff;
            --text: #e7f0ff;
            --muted: #8ea2c6;
            --danger: #ff4b4b;
        }
        html, body, [class*="css"]  {
            font-family: 'Space Grotesk', sans-serif;
            background-color: var(--bg);
            color: var(--text);
        }
        .block-container {
            padding-top: 1.5rem;
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d131d, #0b0f14);
            border-right: 1px solid #1f2a3d;
        }
        .stButton button {
            background: linear-gradient(90deg, var(--accent), var(--accent-2));
            color: #061018;
            border: none;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
        }
        .stMetric {
            background: var(--panel);
            border-radius: 12px;
            padding: 0.8rem;
            border: 1px solid #1b263a;
        }
        .tag-chip {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
            background: #1a2638;
            color: var(--muted);
            margin-right: 0.4rem;
            font-size: 0.75rem;
        }
        .profile-card {
            display: flex;
            gap: 1rem;
            align-items: center;
            background: var(--panel);
            border-radius: 14px;
            padding: 1rem;
            border: 1px solid #1b263a;
        }
        .avatar {
            width: 96px;
            height: 96px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid var(--accent);
        }
        .danger {
            background: rgba(255, 75, 75, 0.12);
            border: 1px solid rgba(255, 75, 75, 0.4);
            color: var(--danger);
            padding: 0.6rem 0.8rem;
            border-radius: 10px;
            margin-top: 0.8rem;
        }
        .image-card {
            background: var(--panel);
            border-radius: 12px;
            padding: 0.6rem;
            border: 1px solid #1b263a;
        }
        .placeholder {
            width: 100%;
            height: 180px;
            background: #1b2332;
            border-radius: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def build_link_table(dork_results: Dict[str, object]) -> pd.DataFrame:
    rows: List[Dict[str, str]] = []
    for entry in dork_results.get("dorks", []):
        dork_type = entry.get("type", "")
        for url in entry.get("urls", []):
            rows.append(
                {
                    "Tipo da Dork": dork_type,
                    "URL Encontrada": url,
                    "Ação": url,
                }
            )
    return pd.DataFrame(rows)


def extract_image_urls_from_dorks(dork_results: Dict[str, object]) -> List[str]:
    image_dork_types = {"Fotos e Imagens", "Fotos em Redes Sociais"}
    image_extensions = (".jpg", ".jpeg", ".png")
    image_urls: List[str] = []
    for entry in dork_results.get("dorks", []):
        if entry.get("type", "") in image_dork_types:
            for url in entry.get("urls", []):
                if url.lower().endswith(image_extensions):
                    image_urls.append(url)
    return image_urls


def fetch_image(url: str, headers: Dict[str, str]) -> Tuple[bytes, str]:
    try:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code == 403:
            return b"", "forbidden"
        response.raise_for_status()
        return response.content, "ok"
    except Exception:
        return b"", "error"


def extract_exif(image_bytes: bytes) -> Dict[str, object]:
    if not image_bytes:
        return {}
    image = Image.open(io.BytesIO(image_bytes))
    exif = image.getexif()
    if not exif:
        return {}
    exif_data = {}
    for tag_id, value in exif.items():
        tag = ExifTags.TAGS.get(tag_id, tag_id)
        exif_data[tag] = value
    gps_info = exif.get(34853)
    if gps_info:
        gps_tags = {}
        for key, value in gps_info.items():
            gps_tags[ExifTags.GPSTAGS.get(key, key)] = value
        exif_data["GPSInfo"] = gps_tags
    return exif_data


def gps_to_decimal(gps_info: Dict[str, object]) -> Tuple[float, float]:
    def to_degrees(value: Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]) -> float:
        d = value[0][0] / value[0][1]
        m = value[1][0] / value[1][1]
        s = value[2][0] / value[2][1]
        return d + (m / 60.0) + (s / 3600.0)

    lat = to_degrees(gps_info["GPSLatitude"])
    if gps_info.get("GPSLatitudeRef") == "S":
        lat = -lat
    lon = to_degrees(gps_info["GPSLongitude"])
    if gps_info.get("GPSLongitudeRef") == "W":
        lon = -lon
    return lat, lon


def main() -> None:
    st.set_page_config(page_title="OSINT Dark Ops", layout="wide")
    set_dark_theme()

    core = OSINTCore()

    st.sidebar.title("OSINT Dark Ops")
    section = st.sidebar.radio(
        "Navegacao",
        ["Dashboard", "Google Dorks", "Instagram Intel", "Relatorios"],
    )

    if "session_results" not in st.session_state:
        st.session_state.session_results = {
            "google_dorks": {},
            "instagram": {},
            "private_sniffer": {},
            "image_gallery": {},
        }

    if section == "Dashboard":
        st.title("Painel de Operacoes")
        st.write("Fluxo rapido de OSINT passivo em ambiente controlado.")
        st.markdown(
            "<span class='tag-chip'>passive</span><span class='tag-chip'>ghdb</span><span class='tag-chip'>social</span><span class='tag-chip'>media</span>",
            unsafe_allow_html=True,
        )

    if section == "Google Dorks":
        st.header("Advanced Google Hacking")
        target = st.text_input("Username ou Nome da Pessoa", placeholder="johndoe ou João Silva")
        dork_options = [
            "Fotos e Imagens",
            "Perfis em Redes Sociais",
            "Fotos em Redes Sociais",
            "Mencoes Publicas",
        ]
        selected_dorks = st.multiselect("Tipos de Busca", dork_options, default=dork_options)
        st.subheader("Galeria de Evidencias")
        image_count = st.slider("Max imagens", min_value=3, max_value=18, value=9, step=3)

        if st.button("Executar Dorks") and target:
            with st.spinner("Executando dorks... isso pode levar alguns segundos."):
                try:
                    dork_results = core.advanced_google_hacking(target, selected_dorks)
                except Exception as exc:
                    st.error(f"Erro ao executar dorks: {exc}")
                    dork_results = {}
            st.session_state.session_results["google_dorks"] = dork_results
            image_urls = extract_image_urls_from_dorks(dork_results)
            if image_urls:
                st.session_state.session_results["image_gallery"] = {
                    "target": target,
                    "urls": image_urls[:image_count],
                }
            else:
                st.session_state.session_results["image_gallery"] = {}
            if dork_results and not any(
                entry.get("urls") for entry in dork_results.get("dorks", [])
            ):
                st.warning(
                    "Nenhum resultado encontrado. O servico de busca pode estar"
                    " bloqueando requisicoes deste servidor. Tente novamente mais tarde."
                )

        dork_results = st.session_state.session_results.get("google_dorks", {})
        if dork_results:
            table = build_link_table(dork_results)
            if not table.empty:
                st.dataframe(
                    table,
                    use_container_width=True,
                    column_config={
                        "Ação": st.column_config.LinkColumn(
                            "Ação",
                            display_text="Abrir",
                        )
                    },
                )

        gallery = st.session_state.session_results.get("image_gallery", {})
        image_urls = gallery.get("urls", []) if gallery else []
        if image_urls:
            columns = st.columns(3)
            headers = core._get_headers()
            for idx, url in enumerate(image_urls[:image_count]):
                col = columns[idx % 3]
                with col:
                    st.markdown("<div class='image-card'>", unsafe_allow_html=True)
                    image_bytes, status = fetch_image(url, headers)
                    if status == "ok":
                        st.image(image_bytes, use_container_width=True)
                    else:
                        st.markdown("<div class='placeholder'></div>", unsafe_allow_html=True)
                        st.caption("Acesso Negado")
                    btn_key = f"meta_{idx}"
                    if st.button("🔍 Ver Metadados", key=btn_key):
                        exif = extract_exif(image_bytes)
                        if not exif:
                            st.info("Sem metadados disponiveis.")
                        else:
                            st.json({k: str(v) for k, v in exif.items() if k != "GPSInfo"})
                            gps = exif.get("GPSInfo")
                            if gps:
                                lat, lon = gps_to_decimal(gps)
                                st.markdown(
                                    f"[Abrir no Google Maps](https://maps.google.com/?q={lat},{lon})"
                                )
                    st.markdown("</div>", unsafe_allow_html=True)

    if section == "Instagram Intel":
        st.header("Instagram Intelligence")
        username = st.text_input("@usuario", placeholder="nome_do_usuario")
        if st.button("Coletar Perfil") and username:
            profile_data = core.get_profile_metadata(username.strip("@"))
            st.session_state.session_results["instagram"] = profile_data

        profile_data = st.session_state.session_results.get("instagram", {})
        if profile_data:
            if "error" in profile_data:
                st.error(profile_data["error"])
            else:
                st.markdown(
                    f"""
                    <div class='profile-card'>
                        <img class='avatar' src='{profile_data.get('profile_pic_url', '')}' />
                        <div>
                            <h3>@{profile_data.get('username')}</h3>
                            <p>{profile_data.get('bio', '')}</p>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                cols = st.columns(3)
                cols[0].metric("Seguidores", profile_data.get("followers", 0))
                cols[1].metric("Seguindo", profile_data.get("following", 0))
                cols[2].metric("ID", profile_data.get("id", ""))

                if profile_data.get("is_private"):
                    st.markdown(
                        "<div class='danger'>⚠️ Perfil Privado Detectado</div>",
                        unsafe_allow_html=True,
                    )

                if st.button("Rodar Private Sniffer"):
                    sniffer = core.private_sniffer(profile_data["username"])
                    st.session_state.session_results["private_sniffer"] = sniffer

        sniffer = st.session_state.session_results.get("private_sniffer", {})
        if sniffer:
            st.subheader("Collabs Publicas Encontradas")
            if sniffer.get("urls"):
                for link in sniffer["urls"]:
                    st.markdown(f"- [{link}]({link})")
            else:
                st.info("Sem resultados publicos.")

    if section == "Relatorios":
        st.header("Exportar Relatorios")
        results = st.session_state.session_results
        if st.button("Exportar CSV"):
            rows = []
            for dork in results.get("google_dorks", {}).get("dorks", []):
                for url in dork.get("urls", []):
                    rows.append({"tipo": dork.get("type"), "url": url})
            for url in results.get("private_sniffer", {}).get("urls", []):
                rows.append({"tipo": "instagram_collab", "url": url})
            for url in results.get("image_gallery", {}).get("urls", []):
                rows.append({"tipo": "image_gallery", "url": url})
            df = pd.DataFrame(rows)
            csv_data = df.to_csv(index=False)
            st.download_button("Baixar CSV", data=csv_data, file_name="osint_results.csv")


if __name__ == "__main__":
    main()
